from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.request import urlopen


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _emit(
    domain: str,
    action: str,
    status: str,
    summary: str,
    started_at: str,
    details: list[str] | None = None,
    error: str | None = None,
) -> str:
    return json.dumps(
        {
            "service": "locust",
            "domain": domain,
            "action": action,
            "target": "service",
            "status": status,
            "summary": summary,
            "details": details or [],
            "destructive": False,
            "started_at": started_at,
            "completed_at": _now(),
            "artifacts": [],
            "next_steps": [],
            "error": error,
        }
    )


def _probe() -> tuple[bool, str]:
    try:
        with urlopen("http://localhost:8089/", timeout=5) as response:
            return (200 <= response.status < 400), f"Locust UI HTTP {response.status}"
    except URLError as exc:
        return False, f"Locust UI unreachable: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Locust platform adapter")
    parser.add_argument("domain")
    parser.add_argument("action")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args()

    started_at = _now()

    if (args.domain, args.action) in {("service", "status"), ("service", "health")}:
        ok, summary = _probe()
        print(_emit(args.domain, args.action, "ok" if ok else "error", summary, started_at))
        return 0 if ok else 1

    if (args.domain, args.action) == ("service", "logs"):
        print(
            _emit(
                args.domain,
                args.action,
                "ok",
                "Use docker compose logs for locust logs",
                started_at,
                ["docker compose -f docker-compose.yml -f docker-compose.apps.yml logs locust"],
            )
        )
        return 0

    if (args.domain, args.action) in {("verify", "preflight"), ("seed", "generate-users")}:
        cmd = ["uv", "run", "gen-users", "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        details = [line for line in (result.stdout.strip(), result.stderr.strip()) if line]
        ok = result.returncode == 0
        summary = (
            "Command succeeded: uv run gen-users --help"
            if ok
            else f"Command failed ({result.returncode})"
        )
        print(
            _emit(
                args.domain,
                args.action,
                "ok" if ok else "error",
                summary,
                started_at,
                details,
                None if ok else summary,
            )
        )
        return 0 if ok else 1

    print(
        _emit(
            args.domain,
            args.action,
            "error",
            f"Unsupported action: {args.domain}:{args.action}",
            started_at,
        )
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
