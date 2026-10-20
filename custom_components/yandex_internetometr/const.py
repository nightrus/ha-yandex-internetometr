"""Constants for the Yandex Internetometr integration."""

from typing import Final

DOMAIN: Final = "yandex_internetometr"
VERSION: Final = "1.0.0"
DEFAULT_NAME: Final = "Яндекс Интернетометр"

KEY_PING: Final = "ping"
KEY_DOWNLOAD: Final = "download"
KEY_UPLOAD: Final = "upload"

CONF_UPDATE_INTERVAL: Final = "update_interval"
DEFAULT_UPDATE_INTERVAL: Final = 30  # minutes, 0 = only on demand
MIN_UPDATE_INTERVAL: Final = 0
MAX_UPDATE_INTERVAL: Final = 240
STEP_UPDATE_INTERVAL: Final = 5

# One run: ~2 s ping + 8 s download + 8 s upload.
TEST_TIMEOUT: Final = 90

CARD_URL: Final = "/yandex_internetometr/yandex-internetometr-card.js"
