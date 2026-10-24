"""Shared identifiers and defaults."""

DOMAIN = "bedtime_sticker_club"
TITLE = "Bedtime Sticker Club"
DASHBOARD_URL = "bedtime-club"
CHILDREN = ("kid_1", "kid_2", "kid_3")
TASKS = ("plate", "teeth", "outfit")
STICKERS = ("⭐", "🌈", "🚀", "🦄", "🦖", "🐱", "🦋", "⚽")
DEFAULT_DINNER = "18:00:00"
DEFAULT_BEDTIME = "19:00:00"
DEFAULT_SWITCH_TIME = "12:00:00"
PROFILE_COLORS = {
    "kid_1": ("#7541bf", "#f0e6ff"),
    "kid_2": ("#087e82", "#d9f4ed"),
    "kid_3": ("#b94d1c", "#ffead9"),
}
DEFAULT_TASKS = [
    {"id": "plate", "label": "Clear my plate", "icon": "🍽️"},
    {"id": "teeth", "label": "Brush my teeth", "icon": "🪥"},
    {"id": "outfit", "label": "Pick tomorrow’s outfit", "icon": "👕"},
]
STORAGE_KEY = DOMAIN
