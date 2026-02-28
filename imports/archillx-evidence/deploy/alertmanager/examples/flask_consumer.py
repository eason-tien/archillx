from __future__ import annotations

from flask import Flask, jsonify, request

from common_payload import PayloadValidationError, build_alert_records

app = Flask(__name__)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/alert")
def alert():
    try:
        payload = request.get_json(force=True)
    except Exception as exc:  # pragma: no cover - template example
        return jsonify({"ok": False, "detail": {"code": "INVALID_JSON", "message": str(exc)}}), 400

    try:
        normalized = build_alert_records(payload)
    except PayloadValidationError as exc:
        return jsonify({"ok": False, "detail": {"code": "INVALID_PAYLOAD", "message": str(exc)}}), 400
    except Exception as exc:  # pragma: no cover - template example
        return jsonify({"ok": False, "detail": {"code": "CONSUMER_ERROR", "message": str(exc)}}), 500

    return {"ok": True, "normalized": normalized}
