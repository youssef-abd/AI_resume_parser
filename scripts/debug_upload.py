#!/usr/bin/env python3
import argparse
import io
import json
import os
import sys
import textwrap
from typing import Any, Dict, List, Tuple

import requests


def print_header(title: str) -> None:
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)


def print_resp(label: str, r: requests.Response) -> None:
    print(f"[{label}] {r.request.method} {r.request.url}")
    print(f"-> {r.status_code} {r.reason}")
    # Show key headers
    hdrs = {k.lower(): v for k, v in r.headers.items()}
    for k in [
        "content-type",
        "access-control-allow-origin",
        "access-control-allow-credentials",
        "access-control-allow-methods",
        "vary",
        "x-request-id",
        "x-proxied-path",
        "server",
        "date",
    ]:
        if k in hdrs:
            print(f"{k}: {hdrs[k]}")
    # Show body (truncate)
    text = r.text
    if not text:
        return
    print("body:")
    if len(text) > 800:
        print(text[:800] + "\n...<truncated>...")
    else:
        print(text)
    # Try JSON pretty
    try:
        js = r.json()
        print("json:")
        print(json.dumps(js, indent=2)[:2000])
    except Exception:
        pass


def mk_bytes(size: int, fill: bytes = b"x") -> bytes:
    return (fill * (size // len(fill) + 1))[:size]


def main() -> None:
    p = argparse.ArgumentParser(description="Debug upload endpoints")
    p.add_argument("--base", default=os.getenv("DEBUG_BASE", "http://127.0.0.1:8000"), help="Base API URL (e.g., https://<space>/api or http://127.0.0.1:8000)")
    p.add_argument("--origin", default=None, help="Origin header to send (optional)")
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--skip-multi", action="store_true")
    args = p.parse_args()

    base = args.base.rstrip("/")
    sess = requests.Session()
    headers: Dict[str, str] = {}
    if args.origin:
        headers["Origin"] = args.origin

    print_header("Health checks")
    try:
        r = sess.get(f"{base}/health", headers=headers, timeout=args.timeout)
        print_resp("health", r)
    except Exception as e:
        print(f"health error: {e}")
    try:
        r = sess.get(f"{base}/readyz", headers=headers, timeout=args.timeout)
        print_resp("readyz", r)
    except Exception as e:
        print(f"readyz error: {e}")

    # If user passed the public Space /api as base, preflight makes sense
    if args.origin:
        print_header("CORS preflight /upload_resume")
        try:
            r = sess.options(
                f"{base}/upload_resume",
                headers={
                    **headers,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
                timeout=args.timeout,
            )
            print_resp("preflight", r)
        except Exception as e:
            print(f"preflight error: {e}")

    print_header("Single upload /upload_resume (PDF)")
    files = {
        "file": ("test.pdf", io.BytesIO(mk_bytes(128)), "application/pdf"),
    }
    data = {"candidate_name": "Alice"}
    try:
        r = sess.post(f"{base}/upload_resume", headers=headers, files=files, data=data, timeout=args.timeout)
        print_resp("upload_resume", r)
    except Exception as e:
        print(f"upload_resume error: {e}")

    if not args.skip_multi:
        print_header("Multi upload /upload_resumes (2 PDFs)")
        files_list: List[Tuple[str, Tuple[str, io.BytesIO, str]]] = [
            ("files", ("a.pdf", io.BytesIO(mk_bytes(64)), "application/pdf")),
            ("files", ("b.pdf", io.BytesIO(mk_bytes(96)), "application/pdf")),
        ]
        data_list: List[Tuple[str, str]] = [("candidate_names", "Alice"), ("candidate_names", "Bob")]
        try:
            r = sess.post(f"{base}/upload_resumes", headers=headers, files=files_list, data=data_list, timeout=args.timeout)
            print_resp("upload_resumes", r)
        except Exception as e:
            print(f"upload_resumes error: {e}")

    print_header("Done")


if __name__ == "__main__":
    main()
