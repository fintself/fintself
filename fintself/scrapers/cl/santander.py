import re
from typing import List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

from fintself.core.exceptions import DataExtractionError, LoginError
from fintself.core.models import MovementModel
from fintself.scrapers.base import BaseScraper
from fintself.utils.logging import logger
from fintself.utils.parsers import parse_chilean_amount, parse_chilean_date


class SantanderScraper(BaseScraper):
    """Scraper to extract movements from Banco Santander Chile."""

    LOGIN_URL = "https://banco.santander.cl/personas"
    DASHBOARD_URL = "https://mibanco.santander.cl/UI.Web.HB/Private_new/frame/#/private/home/main/resumen"
    UNBILLED_URL = "https://mibanco.santander.cl/UI.Web.HB/Private_new/frame/#/private/Saldos_TC/main/bill"
    BILLED_URL = "https://mibanco.santander.cl/UI.Web.HB/Private_new/frame/#/private/Saldos_TC/main/billed"

    def _get_bank_id(self) -> str:
        return "cl_santander"

    def _login(self) -> None:
        """Implements the login logic for Santander Chile."""
        assert self.user is not None, "User must be provided"
        assert self.password is not None, "Password must be provided"

        page = self._ensure_page()
        logger.info("Navigating to Santander login page.")
        self._navigate(self.LOGIN_URL, timeout_override=90000)
        self._save_debug_info("01_login_page")

        logger.info("Clicking on 'Ingresar al sitio privado' button.")
        self._click('role=button[name="Ingresar al sitio privado"]')

        logger.info("Waiting for login iframe.")
        try:
            login_frame = page.frame_locator("#login-frame")
            # Wait for an element inside the frame to ensure it's loaded
            login_frame.locator('role=textbox[name="RUT"]').wait_for(
                state="visible", timeout=20000
            )
        except PlaywrightTimeoutError:
            self._save_debug_info("login_iframe_timeout")
            raise LoginError("Timeout waiting for Santander login iframe.")

        logger.info("Entering credentials.")
        self._type(
            login_frame.locator('role=textbox[name="RUT"]'), self.user, delay=120
        )
        self._type(
            login_frame.locator('role=textbox[name="Clave"]'), self.password, delay=120
        )
        self._save_debug_info("02_credentials_entered")

        logger.info("Submitting login form.")
        self._click(login_frame.locator('role=button[name="Ingresar"]'))

        logger.info("Waiting for post-login confirmation.")
        try:
            expect(page.locator("h3:has-text('Hola')")).to_be_visible(timeout=40000)
            self._save_debug_info("03_login_success")
            logger.info("Login to Santander successful.")
        except PlaywrightTimeoutError:
            self._save_debug_info("post_login_error")
            raise LoginError(
                "Timeout or error after login to Santander. Credentials might be incorrect."
            )

    def _extract_and_store_account_ids(self) -> None:
        """Scrapes all account IDs from the dashboard, storing them in self.account_ids."""
        page = self._ensure_page()
        logger.info("Extracting and storing all account IDs from the dashboard.")
        # We assume we are on the dashboard after a successful login.
        self._save_debug_info("dashboard_for_ids")

        # --- Extract Checking Account IDs ---
        try:
            account_divs = page.locator("#cuentas div.box-product").all()
            for div in account_divs:
                name_p = div.locator("div.datos p").first.inner_text(timeout=2000)
                number_raw = div.locator("div.datos p").nth(1).inner_text(timeout=2000)
                number_clean = re.sub(r"[^\d]", "", number_raw)

                if "dólar" in name_p.lower():
                    self.account_ids["corriente"]["USD"] = number_clean
                    logger.info(f"Stored checking account USD: {number_clean}")
                else:
                    self.account_ids["corriente"]["CLP"] = number_clean
                    logger.info(f"Stored checking account CLP: {number_clean}")
        except Exception as e:
            logger.warning(f"Could not extract checking account IDs: {e}")
            self._save_debug_info("checking_id_extraction_failed")

        # --- Extract Credit Card IDs ---
        try:
            card_divs = page.locator("#tarjetas-creditos div.box-product").all()
            if card_divs:
                first_card = card_divs[0]
                card_number_p = first_card.locator("p:has-text('*')")
                card_text = card_number_p.inner_text(timeout=2000)
                match = re.search(r"\*\s*(\d{4})", card_text)
                if match:
                    card_id = f"**** {match.group(1)}"
                    # Assume same ID for both currencies, as the site seems to have one context per card.
                    self.account_ids["credito"]["CLP"] = card_id
                    self.account_ids["credito"]["USD"] = card_id
                    logger.info(f"Stored credit card ID for CLP/USD: {card_id}")
        except Exception as e:
            logger.warning(f"Could not extract credit card IDs: {e}")
            self._save_debug_info("credit_id_extraction_failed")

    def _scrape_movements(self) -> List[MovementModel]:
        """Orchestrates the extraction of all types of card movements."""
        self.account_ids: dict = {"corriente": {}, "credito": {}}
        self._extract_and_store_account_ids()

        all_movements: List[MovementModel] = []

        # Credit Card: Unbilled
        logger.info("--- Starting extraction of Unbilled CC ---")
        self._navigate(self.UNBILLED_URL, timeout_override=60000)
        self._save_debug_info("04_unbilled_page")
        all_movements.extend(
            self._extract_credit_card_movements("no_facturados", "CLP")
        )
        self._switch_currency_tab("USD")
        all_movements.extend(
            self._extract_credit_card_movements("no_facturados", "USD")
        )

        # Credit Card: Billed
        logger.info("--- Starting extraction of Billed CC ---")
        self._navigate(self.BILLED_URL, timeout_override=60000)
        self._save_debug_info("05_billed_page")
        self._switch_currency_tab("CLP")
        all_movements.extend(self._extract_credit_card_movements("facturados", "CLP"))
        self._switch_currency_tab("USD")
        all_movements.extend(self._extract_credit_card_movements("facturados", "USD"))

        # Debit Card (Checking Account)
        all_movements.extend(self._scrape_debit_card_movements())

        logger.info(
            f"Scraping completed. Total movements extracted: {len(all_movements)}"
        )
        return all_movements

    def _switch_currency_tab(self, currency: str) -> None:
        """Switches between the Pesos and Dólares tabs."""
        page = self._ensure_page()
        target_tab = "Dólares" if currency == "USD" else "Pesos"
        logger.info(f"Switching to currency tab: {target_tab}")
        try:
            self._click(f'button:has-text("{target_tab}")')
            expect(
                page.locator(f'mat-button-toggle:has-text("{target_tab}")')
            ).to_have_class(
                re.compile(r"mat-button-toggle-checked|actived"), timeout=15000
            )
            page.wait_for_timeout(2000)  # Wait for content to load
        except (PlaywrightTimeoutError, DataExtractionError):
            self._save_debug_info(f"currency_switch_timeout_{currency}")
            raise DataExtractionError(f"Timeout switching to {target_tab} tab.")

    def _get_account_id(self, account_type: str, currency: str) -> Optional[str]:
        """Retrieves a pre-scraped account ID from the stored dictionary."""
        try:
            account_id = self.account_ids.get(account_type, {}).get(currency)
            if account_id:
                logger.info(
                    f"Retrieved stored account ID for {account_type}/{currency}: {account_id}"
                )
                return account_id
            else:
                logger.warning(
                    f"No stored account ID found for {account_type}/{currency}."
                )
                return None
        except Exception as e:
            logger.error(
                f"Error retrieving stored account ID for {account_type}/{currency}: {e}"
            )
            return None

    def _scrape_debit_card_movements(self) -> List[MovementModel]:
        """Navigates to and scrapes debit card (checking account) movements."""
        page = self._ensure_page()
        all_debit_movements: List[MovementModel] = []

        logger.info(
            "\n--- Starting extraction of Debit Card (Checking Account) movements ---"
        )

        # CLP Checking Account
        try:
            logger.info("Navigating to dashboard for CLP Checking Account movements...")
            self._navigate(self.DASHBOARD_URL, timeout_override=60000)
            expect(page.locator("h3:has-text('Hola')")).to_be_visible(timeout=40000)
            self._save_debug_info("06_dashboard_for_debit_clp")

            logger.info("Navigating to CLP Checking Account movements...")
            # This locator targets the main checking account summary card.
            # The name contains a special character from an icon font.
            checking_account_card_locator = (
                page.get_by_role("region", name="Cuentas ")
                .get_by_role("emphasis")
                .first
            )
            self._click(checking_account_card_locator)
            self._wait_for_selector("text=Mis movimientos", timeout_override=20000)
            self._save_debug_info("07_debit_clp_movements_page")

            all_debit_movements.extend(
                self._extract_debit_card_movements(currency="CLP")
            )
        except Exception as e:
            logger.error(
                f"Error scraping CLP Checking Account movements: {e}", exc_info=True
            )
            self._save_debug_info("debit_clp_scraping_failed")

        # USD Checking Account
        try:
            logger.info("Navigating to dashboard for USD Checking Account movements...")
            self._navigate(self.DASHBOARD_URL, timeout_override=60000)
            expect(page.locator("h3:has-text('Hola')")).to_be_visible(timeout=40000)
            self._save_debug_info("08_dashboard_for_debit_usd")

            logger.info("Navigating to USD Checking Account movements...")
            # This locator targets the USD checking account by finding the second "Disponible" text
            # within the "Cuentas" region.
            usd_account_card_locator = (
                page.get_by_label("Cuentas").get_by_text("Disponible").nth(1)
            )

            if usd_account_card_locator.count() > 0:
                self._click(usd_account_card_locator)
                self._wait_for_selector("text=Mis movimientos", timeout_override=20000)
                self._save_debug_info("09_debit_usd_movements_page")
                all_debit_movements.extend(
                    self._extract_debit_card_movements(currency="USD")
                )
            else:
                logger.warning("USD Checking Account not found. Skipping.")
        except Exception as e:
            logger.error(
                f"Error scraping USD Checking Account movements: {e}", exc_info=True
            )
            self._save_debug_info("debit_usd_scraping_failed")

        return all_debit_movements

    def _extract_debit_card_movements(self, currency: str) -> List[MovementModel]:
        """Extracts debit card (checking account) movements from the current page."""
        page = self._ensure_page()
        logger.info(f"Extracting debit card movements in {currency}...")
        account_id = self._get_account_id(account_type="corriente", currency=currency)
        container_selector = "div.card.table-container.show"

        try:
            self._wait_for_selector(container_selector, timeout_override=30000)
        except DataExtractionError:
            logger.warning(
                f"No table container found for debit card movements in {currency}."
            )
            return []

        rows = page.locator(
            f"{container_selector} table.mat-table tbody tr.mat-row"
        ).all()
        if not rows:
            logger.info(f"No debit card movements found in {currency}.")
            return []

        movements = []
        last_date_str = ""

        for row in rows:
            raw_movement = {}
            if account_id:
                raw_movement["full_account_id"] = account_id

            try:
                date_text = (
                    row.locator("td.mat-column-date").inner_text(timeout=5000).strip()
                )
                if date_text:
                    last_date_str = date_text

                raw_movement["date"] = last_date_str
                raw_movement["description"] = (
                    row.locator("td.mat-column-detail").inner_text(timeout=5000).strip()
                )

                charge_str = (
                    row.locator("td.mat-column-amountCharge")
                    .inner_text(timeout=5000)
                    .strip()
                )
                payment_str = (
                    row.locator("td.mat-column-paymentAmount")
                    .inner_text(timeout=5000)
                    .strip()
                )

                # For debit, charges are negative, payments are positive.
                if charge_str and charge_str not in ["0", ""]:
                    raw_movement["amount"] = f"-{charge_str}"
                elif payment_str and payment_str not in ["0", ""]:
                    raw_movement["amount"] = payment_str
                else:
                    raw_movement["amount"] = "0"

                parsed_date = parse_chilean_date(raw_movement.get("date"))
                if not parsed_date:
                    continue

                amount = parse_chilean_amount(raw_movement.get("amount"))
                if amount.is_zero():
                    continue

                movements.append(
                    MovementModel(
                        date=parsed_date,
                        description=raw_movement.get("description", ""),
                        amount=amount,
                        currency=currency,
                        transaction_type="Cargo" if amount < 0 else "Abono",
                        account_id=account_id,
                        account_type="corriente",
                        raw_data=raw_movement,
                    )
                )
            except Exception as e:
                logger.warning(f"Error parsing a debit card movement row: {e}")
                continue

        logger.info(f"Extracted {len(movements)} debit card movements in {currency}.")
        return movements

    def _extract_credit_card_movements(
        self, status: str, currency: str
    ) -> List[MovementModel]:
        """Extracts credit card movements from the current page."""
        page = self._ensure_page()
        logger.info(f"Extracting {status} movements in {currency}...")
        account_id = self._get_account_id(account_type="credito", currency=currency)
        container_selector = (
            "div.card.table-container.show"
            if status == "no_facturados"
            else "div.container-tabla"
        )

        try:
            self._wait_for_selector(container_selector, timeout_override=30000)
        except DataExtractionError:
            logger.warning(
                f"No table container found for {status} movements in {currency}."
            )
            return []

        rows = page.locator(
            f"{container_selector} table.mat-table tbody tr.mat-row"
        ).all()
        if not rows:
            logger.info(f"No {status} movements found in {currency}.")
            return []

        movements = []
        last_date_str = ""

        for row in rows:
            raw_movement = {}
            if account_id:
                raw_movement["full_account_id"] = account_id

            try:
                date_text = (
                    row.locator("td.mat-column-date").inner_text(timeout=5000).strip()
                )
                if date_text:
                    last_date_str = date_text

                raw_movement["date"] = last_date_str
                raw_movement["description"] = (
                    row.locator("td.mat-column-detail").inner_text(timeout=5000).strip()
                )

                if status == "no_facturados":
                    charge = (
                        row.locator("td.mat-column-amountCharge")
                        .inner_text(timeout=5000)
                        .strip()
                    )
                    payment = (
                        row.locator("td.mat-column-paymentAmount")
                        .inner_text(timeout=5000)
                        .strip()
                    )
                    raw_movement["amount"] = (
                        f"-{charge}" if charge and charge not in ["0", ""] else payment
                    )
                else:
                    # For billed movements, Santander shows:
                    # - Expenses (gastos) as positive values - we need them negative
                    # - Refunds (reembolsos) as negative values - we need them positive
                    # So we invert the sign to match the expected behavior
                    amount_text = (
                        row.locator("td.mat-column-amount")
                        .inner_text(timeout=5000)
                        .strip()
                    )
                    # Parse the amount to check if it's positive or negative
                    if amount_text.startswith("-"):
                        # Negative amount (refund) - make it positive
                        raw_movement["amount"] = amount_text[
                            1:
                        ]  # Remove the minus sign
                    else:
                        # Positive amount (expense) - make it negative
                        raw_movement["amount"] = f"-{amount_text}"

                parsed_date = parse_chilean_date(raw_movement.get("date"))
                if not parsed_date:
                    continue

                amount = parse_chilean_amount(raw_movement.get("amount"))

                movements.append(
                    MovementModel(
                        date=parsed_date,
                        description=raw_movement.get("description", ""),
                        amount=amount,
                        currency=currency,
                        transaction_type="Cargo" if amount < 0 else "Abono",
                        account_id=account_id,
                        account_type="credito",
                        raw_data=raw_movement,
                    )
                )
            except Exception as e:
                logger.warning(f"Error parsing a movement row: {e}")
                continue

        logger.info(f"Extracted {len(movements)} {status} movements in {currency}.")
        return movements
