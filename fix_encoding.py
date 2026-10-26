"""Sanitize all source files in workspace to pure UTF-8."""
import pathlib

root = pathlib.Path(".")
replacements = [
    (b"\x96", b"--"),
    (b"\x97", b"---"),
    (b"\x91", b"'"),
    (b"\x92", b"'"),
    (b"\x93", b'"'),
    (b"\x94", b'"'),
    (b"\x85", b"..."),
    (b"\xb7", b" - "),
    (b"\xd7", b"x"),
    (b"\x95", b"*"),
    (b"\xa0", b" "),
]

fixed = []
errors = []

for ext in ["*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml"]:
    for p in root.rglob(ext):
        if ".pytest_cache" in str(p) or "__pycache__" in str(p) or ".git" in str(p):
            continue
        raw = p.read_bytes()
        modified = raw
        for bad, good in replacements:
            modified = modified.replace(bad, good)
        if modified != raw:
            p.write_bytes(modified)
            fixed.append(str(p))

        # Test decode
        try:
            p.read_bytes().decode("utf-8")
        except UnicodeDecodeError as e:
            # Let's decode as cp1252 and re-encode as clean utf-8
            try:
                decoded = raw.decode("cp1252")
                p.write_text(decoded, encoding="utf-8")
                fixed.append(f"{p} (via cp1252 re-encode)")
            except Exception as e2:
                errors.append((str(p), str(e2)))

print(f"Processed files.")
if errors:
    print("\nRemaining errors:")
    for fn, err in errors:
        print(f"  ! {fn}: {err}")
else:
    print("\nAll files are now clean, 100% valid UTF-8!")
