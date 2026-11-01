# syntax=docker/dockerfile:1
# Default image: gateway + Claude adapter. The embedding model needs the `embed` extra
# (PyTorch): build with  --build-arg EXTRAS=gateway,anthropic,embed  and a CPU wheel index:
#   --build-arg PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu
FROM python:3.15-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /wheels

FROM python:3.15-slim
ARG EXTRAS=gateway,anthropic
ARG PIP_EXTRA_INDEX_URL=
ENV PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL} PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    CASCADE_DB_PATH=/data/audit.db CASCADE_ARTIFACT_DIR=/artifact
RUN useradd --create-home --uid 10001 app && mkdir /data /artifact && chown app /data
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir "$(ls /wheels/*.whl)[${EXTRAS}]" && rm -rf /wheels
USER app
WORKDIR /home/app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/healthz')" || exit 1
CMD ["uvicorn", "--factory", "cascade.artifact:create_app_from_env", "--host", "0.0.0.0", "--port", "8080"]
