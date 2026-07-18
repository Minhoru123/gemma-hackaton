"""Presumptive deadlines: when a filing of a known type lands, the rules table
says what it triggers and in how many days. Every date this module produces is
PRESUMPTIVE — labeled as such everywhere it appears, never treated as
authoritative. The count ignores service method, weekends, holidays, and local
variations; only a human (or their attorney) can confirm the real date."""

import json
import datetime
import config
from app import obligations, timeline

PRESUMPTIVE_NOTE = "PRESUMPTIVE — confirm with the court or your attorney"


def load_rules() -> list[dict]:
    with open(config.DEADLINE_RULES, "r", encoding="utf-8") as f:
        return json.load(f)


def apply(doc_type: str, filed_date: str, source_name: str) -> list[dict]:
    """Create presumptive obligations triggered by this filing. filed_date is
    ISO (YYYY-MM-DD); falls back to today if missing. Returns created items."""
    filed_date = filed_date or datetime.date.today().isoformat()
    created = []
    for rule in load_rules():
        if rule["trigger_doc_type"] != doc_type:
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
