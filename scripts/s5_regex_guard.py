"""S5 regex side: run the regex guard on the same 14 made-up rows as the Gemma guard."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from gateway.guard import scan  # noqa: E402

rows = json.loads((ROOT / "data" / "guard_rows.json").read_text())
correct = 0
for r in rows:
    t0 = time.perf_counter()
    found = scan(r["text"])
    us = (time.perf_counter() - t0) * 1e6
    ok = bool(found) == r["pii"]
    correct += ok
    print(f"{'OK  ' if ok else 'MISS'} {'seen  ' if r['seen'] else 'unseen'} "
          f"expected={'PII  ' if r['pii'] else 'clean'} found={found or '-'} {us:.0f} us | {r['text']}")
print(f"\nregex: {correct}/{len(rows)} correct")
