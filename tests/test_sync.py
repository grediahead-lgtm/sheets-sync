import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from sheets_sync.__main__ import main  # noqa: E402
from sheets_sync.diff import diff, index, load_snapshot, read_rows, report, save_snapshot  # noqa: E402
from sheets_sync.push import CHUNK, push, safe, table  # noqa: E402

OLD = read_rows(os.path.join(ROOT, "examples", "old.csv"))
NEW = read_rows(os.path.join(ROOT, "examples", "new.csv"))


class DiffTests(unittest.TestCase):
    def test_example(self):
        d = diff(OLD, NEW)
        self.assertEqual([r["sku"] for r in d["added"]], ["A4"])
        self.assertEqual([r["sku"] for r in d["removed"]], ["A3"])
        self.assertEqual([(c["key"], c["field"], c["old"], c["new"]) for c in d["changed"]],
                         [("A1", "price", "1250", "1290"), ("A2", "stock", "3", "0")])
        self.assertEqual(len(d["problems"]), 1)

    def test_no_changes(self):
        d = diff(OLD, OLD)
        self.assertEqual((d["added"], d["removed"], d["changed"]), ([], [], []))

    def test_whitespace_is_not_a_change_and_watch_columns(self):
        a = [{"sku": "1", "price": "10", "name": "x"}]
        b = [{"sku": "1", "price": " 10 ", "name": "y"}]
        self.assertEqual(diff(a, b)["changed"], [])  # name is not watched
        self.assertEqual(len(diff(a, b, watch=("name",))["changed"]), 1)

    def test_empty_and_repeated_keys_reported(self):
        idx, problems = index([{"sku": ""}, {"sku": "a"}, {"sku": "a"}], "sku")
        self.assertEqual(list(idx), ["a"])
        self.assertEqual(len(problems), 2)

    def test_missing_key_column(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write("a,b\n1,2\n")
            with self.assertRaises(ValueError):
                read_rows(p)

    def test_report_text(self):
        txt = report(diff(OLD, NEW))
        self.assertIn("| A1 | Bed grey | price | 1250 | 1290 |", txt)
        self.assertIn("A3 Bowl steel", txt)


class SnapshotTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            self.assertIsNone(load_snapshot(p))
            save_snapshot(p, NEW)
            self.assertEqual(load_snapshot(p), NEW)
            self.assertFalse(os.path.exists(p + ".tmp"))


class PushTests(unittest.TestCase):
    def serve(self, ok=True):
        got = []

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                got.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": ok, "error": "forbidden"}).encode())

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (srv.shutdown(), srv.server_close()))
        return srv, got

    def test_table_is_formula_safe(self):
        self.assertEqual(safe("=1+1"), "'=1+1")
        t = table([{"sku": "1", "name": "=HYPERLINK(1)"}])
        self.assertEqual(t[0], ["sku", "name"])
        self.assertEqual(t[1][1], "'=HYPERLINK(1)")

    def _push(self, srv, rows, secret="s"):
        # the https check is by design; for a local server we call the lower level with a patched URL scheme
        from sheets_sync import push as mod
        import urllib.request
        url = "https://127.0.0.1:%d/exec" % srv.server_port

        class Op:
            def open(self, req, timeout=None):
                req.full_url = req.full_url.replace("https://", "http://")
                return urllib.request.build_opener().open(req, timeout=timeout)
        return mod.push(url, secret, rows, opener=Op())

    def test_chunks_replace_then_append(self):
        srv, got = self.serve()
        rows = [{"sku": str(i), "name": "n"} for i in range(CHUNK + 10)]
        self.assertEqual(self._push(srv, rows), CHUNK + 10)
        self.assertEqual([g["mode"] for g in got], ["replace", "append"])
        self.assertEqual(len(got[0]["rows"]), CHUNK)
        self.assertEqual(len(got[1]["rows"]), 11)  # CHUNK+10 rows + header - CHUNK
        self.assertEqual(got[0]["secret"], "s")

    def test_refusal_raises(self):
        srv, _ = self.serve(ok=False)
        with self.assertRaises(RuntimeError):
            self._push(srv, [{"sku": "1"}])

    def test_http_url_refused(self):
        with self.assertRaises(ValueError):
            push("http://example.com/x", "s", [{"sku": "1"}])


class CliTests(unittest.TestCase):
    def test_first_run_then_report(self):
        with tempfile.TemporaryDirectory() as d:
            snap, rep = os.path.join(d, "s.json"), os.path.join(d, "r.md")
            self.assertEqual(main([os.path.join(ROOT, "examples", "old.csv"), "--snapshot", snap, "--report", rep]), 0)
            self.assertFalse(os.path.exists(rep))  # nothing to compare on the first run
            self.assertEqual(main([os.path.join(ROOT, "examples", "new.csv"), "--snapshot", snap, "--report", rep]), 0)
            with open(rep, encoding="utf-8") as f:
                self.assertIn("Changed values: 2", f.read())

    def test_snapshot_not_updated_when_upload_fails(self):
        with tempfile.TemporaryDirectory() as d:
            snap = os.path.join(d, "s.json")
            os.environ.pop("SHEETS_SYNC_SECRET", None)
            with self.assertRaises(ValueError):
                main([os.path.join(ROOT, "examples", "old.csv"), "--snapshot", snap, "--webhook", "https://x.example/exec"])
            self.assertFalse(os.path.exists(snap))


if __name__ == "__main__":
    unittest.main()
