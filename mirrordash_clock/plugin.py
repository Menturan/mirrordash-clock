import asyncio
import logging

logger = logging.getLogger("mirrordash.modules.clock")

class ClockModule:
    def __init__(self, config):
        self.config = config
        self.name = "mirrordash_clock"
        global_cfg = config.get("globals", {})
        
        # Fallback format: check instance config first, then global config
        self.format = config.get("format") or global_cfg.get("time_format", "24h")
        self.show_seconds = config.get("show_seconds", True)
        self.show_header = config.get("show_header", True)
        
        # Localization and custom date layout
        self.lang = global_cfg.get("language", "en")
        self.date_format = config.get("date_format", "full")
        
        # Timezone configuration
        self.timezone_name = global_cfg.get("timezone", "Europe/Stockholm")
            
        logger.info("Initializing ClockModule with format: %s, show_seconds: %s, lang: %s, date_format: %s, timezone: %s", 
                    self.format, self.show_seconds, self.lang, self.date_format, self.timezone_name)

    async def run_loop(self, broadcast_func):
        logger.info("Starting ClockModule run loop")
        try:
            # Render the static clock container template once
            html = self.render_template(
                "clock.html",
                format=self.format,
                show_seconds=self.show_seconds,
                lang=self.lang,
                timezone=self.timezone_name,
                date_format=self.date_format,
                show_header=self.show_header
            )
            await broadcast_func(self.name, html)
            
            # Keep module task alive by sleeping indefinitely
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Clock module stopped.")
            raise
