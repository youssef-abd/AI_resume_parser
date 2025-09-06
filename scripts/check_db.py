#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# Ensure 'app' package is importable when running from scripts/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Minimal .env loader to avoid needing app.settings locally

def load_database_url() -> str:
    # Prefer environment variable
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    # Fallback to .env in project root
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "DATABASE_URL":
                    return v.strip()
    return ""


def main() -> int:
    url = load_database_url()
    if not url:
        print(json.dumps({
            "ok": False,
            "error": "DATABASE_URL is not set. Put it in .env or export it in the environment.",
        }, ensure_ascii=False, indent=2))
        return 2

    try:
        engine = create_engine(url, future=True)
        with engine.connect() as conn:
            ver = conn.execute(text("SELECT version()")); version = ver.scalar()
            vec = conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")); has_vector = bool(vec.scalar())
            resumes = conn.execute(text("SELECT to_regclass('public.resumes')")); has_resumes = resumes.scalar() is not None
            jobs = conn.execute(text("SELECT to_regclass('public.jobs')")); has_jobs = jobs.scalar() is not None
            conn.execute(text("SELECT 1"))
        out = {
            "ok": True,
            "version": version,
            "has_vector": has_vector,
            "tables": {
                "resumes": has_resumes,
                "jobs": has_jobs,
            },
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({
            "ok": False,
            "error": str(e),
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
