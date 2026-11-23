"""S5 local guard: Gemma 4 E4B (4-bit, MLX) checks requests for personal data.

Runs outside the Claude Code sandbox, because the sandbox hides the GPU (Metal) from MLX.
Prints each step with timings, streams the model's answers live, and saves results to
results/guard_gemma.json for the regex comparison in S5.

Run: see README.md, section "S5 Gemma guard".
"""

import json
import time
from pathlib import Path

MODEL = "mlx-community/gemma-4-e4b-it-4bit"
OUT = Path("results/guard_gemma.json")

# Made-up examples. expected = True when the text holds personal data.
EXAMPLES = [
    ("Summarise our Q3 refund policy in three bullet points.", False),
    ("Call Marie Dupont at 06 12 34 56 78 about her claim.", True),
    ("Client IBAN FR76 3000 6000 0112 3456 7890 189, please draft a payment reminder.", True),
    ("What is the capital of Australia?", False),
    ("Write a reply to jean.martin@example.fr saying his order shipped.", True),
    ("Explain the difference between an exact cache and a semantic cache.", False),
    ("Patient born 14/03/1987, diagnosed with type 2 diabetes, suggest a diet plan.", True),
    ("Translate 'the meeting moved to Thursday' into French.", False),
    ("Emmanuel Macron gave a speech on AI today; summarise the main points.", False),
    ("My colleague Paul lives at 12 rue des Lilas, Grenoble; write him a birthday card.", True),
]

PROMPT = (
    "You are a data-protection filter. Does the text below contain personal data about a private "
    "person (name with contact details, phone, email, address, bank account, ID number, health "
    "data)? Public figures in public roles do not count.\n"
    "Answer on one line: YES or NO, then a dash and the data types found.\n\nText: {text}"
)


def log(msg: str, t0: float) -> None:
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


def main() -> None:
    t0 = time.time()
    log("importing mlx (needs the GPU via Metal)...", t0)
    import mlx.core as mx
    from mlx_lm import load, stream_generate

    log(f"device: {mx.default_device()}", t0)
    log(f"loading {MODEL} from ./.cache ...", t0)
    t = time.time()
    model, tok = load(MODEL)
    load_s = time.time() - t
    log(f"model loaded in {load_s:.1f}s", t0)

    rows, correct = [], 0
    for i, (text, expected) in enumerate(EXAMPLES, 1):
        print(f"\n--- {i}/{len(EXAMPLES)} expected={'PII' if expected else 'clean'}")
        print(f"text:   {text}")
        prompt = tok.apply_chat_template(
            [{"role": "user", "content": PROMPT.format(text=text)}],
            add_generation_prompt=True,
            tokenize=False,
        )
        print("gemma:  ", end="", flush=True)
        t, answer = time.time(), ""
        for chunk in stream_generate(model, tok, prompt=prompt, max_tokens=30):
            print(chunk.text, end="", flush=True)
            answer += chunk.text
        secs = time.time() - t
        got = answer.strip().upper().startswith("YES")
        ok = got == expected
        correct += ok
        print(f"\nresult: {'OK  ' if ok else 'MISS'} ({secs:.2f}s)")
        rows.append({"text": text, "expected": expected, "got": got, "answer": answer.strip(),
                     "seconds": round(secs, 3)})

    avg = sum(r["seconds"] for r in rows) / len(rows)
    print(f"\n=== {correct}/{len(EXAMPLES)} correct, {avg:.2f}s per request on average, "
          f"load {load_s:.1f}s ===")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"model": MODEL, "load_seconds": round(load_s, 1), "rows": rows},
                              indent=2, ensure_ascii=False))
    log(f"saved {OUT}", t0)


if __name__ == "__main__":
    main()
