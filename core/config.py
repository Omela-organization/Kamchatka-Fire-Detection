import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SENTRY_SDK = os.getenv("SENTRY_SDK")
