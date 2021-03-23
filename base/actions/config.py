import os

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", None)
SENTRY_DSN = os.environ.get("SENTRY_DSN", None)
HEALTHCONNECT_URL = os.environ.get("HEALTHCONNECT_URL", None)
HEALTHCONNECT_TOKEN = os.environ.get("HEALTHCONNECT_TOKEN", None)
HTTP_RETRIES = int(os.environ.get("HTTP_RETRIES", 3))
LANGUAGE = os.environ.get("LANGUAGE", "eng")
