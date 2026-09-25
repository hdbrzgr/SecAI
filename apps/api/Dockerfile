# Two images from one file:
#   --target api     the FastAPI server
#   --target worker  the scan worker, with Nuclei and its templates
ARG NUCLEI_VERSION=v3.11.1

FROM python:3.13-slim AS build
RUN pip install --no-cache-dir "uv>=0.8,<0.9"
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .

FROM projectdiscovery/nuclei:${NUCLEI_VERSION} AS nuclei
# Templates are fetched at build time; rebuild the image to update them.
RUN nuclei -update-templates -ud /opt/nuclei-templates -duc -silent \
    && test -d /opt/nuclei-templates/http

FROM python:3.13-slim AS api
RUN useradd --system --uid 10001 --home /app secai
WORKDIR /app
COPY --from=build --chown=secai:secai /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER secai
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

FROM api AS worker
USER root
COPY --from=nuclei /usr/local/bin/nuclei /usr/local/bin/nuclei
# Nuclei keeps its config and cache under $HOME, which must be writable.
RUN mkdir -p /home/secai && chown secai:secai /home/secai
COPY --from=nuclei --chown=secai:secai /opt/nuclei-templates /opt/nuclei-templates
USER secai
# Web templates only (CVEs, exposures, misconfigurations, technologies); the scanner also
# excludes dos, fuzz, brute-force and intrusive tags.
ENV HOME=/home/secai SECAI_NUCLEI_PATH=/usr/local/bin/nuclei SECAI_NUCLEI_TEMPLATES=/opt/nuclei-templates/http
CMD ["arq", "app.worker.WorkerSettings"]
