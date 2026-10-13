import json
import urllib.request

CHUNK = 500


def safe(v):
    s = str(v if v is not None else "")
    return "'" + s if s.startswith(("=", "+", "-", "@")) else s


def table(rows):
    """Header + rows as a list of lists of strings (formula-safe)."""
    cols = list(rows[0].keys()) if rows else []
    return [[safe(c) for c in cols]] + [[safe(r.get(c, "")) for c in cols] for r in rows]


def push(url, secret, rows, sheet="prices", opener=None, timeout=60):
    """Replaces the sheet's content in chunks (first chunk clears, the others append). Raises on any refusal."""
    if not url.startswith("https://"):
        raise ValueError("webhook url must be https")
    data = table(rows)
    opener = opener or urllib.request.build_opener()
    for i in range(0, len(data), CHUNK):
        body = {"secret": secret, "sheet": sheet, "mode": "replace" if i == 0 else "append", "rows": data[i:i + CHUNK]}
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with opener.open(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8") or "{}")
        if not res.get("ok"):
            raise RuntimeError("sheet refused the upload: %s" % res.get("error", "unknown"))
    return len(data) - 1
