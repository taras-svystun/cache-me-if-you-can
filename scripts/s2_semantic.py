"""S2 demo: semantic cache hit rate and wrong hits at several thresholds, with and without the
ID guard. No API calls: we only need which cached question is nearest, and whether its answer
is right for the new question (the label)."""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from gateway.semantic import SemanticCache, ids  # noqa: E402

originals = [q for q in json.loads((ROOT / "data" / "queries.json").read_text())
             if q["kind"] == "original"]
cache = SemanticCache()
for q in originals:
    cache.put("acme", q["q"], f"answer#{q['id']}")
cache.put("acme", "What is the 2025 return policy for Nimbus?", "answer#2025")

# (question, right_match): a hit is correct only if the nearest cached question is right_match.
# Traps have right_match None: any hit is wrong.
tests = [
    ("How many days do I have to return my Nimbus e-bike?", "What is the return window for a Nimbus e-bike?"),
    ("Is a flat tyre covered by the Nimbus warranty?", "Does the Nimbus warranty cover a flat tyre?"),
    ("How many days does delivery to Lyon take with Nimbus?", "How long does Nimbus shipping take to Lyon?"),
    ("After shipping, can a Nimbus order still be cancelled?", "Can I cancel a Nimbus order after it ships?"),
    ("Does Nimbus sell apple watch mounts?", "Does Nimbus sell Apple Watch mounts?"),
    ("Does the Nimbus warranty cover a cracked frame?", None),
    ("What does policy AB13 say about theft?", None),
    ("What does policy Ab12 say about theft?", None),
    ("What battery does the Nimbus Trail model use?", None),
    ("How long does Nimbus shipping take to Berlin?", None),
    ("Can I cancel a Nimbus order before it ships?", None),
    ("Is there a senior discount at Nimbus?", None),
    ("What is the 2024 return policy for Nimbus?", None),
]
rows, times = [], []
for q, want in tests:
    sim, near, _, ms = cache.nearest("acme", q)
    ok = near == want
    times.append(ms)
    guard_pass = ids(near) == ids(q)
    rows.append((q, ok, sim, near, guard_pass))
    print(f"{'OK  ' if ok else 'WRONG' if want else 'TRAP'} sim={sim:.3f} guard={'pass' if guard_pass else 'BLOCK'} "
          f"| {q!r} -> {near!r}")

print("\nthreshold | guard | right hits (of 5) | wrong hits")
for th in (0.95, 0.90, 0.85, 0.80, 0.75, 0.70):
    for guard in (False, True):
        hit = [r for r in rows if r[2] >= th and (r[4] or not guard)]
        right = sum(r[1] for r in hit)
        print(f"   {th:.2f}   | {'on ' if guard else 'off'}  | {right} | {len(hit) - right}")
print(f"\nembed latency per query (CPU): median {statistics.median(times):.1f} ms, "
      f"max {max(times):.1f} ms")
