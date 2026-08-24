"""Streamlit UI for the ISO 42001 Annex A knowledge-graph demo.

Run from this folder:
    streamlit run demo_app.py

Reuses the same functions as build_kg_networkx.py, so the UI shows exactly what
the pipeline computes: graph traversal to inherited controls, and per-system
applicability cross-referenced with the ground-truth evidence map.
"""
import os, csv
import streamlit as st
from build_kg_networkx import load_graph, inherited_controls, applicable_controls

HERE = os.path.dirname(os.path.abspath(__file__))
GT = os.path.join(HERE, "..", "04_ground_truth", "control_evidence_map.csv")


@st.cache_resource
def get_graph():
    return load_graph()


@st.cache_data
def load_evidence():
    m = {}
    with open(GT, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m[row["control_id"]] = row
    return m


g = get_graph()
evidence = load_evidence()
controls = sorted(g.nodes())

st.set_page_config(page_title="ISO 42001 Compliance Assistant — demo", layout="wide")
st.title("ISO 42001 Annex A — knowledge-graph demo")
st.caption("Synthetic data · Meridian Financial Services (fictional). No real institution is represented.")

tab1, tab2 = st.tabs(["Inherited controls (graph traversal)",
                      "Applicable controls (per system)"])

with tab1:
    seed = st.selectbox("Retrieved control", controls,
                        index=controls.index("A.7.2") if "A.7.2" in controls else 0)
    st.write(f"**{seed}** — {g.nodes[seed].get('short_label', '')}")
    st.caption(g.nodes[seed].get("clause_summary", ""))
    etypes = st.multiselect("Follow edge types", ["requires", "mitigates", "extends"],
                            default=["requires", "mitigates"])
    depth = st.slider("Max traversal depth", 1, 5, 3)
    rows = inherited_controls(g, seed, edge_types=tuple(etypes), max_depth=depth)
    if rows:
        st.subheader(f"{len(rows)} inherited control(s)")
        st.table([{"from": r["from"], "edge": r["via"], "control": r["control"],
                   "title": r["label"], "depth": r["depth"]} for r in rows])
    else:
        st.info("No inherited controls along those edge types.")

with tab2:
    c1, c2, c3 = st.columns(3)
    auto = c1.radio("Automated decision", ["N", "Y"], horizontal=True)
    pii = c2.radio("Personal data", ["N", "Y"], horizontal=True)
    risk = c3.select_slider("Risk level", ["Low", "Medium", "High"], value="High")
    system = {"Automated_Decision": auto, "Personal_Data": pii, "Risk_Level": risk}

    applicable = applicable_controls(g, system)
    table = []
    for cid in applicable:
        ev = evidence.get(cid, {})
        table.append({"control": cid,
                      "title": g.nodes[cid].get("short_label", ""),
                      "evidence_status": ev.get("evidence_status", ""),
                      "evidence_source": ev.get("evidence_source", "")})
    gaps = [r for r in table if r["evidence_status"] == "gap"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Applicable controls", f"{len(applicable)} / {g.number_of_nodes()}")
    m2.metric("Evidenced", len(applicable) - len(gaps))
    m3.metric("Gaps", len(gaps))
    st.dataframe(table, use_container_width=True, hide_index=True)
