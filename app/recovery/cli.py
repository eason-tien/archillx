from __future__ import annotations

import argparse
import os

from ..config import settings
from .supervisor import RecoverySupervisor


def main() -> int:
    p = argparse.ArgumentParser(description="ArcHillx recovery controller")
    p.add_argument("--force", action="store_true", help="force takeover")
    p.add_argument("--offline", action="store_true", help="offline dependency repair")
    p.add_argument("--once", action="store_true", help="single check+run then exit")
    p.add_argument("--lock-backend", choices=["file", "redis"], default=None)
    p.add_argument("--redis-url", default=None)
    args = p.parse_args()

    if args.lock_backend:
        settings.recovery_lock_backend = args.lock_backend
    if args.redis_url:
        settings.redis_url = args.redis_url
        os.environ["REDIS_URL"] = args.redis_url

    sup = RecoverySupervisor(
        force_takeover=args.force or settings.recovery_force_takeover,
        offline=args.offline or settings.recovery_offline,
        once=args.once or settings.recovery_once,
    )
    return sup.run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
