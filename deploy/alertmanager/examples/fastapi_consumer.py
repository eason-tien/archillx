from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

from common_payload import PayloadValidationError, build_alert_records

app = FastAPI(title="Archillx Alert Webhook Consumer")


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/alert")
async def alert(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - template example
        raise HTTPException(status_code=400, detail={"code": "INVALID_JSON", "message": str(exc)})

    try:
        normalized = build_alert_records(payload)
    except PayloadValidationError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PAYLOAD", "message": str(exc)})
    except Exception as exc:  # pragma: no cover - template example
        raise HTTPException(status_code=500, detail={"code": "CONSUMER_ERROR", "message": str(exc)})

    return {"ok": True, "normalized": normalized}
