import pathlib, re, sys

ROOTS = ["src", "tests", "examples", "scripts"]
MAP = {
    "‘": "'", "’": "'", "‚": "'",
    "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "→": "->", "➜": "->",
    "±": "+/-", "…": "...",
    "′": "'", "″": "'",
    "🚨": "[ALERT]", "✅": "[OK]",
    "🤖": "[ROBOT]", "🔑": "[KEY]", "🧪": "[TEST]", "📦": "[PACKAGE]",
    "📤": "[OUTBOX]", "📨": "[INBOX]", "🆔": "[ID]", "📬": "[MAILBOX]", "❌": "[CROSS]"
}
REMOVE = ["\u200b", "\u200c", "\u200d", "\ufeff"]  # zero-width + BOM
RE_NON_ASCII = re.compile(r"[^\x00-\x7F]")

def fix_text(s: str) -> str:
    for k, v in MAP.items():
        s = s.replace(k, v)
    for z in REMOVE:
        s = s.replace(z, "")
    # NBSP -> space
    s = s.replace("\u00a0", " ")
    # Fallback for U+FFFD
    s = s.replace("\ufffd", "'")
    return s

def main() -> int:
    changed = 0
    script_path = pathlib.Path(__file__).resolve()
    for root in ROOTS:
        for p in pathlib.Path(root).rglob("*.py"):
            if p.resolve() == script_path:
                continue
            try:
                orig = t = p.read_text(encoding="utf-8", errors="strict")
                t2 = fix_text(t)
                if t2 != t:
                    p.write_text(t2, encoding="utf-8", newline="")
                    changed += 1
            except UnicodeDecodeError as e:
                print(f"Error reading {p}: {e}")
                continue
    print(f"Sanitized {changed} file(s).")
    # Final check: fail if anything non-ASCII remains
    offenders = []
    for root in ROOTS:
        for p in pathlib.Path(root).rglob("*.py"):
            if p.resolve() == script_path:
                continue
            try:
                for i, line in enumerate(p.read_text(encoding="utf-8", errors="strict").splitlines(), 1):
                    if RE_NON_ASCII.search(line):
                        offenders.append(f"{p}:{i}: {line}")
            except UnicodeDecodeError as e:
                print(f"Error reading {p} for final check: {e}")
                continue
    if offenders:
        print("Non-ASCII remains:\n" + "\n".join(offenders))
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())

