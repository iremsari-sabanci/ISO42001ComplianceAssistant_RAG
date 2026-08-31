"""Load the Annex A knowledge-graph scaffold into NetworkX and demonstrate the
graph-augmented retrieval step described in the proposal: after the hybrid
retriever surfaces a control, traverse 'requires'/'mitigates' edges to add
inherited controls to the context window.

Usage:
    pip install networkx        # if not already present
    python build_kg_networkx.py

Reads the CSVs in this directory; no ISO text required to run.
"""
import csv, os, json
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))

def load_graph():
    g = nx.DiGraph()
    with open(os.path.join(HERE, "iso42001_annexA_nodes.csv"), newline="") as f:
        for row in csv.DictReader(f):
            g.add_node(row["control_id"], **row)
    with open(os.path.join(HERE, "iso42001_annexA_edges.csv"), newline="") as f:
        for row in csv.DictReader(f):
            g.add_edge(row["from_id"], row["to_id"],
                       edge_type=row["edge_type"], rationale=row["rationale"])
    return g

def inherited_controls(g, seed, edge_types=("requires", "mitigates"), max_depth=3):
    """BFS from a retrieved control over the given edge types."""
    seen, frontier, out = {seed}, [(seed, 0)], []
    while frontier:
        node, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for _, tgt, data in g.out_edges(node, data=True):
            if data["edge_type"] in edge_types and tgt not in seen:
                seen.add(tgt)
                out.append({"control": tgt, "via": data["edge_type"],
                            "from": node, "depth": depth + 1,
                            "label": g.nodes[tgt].get("short_label", "")})
                frontier.append((tgt, depth + 1))
    return out

def applicable_controls(g, system):
    """Filter controls by a system's inventory attributes (applicability triggers)."""
    order = {"": 0, "Low": 1, "Medium": 2, "High": 3}
    sys_risk = order.get(system.get("Risk_Level", ""), 0)
    hits = []
    for cid, d in g.nodes(data=True):
        ta = d.get("trigger_automated_decision", "") == "Y"
        tp = d.get("trigger_personal_data", "") == "Y"
        tr = order.get(d.get("trigger_min_risk", ""), 0)
        # a control applies if it has no triggers, or any of its triggers is met
        has_trigger = ta or tp or (tr > 0)
        applies = (not has_trigger
                   or (ta and system.get("Automated_Decision") == "Y")
                   or (tp and system.get("Personal_Data") == "Y")
                   or (tr > 0 and sys_risk >= tr))
        if applies:
            hits.append(cid)
    return sorted(hits)

if __name__ == "__main__":
    g = load_graph()
    print(f"Loaded {g.number_of_nodes()} controls, {g.number_of_edges()} edges.\n")

    print("Edge-type distribution:")
    for et in ("requires", "mitigates", "extends"):
        n = sum(1 for *_ , d in g.edges(data=True) if d["edge_type"] == et)
        print(f"  {et:10s} {n}")

    for seed in ("A.6.2.4", "A.7.2"):
        print(f"\nInherited controls from {seed} (requires/mitigates, depth<=3):")
        for h in inherited_controls(g, seed):
            print(f"  {h['from']} --{h['via']}--> {h['control']}  ({h['label']})")

    # Example: a high-risk, automated-decision, personal-data system (e.g. SYS-012)
    sys012 = {"Automated_Decision": "Y", "Personal_Data": "Y", "Risk_Level": "High"}
    print("\nApplicable controls for a High-risk automated PII system:")
    print("  " + ", ".join(applicable_controls(g, sys012)))
