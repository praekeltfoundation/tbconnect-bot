import os

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", None)
SENTRY_DSN = os.environ.get("SENTRY_DSN", None)
HEALTHCONNECT_URL = os.environ.get("HEALTHCONNECT_URL", None)
HEALTHCONNECT_TOKEN = os.environ.get("HEALTHCONNECT_TOKEN", None)
TURN_URL = os.environ.get("TURN_URL", None)
TURN_TOKEN = os.environ.get("TURN_TOKEN", None)
HTTP_RETRIES = int(os.environ.get("HTTP_RETRIES", 3))
LANGUAGE = os.environ.get("LANGUAGE", "eng")
TBCONNECT_RESEARCH_CONSENT = os.environ.get("TBCONNECT_RESEARCH_CONSENT", False)
