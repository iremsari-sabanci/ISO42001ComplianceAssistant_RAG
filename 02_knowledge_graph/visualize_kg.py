"""Render the ISO 42001 Annex A knowledge graph as an interactive HTML page.

Run from this folder:
    python visualize_kg.py

Produces iso42001_kg.html in this folder. Open that file in any browser:
nodes are coloured by objective area, edges by relationship type, and hovering
shows each control's title and one-line summary. Drag nodes to explore.
"""
import os, csv
from pyvis.network import Network

HERE = os.path.dirname(os.path.abspath(__file__))
NODES = os.path.join(HERE, "iso42001_annexA_nodes.csv")
EDGES = os.path.join(HERE, "iso42001_annexA_edges.csv")
OUT = os.path.join(HERE, "iso42001_kg.html")

AREA_COLORS = {
    "A.2": "#1f77b4", "A.3": "#ff7f0e", "A.4": "#2ca02c", "A.5": "#d62728",
    "A.6": "#9467bd", "A.7": "#8c564b", "A.8": "#e377c2", "A.9": "#7f7f7f",
    "A.10": "#17becf",
}
EDGE_COLORS = {"requires": "#d62728", "mitigates": "#2ca02c", "extends": "#1f77b4"}

net = Network(height="820px", width="100%", directed=True, bgcolor="#ffffff", font_color="#222")
net.barnes_hut()

with open(NODES, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        net.add_node(
            r["control_id"], label=r["control_id"],
            title=f"{r['control_id']} — {r['short_label']}\n{r['clause_summary']}",
            color=AREA_COLORS.get(r["area"], "#cccccc"), group=r["area"],
        )

with open(EDGES, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        net.add_edge(
            r["from_id"], r["to_id"], label=r["edge_type"],
            title=f"{r['edge_type']}: {r['rationale']}",
            color=EDGE_COLORS.get(r["edge_type"], "#999999"),
        )

try:
    net.write_html(OUT, notebook=False)
except TypeError:      # older pyvis signatures
    net.save_graph(OUT)
print(f"Wrote {OUT} — open it in your browser.")
