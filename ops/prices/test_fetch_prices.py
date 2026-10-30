import datetime as dt
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import fetch_prices as fp

NOW = dt.datetime(2026, 10, 31, 6, 45, tzinfo=dt.timezone.utc)   # a Saturday morning


def weekdays_back(n, end="2026-10-30"):
    d = dt.date.fromisoformat(end)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d -= dt.timedelta(days=1)
    return out


def payload(base, n=100, end="2026-10-30", step=0.01):
    rows = {}
    for i, d in enumerate(weekdays_back(n, end)):
        rows[d] = {"1. open": "1", "2. high": "1", "3. low": "1", "4. close": f"{base * (1 - step * i):.4f}", "5. volume": "1"}
    return {"Meta Data": {"3. Last Refreshed": end}, "Time Series (Daily)": rows}


class FakeApi:
    def __init__(self, fail=(), limit=False):
        self.fail, self.limit, self.calls = set(fail), limit, []

    def __call__(self, url):
        sym = url.split("symbol=")[1].split("&")[0]
        self.calls.append(sym)
        if self.limit or sym in self.fail:
            return {"Information": "Thank you for using Alpha Vantage! standard rate limit of 25 requests per day"}
        return payload(100.0 + len(sym))


class Unit(unittest.TestCase):
    def test_parse_and_calc(self):
        s = fp.fetch_series("GOOG", "KEY", FakeApi())
        self.assertEqual(s[0][0], "2026-10-30")
        e = fp.entry_from_series("GOOG", True, s)
        self.assertAlmostEqual(e["chg"], ((1 / (1 - 0.0))) * 0 + round((s[0][1] / s[1][1] - 1) * 100, 2), places=2)
        self.assertGreater(e["chg"], 0)             # prices fall going back, so latest is up
        self.assertEqual(len(e["series"]), 30)
        self.assertEqual(e["series"][-1], round(s[0][1], 2))

    def test_rate_limit_message_is_error_without_key(self):
        with self.assertRaises(fp.FetchError) as cm:
            fp.fetch_series("GOOG", "SECRETKEY", FakeApi(limit=True))
        self.assertNotIn("SECRETKEY", str(cm.exception))

    def test_network_error_does_not_leak_key(self):
        def boom(url):
            raise OSError("failed for " + url)
        with self.assertRaises(fp.FetchError) as cm:
            fp.fetch_series("GOOG", "SECRETKEY", boom)
        self.assertNotIn("SECRETKEY", str(cm.exception))

    def test_short_history_rejected(self):
        with self.assertRaises(fp.FetchError):
            fp.fetch_series("GOOG", "K", lambda u: payload(100, n=10))

    def test_bad_close_rejected(self):
        p = payload(100)
        p["Time Series (Daily)"]["2026-10-30"]["4. close"] = "-3"
        with self.assertRaises(fp.FetchError):
            fp.fetch_series("GOOG", "K", lambda u: p)

    def test_document_shape_and_stale_flag(self):
        api = FakeApi()
        res = {t: (o, fp.fetch_series(t, "K", api)) for t, o in fp.TICKERS}
        # make LLY one trading day older than the rest
        res["LLY"] = (False, fp.fetch_series("LLY", "K", lambda u: payload(120, end="2026-10-29")))
        doc = fp.build_document(res, None, NOW, {})
        self.assertEqual(doc["market_date"], "2026-10-30")
        self.assertEqual(doc["expected_asof"], "2026-10-30")
        self.assertFalse(doc["market_stale"])
        self.assertEqual(len(doc["dates"]), 90)
        by = {e["t"]: e for e in doc["tickers"]}
        self.assertEqual([e["t"] for e in doc["tickers"]], [t for t, _ in fp.TICKERS])
        self.assertTrue(by["LLY"]["stale"])
        self.assertFalse(by["GOOG"]["stale"])
        self.assertEqual(by["GOOG"]["idx"][0], 100.0)           # indexed to 100 at first date
        self.assertEqual(len(by["GOOG"]["idx"]), 90)
        self.assertEqual(by["NTLA"]["idx"], [])                 # watchlist has no indexed line
        self.assertEqual(by["GOOG"]["asof"], "30 Oct")

    def test_failed_ticker_carries_over_old_entry_as_stale(self):
        api = FakeApi()
        res = {t: (o, fp.fetch_series(t, "K", api)) for t, o in fp.TICKERS}
        first = fp.build_document(res, None, NOW, {})
        res2 = {t: v for t, v in res.items() if t != "MRNA"}
        again = fp.build_document(res2, first, NOW, {"MRNA": "rate limit"})
        m = {e["t"]: e for e in again["tickers"]}["MRNA"]
        self.assertEqual(m["last"], {e["t"]: e for e in first["tickers"]}["MRNA"]["last"])
        self.assertEqual(again["errors"], {"MRNA": "rate limit"})

    def test_market_stale_when_data_is_old(self):
        res = {"GOOG": (True, fp.fetch_series("GOOG", "K", lambda u: payload(100, end="2026-10-26")))}
        doc = fp.build_document(res, None, NOW, {})
        self.assertTrue(doc["market_stale"])

    def test_nothing_fetched_returns_none(self):
        self.assertIsNone(fp.build_document({}, None, NOW, {"GOOG": "x"}))


