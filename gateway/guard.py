"""Regex guard: finds personal data by its shape before a request leaves for the cloud.
Fast (microseconds) but blind to meaning: it sees '06 12 34 56 78', not 'diabetes'."""
import re

PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "phone_fr": r"\b0[1-9](?:[ .-]?\d{2}){4}\b",
    "iban": r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b",
    "date": r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    "street": r"\b\d{1,4},? (?:rue|avenue|boulevard|bd|chemin|place|allée) ",
}


def scan(text: str) -> list[str]:
    return [name for name, p in PATTERNS.items() if re.search(p, text, re.I)]
