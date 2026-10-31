import http.server
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class MobileLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(ROOT), **kw)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_status_fits_phone_width(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width in (320, 360, 390, 430):
                page = browser.new_page(viewport={"width": width, "height": 780}, device_scale_factor=2)
                page.goto(f"http://127.0.0.1:{self.server.server_port}/index.html", wait_until="domcontentloaded")
                page.evaluate("""() => {
                    const s = document.querySelector('#status');
                    if (!s) throw new Error('Missing #status');
                    s.textContent = '토스 수집 123분 전 · 최근 분봉 123/123종목 · 레이더 123분 전 · 데이터 상태 점검 중';
                }""")
                page.wait_for_timeout(300)
                metrics = page.evaluate("""() => {
                    const e = document.querySelector('#status');
                    const r = e.getBoundingClientRect();
                    return {left:r.left, right:r.right, scrollWidth:e.scrollWidth, clientWidth:e.clientWidth, viewport:innerWidth};
                }""")
                self.assertGreaterEqual(metrics["left"], -1, (width, metrics))
                self.assertLessEqual(metrics["right"], width + 1, (width, metrics))
                self.assertLessEqual(metrics["scrollWidth"], metrics["clientWidth"] + 1, (width, metrics))
                page.screenshot(path=f"mobile-status-{width}.png", full_page=False)
                page.close()
            browser.close()

if __name__ == "__main__":
    unittest.main()
