"""S0.5 smoke test: one tiny Haiku call and the model list, through the SSL_CERT_FILE fix."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gateway.proxy import client  # noqa: E402

ids = {m.id for m in client().models.list(limit=100)}
for want in ("claude-haiku-5-5", "claude-sonnet-5-5"):
    print(want, "listed" if want in ids else "MISSING")

r = client().messages.create(model="claude-haiku-5-5", max_tokens=5,
                             messages=[{"role": "user", "content": "Say hi"}])
print("reply:", r.content[0].text if r.content else "", "| usage:", r.usage)
