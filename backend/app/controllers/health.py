"""Healthcheck usado pelo Docker/Nginx (sem dados sensiveis)."""

from __future__ import annotations

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@bp.get("/health/ready")
def ready():
    try:
        db.s.execute(text("SELECT 1"))
    except Exception:
        return jsonify({"status": "degraded"}), 503
    return jsonify({"status": "ready"}), 200
