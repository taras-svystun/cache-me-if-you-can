"""S5 regex side: run the regex guard on the same 10 made-up rows as the Gemma guard."""
import ast
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from gateway.guard import scan  # noqa: E402

# Read EXAMPLES from the Gemma script without importing mlx.
src = (ROOT / "scripts" / "gemma_guard.py").read_text()
EXAMPLES = next(ast.literal_eval(n.value) for n in ast.parse(src).body
                if isinstance(n, ast.Assign) and n.targets[0].id == "EXAMPLES")
correct = 0
for text, expected in EXAMPLES:
    t0 = time.perf_counter()
    found = scan(text)
    us = (time.perf_counter() - t0) * 1e6
    ok = bool(found) == expected
    correct += ok
    print(f"{'OK  ' if ok else 'MISS'} expected={'PII  ' if expected else 'clean'} "
          f"found={found or '-'} {us:.0f} us | {text}")
print(f"\nregex: {correct}/{len(EXAMPLES)} correct")
