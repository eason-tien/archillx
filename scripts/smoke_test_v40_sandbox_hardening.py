from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    required = [
        ROOT / "deploy/docker/seccomp/archillx-seccomp.json",
        ROOT / "deploy/apparmor/archillx-sandbox.profile",
    ]
    for path in required:
        data = path.read_text(encoding="utf-8").strip()
        assert data
    print("OK_V40_SANDBOX_HARDENING_SMOKE")


if __name__ == "__main__":
    main()
