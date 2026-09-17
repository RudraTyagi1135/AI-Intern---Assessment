"""
End-to-end browser test for the Support Ticket AI System (Streamlit UI).

Prerequisites:
- FastAPI running on http://localhost:8000
- Streamlit running on http://localhost:8501
- Playwright installed with Chromium: `pip install playwright && playwright install chromium`

Run:
    pytest tests/e2e/test_user_flow.py -v -s

The test uses short explicit waits and fails fast with helpful messages.
"""

import re
import pytest
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "http://localhost:8501"
API_URL = "http://localhost:8000"

# -------------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------------
def wait_for_selector(page, selector, timeout=10000):
    """Wait for a selector to be visible, raise with context on failure."""
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout)
    except PlaywrightTimeoutError:
        raise AssertionError(f"Selector '{selector}' not visible within {timeout} ms")


def fill_and_submit(page, input_label, text, submit_button_text="Ask"):
    """Find a text input by its label (or placeholder), fill, and click submit."""
    # Streamlit renders a text_input with a label; we locate by label text.
    input_selector = f"//label[contains(., '{input_label}')]/following-sibling::div//input | //label[contains(., '{input_label}')]/following-sibling::div//textarea"
    page.wait_for_selector(input_selector, state="attached", timeout=10000)
    page.fill(input_selector, text)
    # Submit button
    btn = page.get_by_role("button", name=re.compile(submit_button_text, re.I))
    btn.wait_for(state="visible", timeout=5000)
    btn.click()


def get_answer_text(page):
    """Return the visible answer text after a query."""
    # Answer appears in a success box (stSuccess) or generic div after submit.
    # We'll wait for any element containing "There are" or similar.
    page.wait_for_selector("text=There are", timeout=15000)
    # Grab the whole container text
    return page.locator("text=There are").first.inner_text()


# -------------------------------------------------------------------------
# Test class
# -------------------------------------------------------------------------
class TestUserFlow:
    @classmethod
    def setup_class(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)
        cls.page = cls.browser.new_page()
        cls.page.goto(BASE_URL, wait_until="networkidle", timeout=30000)

    @classmethod
    def teardown_class(cls):
        cls.browser.close()
        cls.pw.stop()

    # ---- Flow 1: Application load ----
    def test_app_loads(self):
        """Page loads, title/header visible, tabs present."""
        wait_for_selector(self.page, "h1:has-text('Support Ticket AI System')")
        # Streamlit tabs have role=tab
        tabs = self.page.get_by_role("tab")
        assert tabs.count() >= 4, "Expected at least 4 tabs (Query, Anomalies, Statistics, Examples)"
        tab_names = [tabs.nth(i).inner_text() for i in range(tabs.count())]
        expected = {"Query", "Anomalies", "Statistics", "Examples"}
        assert expected.issubset(set(tab_names)), f"Missing tabs: {expected - set(tab_names)}"

    # ---- Flow 2: Natural language queries ----
    @pytest.mark.parametrize("question, expected_fragment", [
        ("How many tickets are currently open?", "111"),
        ("Which agent resolved the most tickets?", "AGT-09"),
        ("What is the average resolution time for Technical tickets?", "average"),
        ("How many Critical tickets are unresolved?", "31"),
        ("List unresolved Critical tickets.", "Critical"),
        ("What is the average customer rating?", "3.7"),
    ])
    def test_query_flow(self, question, expected_fragment):
        # Ensure we are on Query tab
        self.page.get_by_role("tab", name="Query").click()
        wait_for_selector(self.page, "text=Ask a question about the tickets")
        fill_and_submit(self.page, "Ask a question about the tickets", question)
        # Wait for answer to appear (generic)
        self.page.wait_for_selector("text=There are", timeout=15000)
        answer = self.page.locator("text=There are").first.inner_text()
        assert expected_fragment in answer, f"Expected '{expected_fragment}' in answer for '{question}'. Got: {answer}"

    # ---- Flow 3: Anomalies tab ----
    def test_anomalies_tab(self):
        self.page.get_by_role("tab", name="Anomalies").click()
        wait_for_selector(self.page, "text=Anomaly Detection")
        # Click refresh button
        self.page.get_by_role("button", name=re.compile("Refresh", re.I)).click()
        # Wait for table rows
        wait_for_selector(self.page, "table")
        rows = self.page.locator("table tbody tr")
        assert rows.count() > 0, "Anomalies table should have at least one row"
        # Verify columns present
        header = self.page.locator("table thead th").all_inner_texts()
        assert "ticket_id" in header
        assert "anomaly_type" in header
        assert "severity" in header

    # ---- Flow 4: Statistics tab ----
    def test_statistics_tab(self):
        self.page.get_by_role("tab", name="Statistics").click()
        wait_for_selector(self.page, "text=Dataset Statistics")
        # Check a few metrics displayed
        assert self.page.locator("text=Total Tickets").is_visible()
        assert self.page.locator("text=500").is_visible()

    # ---- Flow 5: Examples tab ----
    def test_examples_tab(self):
        self.page.get_by_role("tab", name="Examples").click()
        wait_for_selector(self.page, "text=Example Queries")
        # At least one example button present
        buttons = self.page.get_by_role("button", name=re.compile("^📝"))
        assert buttons.count() > 0

    # ---- Flow 6: Error handling ----
    def test_empty_query_error(self):
        self.page.get_by_role("tab", name="Query").click()
        wait_for_selector(self.page, "text=Ask a question about the tickets")
        # Submit without filling (button may be disabled). We'll try to click anyway.
        btn = self.page.get_by_role("button", name=re.compile("Ask", re.I))
        if btn.is_enabled():
            btn.click()
            # Expect no crash; UI should show validation or nothing
            self.page.wait_for_timeout(1000)  # short wait
        # No exception means pass


# -------------------------------------------------------------------------
# Optional: API smoke tests (run without browser)
# -------------------------------------------------------------------------
def test_api_health():
    import requests
    r = requests.get(f"{API_URL}/health/", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("healthy", "degraded")


def test_api_anomalies():
    import requests
    r = requests.get(f"{API_URL}/api/anomalies", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0


def test_api_query_llm_unavailable():
    import requests
    r = requests.post(f"{API_URL}/api/query",
                      json={"question": "How many tickets are open?"}, timeout=10)
    # With no Ollama we expect 503
    assert r.status_code == 503
    assert "LLM provider not available" in r.json()["detail"]