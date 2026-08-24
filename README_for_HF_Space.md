---
title: ISO 42001 Compliance Assistant
emoji: 📋
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# ISO 42001 Compliance Assistant (synthetic demo)

Retrieval-augmented compliance assistant: maps a synthetic AI system inventory to
ISO/IEC 42001 Annex A controls and drafts clause-level gap reports.

**All data is synthetic** — fictional "Meridian Financial Services." No real
institution, system, or individual is represented.

Runs as a Docker Space (Streamlit is no longer a built-in HF SDK). The Dockerfile
launches `02_knowledge_graph/compliance_app.py` on port 7860. Generation defaults to
a no-LLM template backend; set `LLM_BACKEND` and related vars under
**Settings → Variables and secrets** to use a real model.
