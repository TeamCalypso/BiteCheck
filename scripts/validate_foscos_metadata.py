import json
from pathlib import Path

folder = Path("data/corpus/fssai/recalls")
files = list(folder.glob("*.md.metadata.json"))

required = {"issuer", "docType", "category", "date"}
valid_doc_types = {"recall", "alert", "regulation", "judgment", "lab_report", "guideline"}

errors = []

for path in files:
    meta = json.loads(path.read_text(encoding="utf-8"))

    missing = required - set(meta)
    if missing:
        errors.append(f"{path.name}: missing {sorted(missing)}")

    if meta.get("docType") not in valid_doc_types:
        errors.append(f"{path.name}: invalid docType {meta.get('docType')!r}")

    if len(path.read_text(encoding="utf-8").encode("utf-8")) > 1024:
        errors.append(f"{path.name}: metadata exceeds 1KB")

print(f"Files checked: {len(files)}")

if len(files) != 205:
    errors.append(f"Expected 205 metadata files, found {len(files)}")

if errors:
    print("VALIDATION FAILED")
    for error in errors:
        print(" -", error)
else:
    print("VALIDATION PASSED")
