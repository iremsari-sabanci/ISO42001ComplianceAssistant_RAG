# Container image for the compliance assistant.
# Works anywhere Docker runs: the bank's on-prem H200, or a Hugging Face Docker Space.
# On-prem, set LLM_BACKEND=ollama (or openai->local vLLM) so nothing leaves the host.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# HF Spaces route traffic to port 7860 by default (see app_port in README.md).
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
EXPOSE 7860

CMD ["streamlit", "run", "02_knowledge_graph/compliance_app.py", \
     "--server.port=7860", "--server.address=0.0.0.0"]