def git(*a, cwd):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.bare = t / "remote.git"
        seed = t / "seed"
        git("init", "-q", "--bare", "-b", "main", str(self.bare), cwd=t)
        git("clone", "-q", str(self.bare), str(seed), cwd=t)
        (seed / "data").mkdir()
        (seed / "data" / "editions.json").write_text("[]")
        git("add", "-A", cwd=seed)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init", cwd=seed)
        git("push", "-q", "origin", "HEAD:main", cwd=seed)
        self.clone = t / "clone"
        git("clone", "-q", str(self.bare), str(self.clone), cwd=t)

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, api, **kw):
        return fp.main(["--clone-dir", str(self.clone), "--key", "K"], get_json=api, sleep=lambda s: None, now=NOW, **kw)

    def remote_file(self):
        out = subprocess.run(["git", "--git-dir", str(self.bare), "show", "main:data/prices.json"], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def test_publish_then_unchanged(self):
        api = FakeApi()
        self.assertEqual(self.go(api), 0)
        self.assertEqual(len(api.calls), 10)
        doc = self.remote_file()
        self.assertEqual(doc["market_date"], "2026-10-30")
        self.assertEqual(len(doc["tickers"]), 10)
        n = subprocess.run(["git", "--git-dir", str(self.bare), "rev-list", "--count", "main"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(self.go(FakeApi()), 0)       # same data again: no new commit
        n2 = subprocess.run(["git", "--git-dir", str(self.bare), "rev-list", "--count", "main"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(n, n2)

    def test_everything_rate_limited_returns_2_and_writes_nothing(self):
        self.assertEqual(self.go(FakeApi(limit=True)), 2)
        r = subprocess.run(["git", "--git-dir", str(self.bare), "show", "main:data/prices.json"], capture_output=True)
        self.assertNotEqual(r.returncode, 0)

    def test_partial_failure_still_publishes_with_errors(self):
        self.assertEqual(self.go(FakeApi(fail={"BEAM"})), 0)
        doc = self.remote_file()
        self.assertIn("BEAM", doc["errors"])
        self.assertEqual(len(doc["tickers"]), 9)

    def test_dry_run_changes_nothing(self):
        rc = fp.main(["--dry-run", "--clone-dir", str(self.clone), "--key", "K"], get_json=FakeApi(), sleep=lambda s: None, now=NOW)
        self.assertEqual(rc, 0)
        self.assertFalse((self.clone / "data" / "prices.json").exists())

    def test_push_rejected_then_rebased(self):
        # someone else pushes to main after our clone was made
        t = Path(self.tmp.name)
        other = t / "other"
        git("clone", "-q", str(self.bare), str(other), cwd=t)
        (other / "data" / "other.json").write_text("{}")
        git("add", "-A", cwd=other)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "other", cwd=other)
        git("push", "-q", "origin", "HEAD:main", cwd=other)
        orig = fp.ensure_clone
        fp.ensure_clone = lambda c: None          # skip the pull so the push meets a newer remote
        try:
            self.assertEqual(self.go(FakeApi()), 0)
        finally:
            fp.ensure_clone = orig
        self.assertEqual(self.remote_file()["market_date"], "2026-10-30")


if __name__ == "__main__":
    unittest.main(verbosity=2)
