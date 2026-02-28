from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    out = subprocess.check_output([sys.executable, str(ROOT / 'scripts' / 'render_system_delivery_index.py')], text=True)
    assert 'OK_V69_SYSTEM_DELIVERY_PORTAL=' in out
    assert (ROOT / 'docs' / 'SYSTEM_FINAL_DELIVERY.md').exists()
    assert (ROOT / 'docs' / 'SYSTEM_DELIVERY_INDEX.md').exists()
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'SYSTEM_FINAL_DELIVERY.md' in readme
    assert 'SYSTEM_DELIVERY_INDEX.md' in readme
    print('OK_V69_SYSTEM_PORTAL_SMOKE')

if __name__ == '__main__':
    main()
