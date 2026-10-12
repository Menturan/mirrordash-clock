import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from mirrordash_clock.plugin import ClockModule

@pytest.mark.asyncio
async def test_clock_module_run_loop():
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
    
    # Patch asyncio.sleep inside the clock module to immediately raise CancelledError
    # so we don't block forever on the loop
    with patch("mirrordash_clock.plugin.asyncio.sleep", side_effect=asyncio.CancelledError):
        
        broadcast_mock = AsyncMock()
        with pytest.raises(asyncio.CancelledError):
            await clock.run_loop(broadcast_mock)
            
        broadcast_mock.assert_called_once_with("mirrordash_clock", "<div>Clock Rendered</div>")
        clock.render_template.assert_called_once_with(
            "clock.html",
            style="classic",
            format="24h",
            show_seconds=False,
            lang="sv",
            timezone="Europe/Stockholm",
            timezone_display="none",
            date_format="full",
            show_header=True
        )


def test_clock_own_timezone_wins_over_system():
    config = {"globals": {"timezone": "Europe/Stockholm"}, "timezone": "America/New_York", "timezone_display": "city_abbr"}
    clock = ClockModule(config)
    assert clock.timezone_name == "America/New_York"
    assert clock.timezone_display == "city_abbr"
    # An empty field (the schema default) falls back to the system's timezone
    assert ClockModule({"globals": {"timezone": "Europe/Stockholm"}, "timezone": ""}).timezone_name == "Europe/Stockholm"
