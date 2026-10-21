"""ECB press feed. Speeches and interviews in the same file are not stored."""

SOURCE_ID = "ecb_monetary_press"
DATASET_ID = "ecb.press.monetary"
ADAPTER_ID = "ecb_monetary_press"
ADAPTER_VERSION = "1"
FEED_URL = "https://www.ecb.europa.eu/rss/press.html"
ALLOWED_HOST = "www.ecb.europa.eu"
ALLOWED_PATH_PREFIXES = (
    "/press/pr/",
    "/press/accounts/",
    "/press/govcdec/",
    "/press/pressconf/",
)
