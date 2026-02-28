FROM python:3.11-alpine

WORKDIR /sandbox
RUN adduser -D -H sandbox && mkdir -p /sandbox/run /sandbox/worker && chown -R sandbox:sandbox /sandbox
USER sandbox
ENTRYPOINT ["python", "-I", "-S", "-B", "/sandbox/worker/sandbox_worker.py"]
