"""Offline eligibility check for the on-device track.

Proves the app has no runtime network dependency except local Ollama. Scans the
whole repo for external references and confirms the only networking code targets
localhost. Exits nonzero if anything suspicious is found, so it can gate a build.

Run:  python scripts/offline_check.py
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Hosts that are allowed (local only).
LOCAL_OK = ("localhost", "127.0.0.1", "0.0.0.0")

# Folders/files to scan for external references.
SCAN_EXT = (".py", ".js", ".html", ".css", ".md", ".json")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache",
             "node_modules", "docs", "intake", "uploads"}

# An http(s) URL whose host is not local.
URL_RE = re.compile(r"https?://([^/\s\"'>)]+)", re.IGNORECASE)
# Networking imports we consider risky if used anywhere except ollama_client.py.
NET_IMPORT_RE = re.compile(
    r"^\s*(?:import|from)\s+(requests|httpx|aiohttp|socket|urllib)\b", re.MULTILINE
)

problems = []
notes = []


def is_local(host: str) -> bool:
    return any(host.startswith(h) for h in LOCAL_OK)


def scan_file(path: str, rel: str) -> None:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return

    for m in URL_RE.finditer(text):
        host = m.group(1)
        if is_local(host):
            continue
        line = text[: m.start()].count("\n") + 1
        snippet = text.splitlines()[line - 1].strip()
        # Placeholder examples in help text / comments are not runtime calls.
        placeholder = ("..." in host) or host.endswith("...")
        if placeholder or snippet.lstrip().startswith(("#", "*", "//")):
            notes.append(f"{rel}:{line}  (example/comment, not a runtime call)  {snippet[:80]}")
        else:
            problems.append(f"EXTERNAL URL  {rel}:{line}  host={host}  ->  {snippet[:80]}")

    # Networking imports outside the sanctioned Ollama client.
    if rel.endswith(".py") and not rel.replace("\\", "/").endswith("app/ollama_client.py"):
        for m in NET_IMPORT_RE.finditer(text):
            line = text[: m.start()].count("\n") + 1
            mod = m.group(1)
            problems.append(
                f"NET IMPORT    {rel}:{line}  imports '{mod}' outside ollama_client.py"
            )


def main() -> int:
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if not name.endswith(SCAN_EXT):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT)
            scan_file(path, rel)

    # Confirm the one sanctioned network target is local Ollama.
    import config
    if not any(config.OLLAMA_URL.replace("http://", "").startswith(h) for h in LOCAL_OK):
        problems.append(f"config.OLLAMA_URL is not local: {config.OLLAMA_URL}")

    print("=" * 60)
    print("OFFLINE ELIGIBILITY CHECK")
    print("=" * 60)
    print(f"Ollama target: {config.OLLAMA_URL}  (must be local)")
    print()

    if notes:
        print("Allowed (examples/comments, not runtime calls):")
        for n in notes:
            print("  -", n)
        print()

    if problems:
        print("PROBLEMS FOUND (would break offline / on-device eligibility):")
        for p in problems:
            print("  !!", p)
        print()
        print("RESULT: FAIL")
        return 1

    print("No external network dependencies found in scanned code.")
    print("The only outbound call is to local Ollama.")
    print("RESULT: PASS  (safe for network-disabled demo)")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    sys.exit(main())
