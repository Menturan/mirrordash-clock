"""Every look of the clock, rendered as the mirror renders it and run in WebKit (Cog's engine) at a fixed time.

Once: uv run playwright install webkit
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

PKG = Path(__file__).parent.parent / "mirrordash_clock"
STYLES = json.loads((PKG / "config_schema.json").read_text())["properties"]["style"]["enum"]
NOW = datetime(2026, 10, 12, 13, 47, 20, tzinfo=timezone.utc)  # Monday 15:47:20 in Stockholm (CEST)

# What each look shows at NOW, in Swedish
TEXTS = {
    "classic": {".clock-hm": "15:47", ".clock-s": ":20", "div.clock-date": "Måndag 12 oktober 2026"},
    "minimal": {".clock-hm": "15:47"},
    "stacked": {".clock-h": "15", ".clock-m": "47", "div.clock-date": "Måndag 12 oktober 2026"},
    "words": {".clock-w-lead": "Kvart i", ".clock-w-hour": "fyra", "span.clock-hm": "15:47"},
    "dayfirst": {".clock-weekday": "Måndag", ".clock-daymonth": "12 oktober", ".clock-hm": "15:47"},
    "secline": {".clock-hm": "15:47", "div.clock-date": "Måndag 12 oktober 2026"},
    "rings": {".ring-time": "15:47"},
}
# Hour hand 3 h 47 min = 113.5°, minute hand 47 min 20 s = 284°, second hand 20 s = 120°
HANDS = {".hand-h": "rotate(113.5)", ".hand-m": "rotate(284)", ".hand-s": "rotate(120)"}
ANALOG_HANDS = ["analog-minimal", "station", "dots"]

# kiosk/core.js: the module's HTML goes into a shadow root, and each script runs with that root as `root`
SHOW = """html => {
    const host = document.body.appendChild(document.createElement('div'));
    const shadow = host.attachShadow({ mode: 'open' });
    shadow.innerHTML = html;
    window.__mirrordashRoot = shadow;
    for (const old of shadow.querySelectorAll('script')) {
        const script = document.createElement('script');
        script.textContent = `(function (root) {\\n${old.textContent}\\n})(window.__mirrordashRoot);`;
        old.replaceWith(script);
    }
}"""


def render(lang="sv", **config):
    """clock.html with the same context plugin.py and the mirror's loader give it."""
    read = lambda name: json.loads((PKG / "translations" / name).read_text())
    env = Environment(loader=FileSystemLoader(PKG / "templates"), autoescape=select_autoescape(["html", "xml"]))
    context = dict(style="classic", format="24h", show_seconds=True, lang=lang, timezone="Europe/Stockholm",
                   timezone_display="none", date_format="full", show_header=True,
                   translations=read("en.json") | read(f"{lang}.json"))
    return env.get_template("clock.html").render(**(context | config))


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.webkit.launch()
        yield browser
        browser.close()


@pytest.fixture
def show(browser):
    """show(html, now) puts a rendered clock on a fresh page at that time; any script error fails the test."""
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(error))

    def _show(html, now=NOW):
        page.clock.set_fixed_time(now)
        page.evaluate(SHOW, html)
        return page

    yield _show
    page.close()
    assert not errors, errors


def test_every_look_is_tested():
    assert set(STYLES) == set(TEXTS) | set(ANALOG_HANDS)


@pytest.mark.parametrize("style", STYLES)
def test_each_look_shows_the_time(show, style):
    page = show(render(style=style))
    assert page.locator(".clock-container").get_attribute("data-style") == style
    for selector, text in TEXTS.get(style, {}).items():
        assert page.locator(selector).first.text_content() == text, selector
    if style in ANALOG_HANDS:
        for selector, transform in HANDS.items():
            assert page.locator(selector).get_attribute("transform") == transform, selector


def test_an_unknown_look_falls_back_to_classic(show):
    page = show(render(style=None))
    assert page.locator(".clock-container").get_attribute("data-style") == "classic"
    assert page.locator(".clock-s").text_content() == ":20"


def test_words_round_to_the_next_hour(show):
    page = show(render(style="words"), now=datetime(2026, 10, 12, 13, 58, 0, tzinfo=timezone.utc))
    assert page.locator(".clock-w-lead").text_content() == "Klockan är"
    assert page.locator(".clock-w-hour").text_content() == "fyra"


def test_words_in_english(show):
    page = show(render(lang="en", style="words"))
    assert page.locator(".clock-w-lead").text_content() == "Quarter to"
    assert page.locator(".clock-w-hour").text_content() == "four"


def test_seconds_line_fills_over_the_minute(show):
    page = show(render(style="secline"))
    assert page.locator(".clock-fill").evaluate("el => el.style.width") == "33.9%"  # 20 of 59 s


def test_rings_fill_to_the_time(show):
    page = show(render(style="rings"))
    dashes = [float(a.get_attribute("stroke-dasharray").split()[0]) for a in page.locator(".ring").all()]
    # Seconds 120°, minutes 284°, hours 113.5° of rings with radius 92, 80 and 68
    assert dashes == pytest.approx([2 * 3.14159265 * r * deg / 360 for r, deg in ((92, 120), (80, 284), (68, 113.5))])


def test_without_seconds_nothing_shows_them(show):
    for style, selector in (("classic", ".clock-s"), ("station", ".hand-s"), ("dots", ".hand-s"), ("secline", ".clock-fill")):
        assert show(render(style=style, show_seconds=False)).locator(selector).count() == 0, style


def test_twelve_hour_clock(show):
    page = show(render(lang="en", format="12h"))
    assert page.locator(".clock-hm").text_content() == "03:47"
    assert page.locator(".clock-ampm").text_content() == "PM"


def test_own_timezone_shifts_the_time_and_names_it(show):
    page = show(render(lang="en", timezone="America/New_York", timezone_display="city_abbr"))
    assert page.locator(".clock-hm").text_content() == "09:47"
    assert page.locator(".clock-tz").text_content() == "New York · EDT"


def test_an_invalid_timezone_still_shows_a_time(show):
    for style in ("classic", "station"):
        page = show(render(style=style, timezone="Mars/Olympus_Mons"))
        assert page.locator(".clock-container").last.locator(".clock-date").first.text_content()
