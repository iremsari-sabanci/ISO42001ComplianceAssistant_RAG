# Install & run guide — ISO 42001 Compliance Assistant

One codebase, three ways to run it. Start with **Path 0** to evaluate it locally,
then pick the deployment track. RAG + a live LLM connection is preserved in all of
them; only the LLM backend changes (config, not code).

Synthetic data throughout ("Meridian Financial Services", fictional). The real
inventory/policies never leave the bank.

---

## Path 0 — Run locally first (to evaluate)

Windows `cmd` (yours works with `python`):

```
:: 1. extract the zip, then from the package root:
python -m pip install -r requirements.txt

:: 2. go into the app folder and launch
cd 02_knowledge_graph
streamlit run compliance_app.py
```

A browser opens at http://localhost:8501. It runs immediately on the **template**
backend (no LLM, 0 tokens). Explore all four tabs. Ctrl+C in cmd stops it.

To try **real generation locally**, set these before launching (free, no OpenAI key):

```
set LLM_BACKEND=openai
set OPENAI_BASE_URL=https://router.huggingface.co/v1
set OPENAI_API_KEY=hf_your_token_here
set LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
streamlit run compliance_app.py
```

The HF token is a **free** Hugging Face access token (hf.co/settings/tokens) with the
"Make calls to Inference Providers" permission. No PRO plan required.

---

## Path A — University demo (free): Streamlit Community Cloud

1. Push this whole folder to a **GitHub repo** (keep the structure; `requirements.txt`
   must stay at the repo root).
2. Go to https://share.streamlit.io → **New app** → select your repo.
3. Set **Main file path** to `02_knowledge_graph/compliance_app.py`.
4. (Optional, for live generation) open the app's **Settings → Secrets** and paste:

   ```toml
   LLM_BACKEND = "openai"
   OPENAI_BASE_URL = "https://router.huggingface.co/v1"
   OPENAI_API_KEY = "hf_your_token_here"
   LLM_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
   ```
5. Deploy. Cost: **$0**. If Secrets are left empty it still runs on the template backend.

---

## Path B — Bank / production (on-prem H200): Docker + local LLM

Nothing leaves the host. Assumes Docker on the H200 and a local model server
(Ollama shown; vLLM works via the `openai` backend at a localhost URL).

```
# 1. have a local model available, e.g. Ollama on the host:
ollama pull llama3.1

# 2. build the image (Dockerfile is at the repo root):
docker build -t iso42001-assistant .

# 3. run it, pointing generation at the local Ollama (Linux host networking):
docker run --network host \
  -e LLM_BACKEND=ollama \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -e OLLAMA_MODEL=llama3.1 \
  iso42001-assistant
```

Open http://localhost:7860. For a GPU-served model instead, run vLLM locally and use:

```
docker run --network host \
  -e LLM_BACKEND=openai \
  -e OPENAI_BASE_URL=http://localhost:8000/v1 \
  -e LLM_MODEL=your-local-model \
  iso42001-assistant
```

Cost: **$0 incremental** (own hardware, own model). No external calls, KVKK/VERBİS-safe.

---

## LLM backend reference (set via env vars or Streamlit Secrets)

| Variable          | template | openai (HF router / vLLM / hosted) | ollama            |
|-------------------|----------|------------------------------------|-------------------|
| `LLM_BACKEND`     | template | openai                             | ollama            |
| `OPENAI_BASE_URL` | —        | e.g. https://router.huggingface.co/v1 | —              |
| `OPENAI_API_KEY`  | —        | HF token / provider key            | —                 |
| `OLLAMA_BASE_URL` | —        | —                                  | http://localhost:11434 |
| `OLLAMA_MODEL`    | —        | —                                  | llama3.1          |
| `LLM_MODEL`       | —        | model id                           | —                 |

Leaving everything unset = template backend (works everywhere, 0 tokens).

---

## Other components (optional)

```
cd 02_knowledge_graph
python build_kg_networkx.py     # console demo: graph traversal + applicability filter
python visualize_kg.py          # writes iso42001_kg.html — interactive graph, open in browser
streamlit run demo_app.py       # lighter two-tab KG demo
```

---

## Enabling LLM-backed answers (required for the RAG demo)

The assistant runs without a model on a deterministic retrieval-only backend. To enable
generation, set four environment variables **in the same cmd window before launching**,
then start the app from that window:

```
cd 02_knowledge_graph
set LLM_BACKEND=openai
set OPENAI_BASE_URL=https://router.huggingface.co/v1
set OPENAI_API_KEY=hf_your_token_here
set LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
streamlit run compliance_app.py
```

The variables live only in that cmd window, so they must be set every session (or stored
in `.streamlit/secrets.toml`, or in Settings -> Secrets when deployed). The Risk & compliance
AI tab shows the active backend, the model and the prompt/completion token counts, so it is
visible whether a real model answered.

On-premises equivalent (nothing leaves the host):

```
set LLM_BACKEND=ollama
set OLLAMA_MODEL=llama3.1
streamlit run compliance_app.py
```
