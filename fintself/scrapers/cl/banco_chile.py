import re
from typing import List

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

from fintself.core.exceptions import DataExtractionError, LoginError
from fintself.core.models import MovementModel
from fintself.scrapers.base import BaseScraper
from fintself.utils.logging import logger
from fintself.utils.parsers import parse_chilean_amount, parse_chilean_date


class BancoChileScraper(BaseScraper):
    """
    Scraper for Banco de Chile.
    """

    LOGIN_URL = "https://sitiospublicos.bancochile.cl/personas"

    def _get_bank_id(self) -> str:
        return "cl_banco_chile"

    def _login(self) -> None:
        """Implements the login logic for Banco de Chile."""
        assert self.user is not None, "User must be provided"
        assert self.password is not None, "Password must be provided"
        
        page = self._ensure_page()
        logger.info("Logging into Banco de Chile.")
        self._navigate(self.LOGIN_URL)
        self._save_debug_info("01_login_page")

        # Look for login button - try multiple possible selectors
        logger.info("Looking for login access button.")
        login_selectors = [
            'a:has-text("Ingresar")',
            'button:has-text("Ingresar")',
            'a:has-text("Banco en Línea")',
            'a[href*="login"]',
            'button[data-test*="login"]',
            'a:has-text("Acceder")',
            '.login-button',
            '[data-cy="login"]'
        ]
        
        login_clicked = False
        for selector in login_selectors:
            try:
                if page.locator(selector).is_visible(timeout=3000):
                    logger.info(f"Found login button with selector: {selector}")
                    self._click(selector)
                    login_clicked = True
                    break
            except Exception:
                continue
        
        if not login_clicked:
            # If no login button found, try direct navigation to login URL
            logger.info("No login button found, trying direct navigation to login page.")
            login_urls = [
                "https://login.portales.bancochile.cl/login",
                "https://portalpersonas.bancochile.cl/login",
                "https://sitiospublicos.bancochile.cl/personas/login"
            ]
            
            for login_url in login_urls:
                try:
                    self._navigate(login_url)
                    if page.locator('input[name="username"], input[name="rut"], role=textbox[name="RUT"]').is_visible(timeout=5000):
                        logger.info(f"Successfully navigated to login page: {login_url}")
                        break
                except Exception:
                    continue

        # Wait for login form elements with multiple possible selectors
        form_selectors = [
            'role=textbox[name="RUT"]',
            'input[name="username"]',
            'input[name="rut"]',
            'input[placeholder*="RUT"]',
            '#username',
            '#rut'
        ]
        
        form_found = False
        for selector in form_selectors:
            try:
                self._wait_for_selector(selector, timeout_override=10000)
                logger.info(f"Found login form with selector: {selector}")
                form_found = True
                break
            except Exception:
                continue
        
        if not form_found:
            self._save_debug_info("login_form_not_found")
            raise LoginError("Could not find login form after multiple attempts")
            
        self._save_debug_info("01a_login_frame_loaded")

        logger.info("Entering credentials.")
        
        # Find and fill username/RUT field
        username_selectors = [
            'role=textbox[name="RUT"]',
            'input[name="username"]',
            'input[name="rut"]',
            'input[placeholder*="RUT"]',
            '#username',
            '#rut'
        ]
        
        username_filled = False
        for selector in username_selectors:
            try:
                if page.locator(selector).is_visible(timeout=3000):
                    self._type(selector, self.user, delay=120)
                    logger.info(f"Filled username with selector: {selector}")
                    username_filled = True
                    break
            except Exception:
                continue
        
        if not username_filled:
            raise LoginError("Could not find username/RUT field")
        
        # Find and fill password field
        password_selectors = [
            'role=textbox[name="Contraseña"]',
            'input[name="password"]',
            'input[type="password"]',
            'input[placeholder*="contraseña"]',
            'input[placeholder*="Contraseña"]',
            '#password'
        ]
        
        password_filled = False
        for selector in password_selectors:
            try:
                if page.locator(selector).is_visible(timeout=3000):
                    self._type(selector, self.password, delay=120)
                    logger.info(f"Filled password with selector: {selector}")
                    password_filled = True
                    break
            except Exception:
                continue
        
        if not password_filled:
            raise LoginError("Could not find password field")
        
        self._save_debug_info("02_credentials_entered")

        logger.info("Submitting login form.")
        
        # Find and click submit button
        submit_selectors = [
            'role=button[name="Ingresar a cuenta"]',
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Ingresar")',
            'button:has-text("Entrar")',
            'button:has-text("Acceder")',
            '.login-submit',
            '[data-cy="submit"]'
        ]
        
        submit_clicked = False
        for selector in submit_selectors:
            try:
                if page.locator(selector).is_visible(timeout=3000):
                    self._click(selector)
                    logger.info(f"Clicked submit with selector: {selector}")
                    submit_clicked = True
                    break
            except Exception:
                continue
        
        if not submit_clicked:
            # Try pressing Enter as fallback
            logger.info("Could not find submit button, trying Enter key")
            page.keyboard.press("Enter")

        logger.info("Waiting for post-login page.")
        try:
            # The main menu is a good indicator of successful login
            expect(page.locator('button:has-text("Mis Productos")')).to_be_visible(
                timeout=40000
            )
            self._save_debug_info("03_login_success")
            logger.info("Login to Banco de Chile successful.")
        except PlaywrightTimeoutError:
            self._save_debug_info("post_login_error")
            raise LoginError(
                "Timeout or error after login to Banco de Chile. Check credentials or for an unexpected page (e.g., maintenance)."
            )

    def _close_popup(self) -> None:
        """Closes the initial marketing popup if it appears."""
        page = self._ensure_page()
        logger.info("Checking for marketing popup.")
        # This selector is based on the HTML provided, and updated to only
        # select the visible button, excluding a hidden one with the same classes.
        popup_close_button = page.locator(
            "button.btn.default.pull-right:has(i.ion-ios-close-empty):not([hidden])"
        )
        try:
            # Give it some time to appear
            if popup_close_button.is_visible(timeout=10000):
                self._click(popup_close_button)
                logger.info("Marketing popup closed.")
                self._save_debug_info("04_popup_closed")
        except (PlaywrightTimeoutError, DataExtractionError):
            logger.info(
                "No marketing popup found or it could not be closed, continuing."
            )

    def _extract_movements_from_table(
        self, currency: str, account_id: str
    ) -> List[MovementModel]:
        """Extracts all movements from the currently displayed table, handling pagination."""
        page = self._ensure_page()
        movements: List[MovementModel] = []

        # Wait for either the table or a "no info" message
        try:
            self._wait_for_selector(
                "table.bch-table, div.bch-alert:has-text('No existe información')",
                timeout_override=30000,
            )
        except DataExtractionError:
            logger.warning(
                f"Neither movements table nor 'no info' message appeared for account {account_id}."
            )
            return []

        if page.locator(
            "div.bch-alert:has-text('No existe información para la consulta solicitada')"
        ).is_visible():
            logger.info(f"No movements found for account {account_id} in {currency}.")
            return []

        logger.info(f"Extracting movements for account {account_id} in {currency}.")
        self._save_debug_info(f"movements_table_{currency}_{account_id}")

        page_num = 1
        while True:
            logger.info(f"Scraping page {page_num} for account {account_id}.")

            try:
                self._wait_for_selector(
                    "table.bch-table tbody tr.bch-row", timeout_override=15000
                )
            except DataExtractionError:
                logger.info("Movement table is present, but contains no rows.")
                break

            # Exclude detail rows that are also matched by .bch-row
            rows = page.locator(
                "table.bch-table tbody tr.bch-row:not(.table-collapse-row)"
            ).all()
            for row in rows:
                try:
                    date_str = row.locator("td.cdk-column-fechaContable").inner_text()
                    description = row.locator("td.cdk-column-descripcion").inner_text()
                    cargo_str = row.locator("td.cdk-column-cargo").inner_text()
                    abono_str = row.locator("td.cdk-column-abono").inner_text()

                    date = parse_chilean_date(date_str)
                    if not date:
                        logger.warning(
                            f"Could not parse date '{date_str}', skipping row."
                        )
                        continue

                    amount_str = f"-{cargo_str}" if cargo_str.strip() else abono_str
                    amount = parse_chilean_amount(amount_str)

                    if amount.is_zero():
                        continue

                    movements.append(
                        MovementModel(
                            date=date,
                            description=description.strip(),
                            amount=amount,
                            currency=currency,
                            transaction_type="Cargo" if amount < 0 else "Abono",
                            account_id=account_id,
                            account_type="corriente",
                            raw_data={
                                "date_str": date_str,
                                "cargo_str": cargo_str,
                                "abono_str": abono_str,
                                "full_account_id": account_id,
                            },
                        )
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to parse a movement row for {account_id}: {e}"
                    )

            next_button = page.locator('button[aria-label="Próxima página"]')
            # If the button doesn't exist/is not visible, or is disabled,
            # we're on the last page. A short timeout on is_visible handles
            # cases where the button doesn't exist at all.
            if not next_button.is_visible(timeout=3000) or next_button.is_disabled():
                logger.info(f"Last page of movements reached for account {account_id}.")
                break

            paginator_label = page.locator(
                "div.mat-paginator-range-actions .mat-paginator-label"
            )
            paginator_text_before = ""
            try:
                # A short timeout because if it's not there, we shouldn't wait long.
                paginator_text_before = paginator_label.inner_text(timeout=3000)
            except PlaywrightTimeoutError:
                logger.warning(
                    "Paginator label not found before clicking next. Waiting may be unreliable."
                )

            logger.info(f"Going to next page of movements for account {account_id}.")
            page_num += 1
            self._click(next_button)

            # Wait for the paginator text to change, which is a reliable signal that the
            # new page's data has loaded. This avoids flaky 'networkidle' waits.
            if paginator_text_before:
                try:
                    expect(paginator_label).not_to_have_text(
                        paginator_text_before, timeout=20000
                    )
                except PlaywrightTimeoutError:
                    logger.warning(
                        "Paginator text did not change after clicking next. "
                        "This might indicate a page load issue."
                    )
            else:
                # If we couldn't get paginator text, use a less reliable wait.
                page.wait_for_load_state("domcontentloaded", timeout=20000)

            self._save_debug_info(
                f"movements_table_{currency}_{account_id}_page_{page_num}"
            )

        logger.info(
            f"Extracted {len(movements)} movements for account {account_id} in {currency}."
        )
        return movements

    def _scrape_movements(self) -> List[MovementModel]:
        """Orchestrates the extraction of movements by iterating through accounts and currencies."""
        page = self._ensure_page()
        all_movements: List[MovementModel] = []

        self._close_popup()

        logger.info("Navigating to 'Saldos y Movimientos' section.")
        self._click('button:has-text("Mis Productos")')
        self._click('a[href="#/movimientos/cuenta/saldos-movimientos"]')
        self._save_debug_info("05_movements_section_clicked")

        self._wait_for_selector(
            'h2:has-text("Seleccione una cuenta")', timeout_override=30000
        )
        self._save_debug_info("06_account_selection_modal_opened")

        # Get all currency options text
        self._click('mat-select[name="monedas"]')
        currency_options_loc = page.locator("mat-option span.mat-option-text")
        currency_texts = [
            currency_options_loc.nth(i).inner_text()
            for i in range(currency_options_loc.count())
        ]
        currency_options_loc.first.click()  # Close dropdown
        logger.info(f"Found currencies: {currency_texts}")

        for i_currency, currency_text in enumerate(currency_texts):
            logger.info(f"Processing currency: {currency_text}")

            # Select currency in modal. The modal should already be open.
            self._click('mat-select[name="monedas"]')
            self._click(f'mat-option:has-text("{currency_text}")')
            page.wait_for_timeout(2000)  # Give time for accounts to load

            currency_code_match = re.search(r"\((.*?)\)", currency_text)
            if not currency_code_match:
                logger.warning(
                    f"Could not extract currency code from '{currency_text}', skipping."
                )
                continue
            currency_code = currency_code_match.group(1).strip()

            account_labels = [
                loc.inner_text().strip()
                for loc in page.locator(
                    "mat-radio-button .mat-radio-label-content"
                ).all()
            ]
            logger.info(
                f"Found {len(account_labels)} accounts for {currency_code}: {account_labels}"
            )

            for i_account, account_label in enumerate(account_labels):
                logger.info(
                    f"Processing account {i_account + 1}/{len(account_labels)}: {account_label}"
                )

                # Use nth to select the correct radio button to avoid ambiguity
                account_radio = page.locator("mat-radio-button").nth(i_account)

                match = re.search(r"([\d-]+)", account_label)
                account_id = (
                    match.group(1).strip() if match else f"unknown_{account_label}"
                )

                # Instructions say click twice.
                account_radio.click(click_count=2, delay=100)

                self._click(
                    'bch-button[id="modalPrimaryBtn"] button:has-text("Aceptar")'
                )

                movements = self._extract_movements_from_table(
                    currency_code, account_id
                )
                all_movements.extend(movements)

                is_last_overall_account = (i_currency == len(currency_texts) - 1) and (
                    i_account == len(account_labels) - 1
                )

                if not is_last_overall_account:
                    logger.info("Going back to account selection modal.")
                    # Try multiple selectors for "select another account" button/link
                    account_selection_selectors = [
                        'button:has-text("Seleccionar otra cuenta")',
                        'a:has-text("SELECCIONAR OTRA CUENTA")',
                        'a:has-text("Seleccionar otra cuenta")',
                        'button:has-text("SELECCIONAR OTRA CUENTA")',
                        '[data-test*="select-account"]',
                        'a[href*="seleccionar"]'
                    ]
                    
                    selection_clicked = False
                    for selector in account_selection_selectors:
                        try:
                            if page.locator(selector).is_visible(timeout=3000):
                                self._click(selector)
                                logger.info(f"Clicked account selection with selector: {selector}")
                                selection_clicked = True
                                break
                        except Exception:
                            continue
                    
                    if not selection_clicked:
                        logger.warning("Could not find 'select another account' button, trying navigation workaround")
                        # Alternative: navigate back to the movements section
                        try:
                            self._click('a[href="#/movimientos/cuenta/saldos-movimientos"]')
                        except Exception:
                            self._click('button:has-text("Mis Productos")')
                            self._click('a[href="#/movimientos/cuenta/saldos-movimientos"]')
                    
                    # Wait for account selection modal with more flexible selectors
                    modal_selectors = [
                        'h2:has-text("Seleccione una cuenta")',
                        'h1:has-text("Seleccione una cuenta")',
                        '.modal-title:has-text("Seleccione")',
                        'mat-select[name="monedas"]'
                    ]
                    
                    modal_found = False
                    for selector in modal_selectors:
                        try:
                            self._wait_for_selector(selector, timeout_override=10000)
                            logger.info(f"Found account selection modal with selector: {selector}")
                            modal_found = True
                            break
                        except Exception:
                            continue
                    
                    if not modal_found:
                        logger.warning("Could not find account selection modal, continuing anyway")

                    # If there are more accounts for the same currency, we need to reselect the currency
                    # to have the list of accounts ready for the next iteration.
                    if i_account < len(account_labels) - 1:
                        self._click('mat-select[name="monedas"]')
                        self._click(f'mat-option:has-text("{currency_text}")')
                        page.wait_for_timeout(2000)

        logger.info(
            f"Scraping completed. Total movements extracted: {len(all_movements)}"
        )
        return all_movements
