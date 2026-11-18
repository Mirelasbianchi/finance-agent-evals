FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /srv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --no-dev --frozen

COPY dashboard ./dashboard
COPY data ./data
COPY evals ./evals
COPY .streamlit ./.streamlit

# Offline by default; set MODEL and the provider key (e.g. ANTHROPIC_API_KEY) to use an LLM
ENV MODEL=baseline/rules PYTHONUNBUFFERED=1
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["uv", "run", "--no-dev", "--frozen", "streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0"]
