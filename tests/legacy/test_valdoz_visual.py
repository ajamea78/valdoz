"""End-to-end tests for `valdoz visual-diff` (SCAR-012).

Needs Chromium (`valdoz install-browser`). The whole module skips if the browser
cannot launch, so the main suite still works without it.

Keep this file next to test_valdoz.py (it reuses that file's fixtures).
"""
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from test_valdoz import runner, sandbox, vz  # noqa: F401  (sandbox is an autouse fixture)


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _chromium_available(),
                                reason="Chromium not installed (run: valdoz install-browser)")

BASE_HTML = "<body style='margin:0;background:#fff'><div style='width:50px;height:50px;background:#00f'></div></body>"
# Adds a 300x300 red block: about 6.9% of a 1440x900 viewport, above the 2% default.
CHANGED_HTML = BASE_HTML.replace("</body>",
                                 "<div style='width:300px;height:300px;background:#f00'></div></body>")


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep test output clean
        pass


@pytest.fixture
def site(tmp_path):
    root = tmp_path / "site"
    root.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    class Site:
        base = f"http://127.0.0.1:{server.server_port}"

        @staticmethod
        def page(name: str, html: str) -> str:
            (root / name).write_text(html, encoding="utf-8")
            return f"{Site.base}/{name}"

    yield Site
    server.shutdown()


@pytest.fixture(autouse=True)
def no_ci_env(monkeypatch):
    monkeypatch.delenv("CI", raising=False)  # GitHub Actions sets CI=true


def vd(url, *extra):
    return runner.invoke(vz.app, ["visual-diff", url, *extra])


def test_first_run_saves_baseline(site):
    url = site.page("a.html", BASE_HTML)
    r = vd(url, "--name", "home")
    assert r.exit_code == 0, r.output
    assert Path(".valdoz/baselines/home.png").exists()


def test_unchanged_page_passes(site):
    url = site.page("a.html", BASE_HTML)
    vd(url, "--name", "home")
    r = vd(url, "--name", "home")
    assert r.exit_code == 0, r.output
    assert "PASSED" in r.output


def test_changed_page_fails_and_writes_artifacts(site):
    url = site.page("a.html", BASE_HTML)
    vd(url, "--name", "home")
    site.page("a.html", CHANGED_HTML)
    r = vd(url, "--name", "home")
    assert r.exit_code == 1, r.output
    assert "FAILED" in r.output
    assert Path(".valdoz/baselines/home.diff.png").exists()
    assert Path(".valdoz/baselines/home.current.png").exists()


def test_ratio_is_a_fraction_of_pixels_never_above_one(site):
    url = site.page("a.html", BASE_HTML)
    vd(url, "--name", "home")
    site.page("a.html", CHANGED_HTML)
    out = vd(url, "--name", "home").output
    ratio = float(out.split(":")[1].split("of pixels")[0])
    assert 0.05 < ratio < 0.09  # about 6.9%, not a per-channel count


def test_looser_threshold_lets_the_change_pass(site):
    url = site.page("a.html", BASE_HTML)
    vd(url, "--name", "home")
    site.page("a.html", CHANGED_HTML)
    assert vd(url, "--name", "home", "--threshold", "0.5").exit_code == 0


def test_baselines_are_keyed_per_name(site):
    a = site.page("a.html", BASE_HTML)
    b = site.page("b.html", CHANGED_HTML)
    vd(a, "--name", "page-a")
    vd(b, "--name", "page-b")
    assert vd(a, "--name", "page-a").exit_code == 0
    assert vd(b, "--name", "page-b").exit_code == 0  # B is not compared to A's baseline


def test_update_baseline_accepts_the_new_look(site):
    url = site.page("a.html", BASE_HTML)
    vd(url, "--name", "home")
    site.page("a.html", CHANGED_HTML)
    assert vd(url, "--name", "home").exit_code == 1
    assert vd(url, "--name", "home", "--update-baseline").exit_code == 0
    assert vd(url, "--name", "home").exit_code == 0


def test_missing_baseline_fails_in_ci(site, monkeypatch):
    monkeypatch.setenv("CI", "1")
    r = vd(site.page("a.html", BASE_HTML), "--name", "home")
    assert r.exit_code == 1
    assert "commit" in r.output.lower()
    assert not Path(".valdoz/baselines/home.png").exists()  # CI must not self-seed


def test_unreachable_url_is_a_capture_error_not_a_pass():
    r = vd("http://127.0.0.1:9/nothing", "--name", "dead")
    assert r.exit_code == 2
