"""Federal Reserve monetary-policy press feed."""

SOURCE_ID = "federal_reserve_monetary_press"
DATASET_ID = "fed.press.monetary"
ADAPTER_ID = "federal_reserve_monetary_press"
ADAPTER_VERSION = "1"
FEED_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
ALLOWED_HOSTS = frozenset({"www.federalreserve.gov"})
ALLOWED_PATH_PREFIX = "/newsevents/pressreleases/"
