"""Hybrid retrieval over the Layer 2 policy corpus and the Annex A knowledge graph.

Implements the retrieval half of the RAG pipeline:
  - sparse BM25 over chunked policy-corpus documents (pure Python, no heavy deps),
  - a control-level lexical retriever over Annex A nodes,
  - knowledge-graph expansion of retrieved controls along requires/mitigates edges,
  - Reciprocal Rank Fusion of the ranked lists.

A dense FAISS retriever is used in the on-premises deployment; it is omitted here so the
demo runs on CPU-only hosting. `rrf_fuse` accepts any number of ranked lists, so a dense
list can be added without changing callers.
"""
import os, re, math, glob
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "..", "03_policy_corpus")

_TOKEN = re.compile(r"[a-z0-9][a-z0-9\-\.]+")
_STOP = set("""the a an and or of to in for on with as is are be by that this these those it its
from at not no any all such which where when who whom shall should must may can will would
we you they he she our your their i""".split())


def tokenize(text):
    return [t for t in _TOKEN.findall((text or "").lower()) if t not in _STOP and len(t) > 1]


# ---------------------------------------------------------------- corpus chunking
def load_corpus_chunks():
    """One chunk per markdown section, carrying its document id, title and owner."""
    chunks = []
    for path in sorted(glob.glob(os.path.join(CORPUS, "*.md"))):
        raw = open(path, encoding="utf-8").read()
        doc_id = os.path.basename(path).split("_")[0]
        title = raw.splitlines()[0].lstrip("# ").strip()
        owner = ""
        m = re.search(r"\*\*Procedure owner:\*\*\s*(.+)", raw)
        if m:
            owner = m.group(1).strip()
        controls = ""
        m = re.search(r"\*\*Related Annex A controls:\*\*\s*(.+)", raw)
        if m:
            controls = m.group(1).strip()
        # split on markdown H2 sections; keep the header with its body
        parts = re.split(r"\n## ", raw)
        for i, p in enumerate(parts):
            body = p if i == 0 else "## " + p
            body = body.strip()
            if len(body) < 40:
                continue
            sec = body.splitlines()[0].lstrip("# ").strip()
            chunks.append({"doc_id": doc_id, "title": title, "owner": owner,
                           "controls": controls, "section": sec, "text": body,
                           "tokens": tokenize(body)})
    return chunks


# ---------------------------------------------------------------- BM25
class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.N = len(docs) or 1
        self.dl = [len(d["tokens"]) for d in docs]
        self.avgdl = (sum(self.dl) / self.N) if self.N else 0
        df = Counter()
        for d in docs:
            df.update(set(d["tokens"]))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [Counter(d["tokens"]) for d in docs]

    def search(self, query, top_k=6):
        q = tokenize(query)
        scores = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                if t not in self.tf[i]:
                    continue
                f = self.tf[i][t]
                denom = f + self.k1 * (1 - self.b + self.b * self.dl[i] / (self.avgdl or 1))
                s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (denom or 1)
            if s > 0:
                scores.append((s, i))
        scores.sort(reverse=True)
        return [(self.docs[i], s) for s, i in scores[:top_k]]


# ---------------------------------------------------------------- control retrieval
def search_controls(query, controls, top_k=6):
    """Lexical match of the question against this system's control set."""
    q = set(tokenize(query))
    out = []
    for c in controls:
        hay = tokenize(f"{c['control']} {c['title']} {c.get('requirement','')}")
        overlap = len(q & set(hay))
        if c["control"].lower() in (query or "").lower():
            overlap += 5
        if overlap:
            out.append((overlap, c))
    out.sort(key=lambda x: -x[0])
    return [c for _, c in out[:top_k]]


def expand_with_graph(controls_hit, g, all_controls, max_add=4):
    """Knowledge-graph expansion: add inherited controls along requires/mitigates edges."""
    if g is None:
        return []
    have = {c["control"] for c in controls_hit}
    by_id = {c["control"]: c for c in all_controls}
    added = []
    for c in controls_hit:
        cid = c["control"]
        if cid not in g.nodes:
            continue
        for _, tgt, data in g.out_edges(cid, data=True):
            if data.get("edge_type") in ("requires", "mitigates") and tgt not in have:
                have.add(tgt)
                if tgt in by_id:
                    item = dict(by_id[tgt]); item["_inherited_from"] = cid
                    added.append(item)
                if len(added) >= max_add:
                    return added
    return added


# ---------------------------------------------------------------- fusion
def rrf_fuse(ranked_lists, k=60, top_k=8):
    """Reciprocal Rank Fusion over any number of ranked lists of hashable keys."""
    scores = {}
    for lst in ranked_lists:
        for rank, key in enumerate(lst, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return [key for key, _ in sorted(scores.items(), key=lambda x: -x[1])[:top_k]]


_INDEX = None


def get_index():
    global _INDEX
    if _INDEX is None:
        chunks = load_corpus_chunks()
        _INDEX = (chunks, BM25(chunks))
    return _INDEX


def retrieve(query, controls=None, g=None, top_corpus=4, top_controls=5):
    """Return retrieved policy-corpus chunks and controls for one question."""
    chunks, bm25 = get_index()
    corpus_hits = bm25.search(query, top_k=top_corpus * 2)
    # RRF over BM25 rank and a document-title match rank, then keep the top chunks
    bm_rank = [c["doc_id"] + "|" + c["section"] for c, _ in corpus_hits]
    q = set(tokenize(query))
    title_rank = [c["doc_id"] + "|" + c["section"] for c, _ in
                  sorted(corpus_hits, key=lambda x: -len(q & set(tokenize(x[0]["title"]))))]
    keep = set(rrf_fuse([bm_rank, title_rank], top_k=top_corpus))
    corpus = [c for c, _ in corpus_hits if c["doc_id"] + "|" + c["section"] in keep]

    ctrl_hits, inherited = [], []
    if controls:
        ctrl_hits = search_controls(query, controls, top_k=top_controls)
        inherited = expand_with_graph(ctrl_hits, g, controls)
    return {"corpus": corpus[:top_corpus], "controls": ctrl_hits, "inherited": inherited}
