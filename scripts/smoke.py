"""S0.5 smoke test: one tiny Haiku call and the model list, through the SSL_CERT_FILE fix."""
import os
from pathlib import Path

import anthropic

for line in Path(".env").read_text().splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

client = anthropic.Anthropic()
ids = {m.id for m in client.models.list(limit=100)}
for want in ("claude-haiku-5-5", "claude-sonnet-5-5"):
    print(want, "listed" if want in ids else "MISSING")

r = client.messages.create(model="claude-haiku-5-5", max_tokens=5,
                           messages=[{"role": "user", "content": "Say hi"}])
print("reply:", r.content[0].text if r.content else "", "| usage:", r.usage)
