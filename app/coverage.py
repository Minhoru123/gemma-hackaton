"""Coverage maps: seed a checklist of contentions from an opposing filing so a
responsive draft can be gated on answering every one. Checking boxes is a
human act; the verifier only enforces that none are left unchecked."""

import re

_HEADING_RE = re.compile(r"^\s*(?:[IVXLC]+|\d+|[A-Z])\.\s+(\S.*)$")
_UNCHECKED_RE = re.compile(r"^- \[ \] (.+)$", re.MULTILINE)


def _is_shouted(line: str) -> bool:
    letters = [ch for ch in line if ch.isalpha()]
    return (len(letters) >= 8 and all(ch.isupper() for ch in letters)
            and len(line.split()) >= 2)


def seed_map(parent_text: str, parent_name: str = "parent filing") -> str:
    """Extract heading-like lines (numbered/lettered headings, ALL-CAPS lines)
    from the parent filing into a markdown checklist."""
    items, seen = [], set()
    for raw in parent_text.splitlines():
        line = raw.strip()
        m = _HEADING_RE.match(line)
        text = m.group(1).strip() if m else (line if _is_shouted(line) else "")
        if text and text not in seen:
            seen.add(text)
            items.append(text)
    body = "\n".join(f"- [ ] {t}" for t in items)
    return (f"# Coverage map — {parent_name}\n\n"
            "Check each box once the responsive draft answers the contention.\n\n"
            f"{body}\n")


def unanswered(map_text: str) -> list[str]:
    """Unchecked items in a coverage map."""
    return [m.strip() for m in _UNCHECKED_RE.findall(map_text)]
