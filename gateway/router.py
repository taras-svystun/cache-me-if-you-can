"""Router: pick the model per request. Two versions to compare.
- rules: free and instant; 'hard' if the text asks for arithmetic, comparison or writing, or is long.
- haiku: one extra Haiku call that answers 'simple' or 'hard'.
When unsure, both lean to Sonnet: a hard task on Haiku costs more (a wrong answer) than a simple
task on Sonnet (overpaying)."""
import re

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
HARD_WORDS = re.compile(r"\b(how much|calculate|compare|which .* (fit|should)|write|draft|explain|"
                        r"am i covered)\b", re.I)


def route_rules(text: str) -> str:
    return SONNET if HARD_WORDS.search(text) or len(text) > 140 else HAIKU


CLASSIFIER_SYSTEM = (
    "You route customer questions for an e-bike shop. Reply with one word: simple or hard.\n"
    "simple = the answer is one fact from the policy.\n"
    "hard = needs several policy sections, arithmetic, judgment about the customer's case, or "
    "writing a message. If unsure, reply hard.")


def route_haiku(text: str, client) -> tuple[str, object]:
    r = client.messages.create(model=HAIKU, max_tokens=5, system=CLASSIFIER_SYSTEM,
                               thinking={"type": "disabled"},
                               messages=[{"role": "user", "content": text}])
    word = "".join(b.text for b in r.content if b.type == "text").strip().lower()
    return (HAIKU if word.startswith("simple") else SONNET), r.usage
