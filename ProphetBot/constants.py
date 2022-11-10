import json
import os
from typing import Dict

# Bot Configuration Stuff
BOT_OWNERS = [286360249659817984, 208388527401074688, 225752877316964352]
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DEFAULT_PREFIX = os.environ.get("COMMAND_PREFIX", ">")
DEBUG_GUILDS = json.loads(os.environ["GUILD"]) if "GUILD" in os.environ else None
DASHBOARD_REFRESH_INTERVAL = float(os.environ.get("DASHBOARD_REFRESH_INTERVAL", 15))

# Database Stuff
DB_URL = os.environ.get("DATABASE_URL", "")

# Misc
THUMBNAIL = "https://cdn.discordapp.com/attachments/794989941690990602/972998353103233124/IMG_2177.jpg"

# Keep around for GSheets stuff for now
TIERS = [0, 5, 9, 13, 17]
SHOP_TIERS = [0, 5, 8, 12, 18]
