import csv
import json
import os


def read_rows(path, key="sku"):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or key not in rows[0]:
        raise ValueError("column %r not found in %s" % (key, path))
    return rows


def index(rows, key):
    """key -> row. Returns (index, problems): empty keys and repeated keys are reported, the first row wins."""
    idx, problems = {}, []
    for n, r in enumerate(rows, start=2):
        k = (r.get(key) or "").strip()
        if not k:
            problems.append("row %d: empty %s" % (n, key))
        elif k in idx:
            problems.append("row %d: repeated %s %s (ignored)" % (n, key, k))
        else:
            idx[k] = r
    return idx, problems


def diff(old_rows, new_rows, key="sku", watch=("price", "stock")):
    old, p1 = index(old_rows, key)
    new, p2 = index(new_rows, key)
    added = [new[k] for k in new if k not in old]
    removed = [old[k] for k in old if k not in new]
    changed = []
    for k in new:
        if k in old:
            for col in watch:
                a, b = (old[k].get(col) or "").strip(), (new[k].get(col) or "").strip()
                if a != b:
                    changed.append({"key": k, "name": new[k].get("name", ""), "field": col, "old": a, "new": b})
    return {"added": added, "removed": removed, "changed": changed, "problems": p1 + p2}


def report(d, key="sku", limit=100):
    lines = ["# What changed", "", "Added: %d. Removed: %d. Changed values: %d." % (len(d["added"]), len(d["removed"]), len(d["changed"])), ""]
    if d["changed"]:
        lines += ["## Changed", "", "| %s | name | field | old | new |" % key, "|---|---|---|---|---|"]
        lines += ["| %s | %s | %s | %s | %s |" % tuple(str(c[x]).replace("|", "/") for x in ("key", "name", "field", "old", "new")) for c in d["changed"][:limit]]
    for title, items in (("Added", d["added"]), ("Removed", d["removed"])):
        if items:
            lines += ["", "## %s (first %d)" % (title, limit), ""] + ["- %s %s" % (r.get(key, ""), r.get("name", "")) for r in items[:limit]]
    if d["problems"]:
        lines += ["", "## Problems in the files", ""] + ["- " + p for p in d["problems"][:limit]]
    return "\n".join(lines) + "\n"


def load_snapshot(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    os.replace(tmp, path)
