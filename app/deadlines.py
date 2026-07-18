"""Presumptive deadlines: when a filing of a known type lands, the rules table
says what it triggers and in how many days. Every date this module produces is
PRESUMPTIVE — labeled as such everywhere it appears, never treated as
authoritative. The count ignores service method, weekends, holidays, and local
variations; only a human (or their attorney) can confirm the real date.

A case is governed by ONE rule set. Each rule carries a "jurisdiction" tag
('utah' or 'federal'), and apply() only fires rules whose tag matches the
case's jurisdiction — never both. While the jurisdiction is still unknown
(''), no tagged rule fires: computing a deadline from the wrong court's rules
is worse than computing none. Untagged rules (no "jurisdiction" key) fire only
while the jurisdiction is unknown, preserving legacy generic-rules behavior."""

import json
import datetime
import config
from app import obligations, timeline, dates

PRESUMPTIVE_NOTE = "PRESUMPTIVE — confirm with the court or your attorney"


def load_rules() -> list[dict]:
    with open(config.DEADLINE_RULES, "r", encoding="utf-8") as f:
        return json.load(f)


def apply(doc_type: str, filed_date: str, source_name: str,
          jurisdiction: str = "", origin: str = "") -> list[dict]:
    """Create presumptive obligations triggered by this filing. filed_date is
    ISO (YYYY-MM-DD); falls back to today if missing. Only rules matching the
    case's jurisdiction fire (see module docstring). origin is who filed the
    trigger relative to the user ('user' | 'opponent' | '' unknown): the user's
    own filing creates the OTHER side's duty to respond, not the user's, so
    origin='user' fires nothing. Unknown origin fires — a spurious to-do beats
    a silently missed deadline. Returns created items."""
    if origin == "user":
        return []
    # Semantic guard: a malformed or impossible date must never reach the
    # calendar arithmetic below (timedelta handles month/year rollover).
    filed_date = dates.valid_iso(filed_date) or datetime.date.today().isoformat()
    created = []
    for rule in load_rules():
        if rule["trigger_doc_type"] != doc_type:
            continue
        if rule.get("jurisdiction", "") != jurisdiction:
            continue
        due = (datetime.date.fromisoformat(filed_date)
               + datetime.timedelta(days=rule["days"])).isoformat()
        label = rule["obligation"].replace("{source}", source_name)
        obligations.add(label, trigger_source=source_name, due_date=due,
                        presumptive=True, rule_cite=rule["rule_cite"],
                        satisfied_by=rule["satisfied_by"])
        timeline.add_event(
            "presumptive_deadline",
            f"{label} ({PRESUMPTIVE_NOTE}; {rule['rule_cite']})", due)
        created.append({"label": label, "due_date": due,
                        "rule_cite": rule["rule_cite"]})
    return created
