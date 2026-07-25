from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    PROJECT_NAME = os.getenv(
        "PROJECT_NAME",
        "Claude eBay Listing Assistant"
    )

    EBAY_ENV = os.getenv(
        "EBAY_ENV",
        "sandbox"
    )

    EBAY_CLIENT_ID = os.getenv(
        "EBAY_CLIENT_ID"
    )

    EBAY_CLIENT_SECRET = os.getenv(
        "EBAY_CLIENT_SECRET"
    )

    ANTHROPIC_API_KEY = os.getenv(
        "ANTHROPIC_API_KEY"
    )


settings = Settings()
