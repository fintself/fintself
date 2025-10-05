import os
import sys

from dotenv import load_dotenv

from fintself import get_scraper
from fintself.utils.logging import logger
from fintself.utils.output import save_to_xlsx

# Load environment variables from a .env file.
load_dotenv()

# --- Debug Configuration ---
# Modify this variable to choose which bank you want to debug.
# Available options: "cl_santander", "cl_banco_chile", "cl_estado", "cl_cencosud"
BANK_TO_DEBUG = "cl_santander"
# BANK_TO_DEBUG = "cl_estado"
# BANK_TO_DEBUG = "cl_cencosud"
# BANK_TO_DEBUG = "cl_banco_chile"


def main():
    """
    Main function to run a specific scraper in debug mode.
    This mode shows the browser and saves screenshots/HTML in `debug_output/`.
    """
    logger.info(f"--- Starting debug session for: {BANK_TO_DEBUG} ---")

    # Build environment variable names
    user_env_var = f"{BANK_TO_DEBUG.upper()}_USER"
    password_env_var = f"{BANK_TO_DEBUG.upper()}_PASSWORD"

    # Get credentials
    user = os.getenv(user_env_var)
    password = os.getenv(password_env_var)

    if not user or not password:
        logger.error(
            f"Credentials for {BANK_TO_DEBUG} not found. "
            f"Make sure to define {user_env_var} and {password_env_var} in your .env file."
        )
        sys.exit(1)

    try:
        # Get the scraper instance in debug mode.
        # We pass `debug_mode=True` explicitly to force this mode,
        # regardless of what is configured in the .env file.
        # This automatically makes headless False.
        scraper = get_scraper(BANK_TO_DEBUG, debug_mode=True)

        # Execute the scraper
        movements = scraper.scrape(user=user, password=password)

        if movements:
            output_filename = f"outputs/{BANK_TO_DEBUG}_movements.xlsx"
            save_to_xlsx(movements, output_filename)
            logger.success(
                f"Debug finished. Found and saved {len(movements)} movements for {BANK_TO_DEBUG} in '{output_filename}'."
            )
        else:
            logger.info(f"Debug finished. No movements found for {BANK_TO_DEBUG}.")

        logger.info(
            "Check the 'debug_output' folder to see screenshots and HTML files."
        )

    except Exception as e:
        logger.error(
            f"An error occurred during debugging of {BANK_TO_DEBUG}: {e}",
            exc_info=True,
        )
        logger.info(
            "Check the 'debug_output' folder to see error screenshots and HTML files."
        )


if __name__ == "__main__":
    main()
