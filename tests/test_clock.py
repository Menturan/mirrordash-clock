import pytest
from unittest.mock import MagicMock
from mirrordash_clock.plugin import ClockModule

@pytest.mark.asyncio
async def test_clock_module_render():
    config = {
        "globals": {
            "time_format": "24h",
            "language": "sv",
            "timezone": "Europe/Stockholm"
        },
        "show_seconds": False,
        "show_header": True,
        "date_format": "full"
    }

    # Mock template rendering
    clock = ClockModule(config)
    clock.render_template = MagicMock(return_value="<div>Clock Rendered</div>")

    assert await clock.render() == "<div>Clock Rendered</div>"
    clock.render_template.assert_called_once_with(
        "clock.html",
        style="classic",
        format="24h",
        show_seconds=False,
        lang="sv",
        timezone="Europe/Stockholm",
        timezone_display="none",
        date_format="full",
        show_header=True,
        size=100
    )


def test_clock_own_timezone_wins_over_system():
    config = {"globals": {"timezone": "Europe/Stockholm"}, "timezone": "America/New_York", "timezone_display": "city_abbr"}
    clock = ClockModule(config)
    assert clock.timezone_name == "America/New_York"
    assert clock.timezone_display == "city_abbr"
    # An empty field (the schema default) falls back to the system's timezone
    assert ClockModule({"globals": {"timezone": "Europe/Stockholm"}, "timezone": ""}).timezone_name == "Europe/Stockholm"


@pytest.mark.parametrize("given,expected", [(None, 100), (100, 100), (150, 150), (10, 50), (500, 200), ("80", 80),
                                            ("abc", 100), (None, 100), ([], 100), (float("inf"), 100), (120.7, 120)])
def test_clock_size_is_clamped_and_defaults_to_100(given, expected):
    config = {} if given is None else {"size": given}
    clock = ClockModule(config)
    assert clock.size == expected
    clock.render_template = MagicMock(return_value="")
    import asyncio
    asyncio.run(clock.render())
    assert clock.render_template.call_args.kwargs["size"] == expected
