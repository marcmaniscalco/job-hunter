# Image for the backend: serves the FastAPI app in the cluster, and will run
# the Greenhouse poller as a CronJob starting Phase 2 (same image, a different
# command).
#
# python:3.13-slim keeps the image small. We `pip install .` the package the
# same way PyPI consumers would, rather than the `-e` (editable) install the
# local dev venv uses, so the image contains a real, self-sufficient copy of
# the code instead of relying on a mounted source tree.
FROM python:3.13-slim

WORKDIR /app

# Copy dependency-relevant files first so Docker can cache this layer and skip
# reinstalling packages on rebuilds that only change application code.
COPY pyproject.toml ./
COPY app ./app
COPY pollers ./pollers

RUN pip install --no-cache-dir .

# Alembic ships in the image too: the Deployment's initContainer (see
# k8s/backend/deployment.yaml) runs `alembic upgrade head` before the API
# container starts, so the schema is always current.
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

# LOG_LEVEL comes from the backend ConfigMap; defaults to info so the image
# also works with a plain `docker run` for a quick local smoke test.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level ${LOG_LEVEL:-info}"]
