"""Playwright end-to-end tests for the Streamlit dashboard."""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_dashboard_loads_seeded_data(page: Page, streamlit_server_url: str) -> None:
    page.goto(streamlit_server_url, wait_until="domcontentloaded")

    expect(page.get_by_role("heading", name="Operations Issue Metrics")).to_be_visible()
    expect(page.get_by_text("Issue Summary", exact=True)).to_be_visible()
    expect(page.get_by_text("Issue summary rows: 3")).to_be_visible()
    expect(page.get_by_text("Affected lots rows: 3")).to_be_visible()
    expect(
        page.get_by_role("button", name="Download issue summary CSV")
    ).to_be_visible()
    expect(
        page.get_by_role("button", name="Download affected lots CSV")
    ).to_be_visible()
