import datetime
import json
import os
import platform
import random
import time
from abc import ABC, abstractmethod
from typing import List, Literal, Optional, Union

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    Playwright,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from fintself import settings
from fintself.core.exceptions import DataExtractionError, LoginError
from fintself.core.models import MovementModel
from fintself.utils.logging import logger


class BaseScraper(ABC):
    """
    Abstract base class for all bank scrapers.
    It defines the common interface for authentication and data extraction.
    """

    def __init__(
        self,
        headless: Optional[bool] = None,
        debug_mode: Optional[bool] = None,
        debug_dir: str = "debug_output",
    ):
        """
        Initializes the base scraper.

        Args:
            headless (bool): If True, the browser runs without a graphical interface.
            debug_mode (bool): If True, saves screenshots and HTML for debugging.
            debug_dir (str): Directory where debug files will be saved.
        """
        self.debug_mode = settings.DEBUG if debug_mode is None else debug_mode
        self.headless = settings.SCRAPER_HEADLESS_MODE if headless is None else headless
        self.debug_dir = debug_dir
        if self.debug_mode:
            os.makedirs(self.debug_dir, exist_ok=True)
            self.headless = False

        self.default_timeout = settings.SCRAPER_DEFAULT_TIMEOUT
        self.slow_mo = settings.SCRAPER_SLOW_MO
        self.user_agent = settings.SCRAPER_USER_AGENT
        self.viewport = {
            "width": settings.SCRAPER_VIEWPORT_WIDTH,
            "height": settings.SCRAPER_VIEWPORT_HEIGHT,
        }
        self.locale = settings.SCRAPER_LOCALE
        self.timezone_id = settings.SCRAPER_TIMEZONE_ID
        self.browser_channel = settings.SCRAPER_BROWSER_CHANNEL
        self.browser_executable = settings.SCRAPER_BROWSER_EXECUTABLE
        self.min_human_delay_ms = settings.SCRAPER_MIN_HUMAN_DELAY_MS
        self.max_human_delay_ms = settings.SCRAPER_MAX_HUMAN_DELAY_MS

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.user: Optional[str] = None
        self.password: Optional[str] = None
        self._effective_user_agent: Optional[str] = None
        self._user_agent_version: Optional[str] = None
        self.chrome_user_data_dir = settings.SCRAPER_CHROME_USER_DATA_DIR

    @abstractmethod
    def _get_bank_id(self) -> str:
        """Returns the unique bank identifier (e.g., 'cl_santander')."""
        pass

    @abstractmethod
    def _login(self) -> None:
        """Implements the bank-specific login logic."""
        pass

    @abstractmethod
    def _scrape_movements(self) -> List[MovementModel]:
        """Implements the bank-specific movement extraction logic."""
        pass

    def _ensure_page(self) -> Page:
        """Ensures the page object is initialized, raising an error if not."""
        if not self.page:
            raise DataExtractionError(
                "Page not initialized. Scraper might not have been started correctly."
            )
        return self.page

    def _human_delay(
        self,
        min_override_ms: Optional[float] = None,
        max_override_ms: Optional[float] = None,
    ) -> None:
        """Waits for a random time to simulate human behavior."""
        min_d = (
            min_override_ms if min_override_ms is not None else self.min_human_delay_ms
        )
        max_d = (
            max_override_ms if max_override_ms is not None else self.max_human_delay_ms
        )
        if min_d <= 0 and max_d <= 0:
            return
        delay_seconds = random.uniform(
            min(min_d, max_d) / 1000.0, max(min_d, max_d) / 1000.0
        )
        logger.trace(f"Applying human delay: {delay_seconds:.3f} seconds.")
        time.sleep(delay_seconds)

    def _platform_token(self) -> str:
        """Returns the user-agent platform token matching the current OS."""
        system = platform.system()
        if system == "Windows":
            return "Windows NT 10.0; Win64; x64"
        if system == "Darwin":
            return "Macintosh; Intel Mac OS X 10_15_7"
        return "X11; Linux x86_64"

    def _platform_name(self) -> str:
        """Returns a human-readable platform name for client hints."""
        system = platform.system()
        if system == "Windows":
            return "Windows"
        if system == "Darwin":
            return "macOS"
        return "Linux"

    def _platform_version(self) -> str:
        """Returns a plausible platform version string for client hints."""
        system = platform.system()
        if system == "Windows":
            return "10.0.0"
        if system == "Darwin":
            return "13.5.0"
        return "6.9.0"

    def _resolve_user_agent(self) -> Optional[str]:
        """Determines the user agent string to use for the browser context."""
        if self.user_agent:
            self._effective_user_agent = self.user_agent
            return self.user_agent

        version = self._user_agent_version
        if not version and self.browser:
            try:
                browser_version = self.browser.version
                if browser_version and "/" in browser_version:
                    _, version = browser_version.split("/", 1)
                else:
                    version = browser_version
            except Exception:
                version = None

        if not version:
            self._effective_user_agent = None
            return None

        self._user_agent_version = version
        resolved = (
            f"Mozilla/5.0 ({self._platform_token()}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
        )
        self._effective_user_agent = resolved
        return resolved

    def _stealth_init_script(self) -> str:
        """Returns a script that removes common automation fingerprints."""
        languages = [self.locale]
        base_lang = self.locale.split("-")[0]
        if base_lang not in languages:
            languages.append(base_lang)
        lang_array_literal = json.dumps(languages)
        platform_token = self._platform_token()
        platform_name = self._platform_name()
        platform_version = self._platform_version()
        ua_version = self._user_agent_version or "120.0.0.0"
        major_version = ua_version.split(".")[0]
        brands = [
            {"brand": "Not A(Brand", "version": "99"},
            {"brand": "Google Chrome", "version": major_version},
            {"brand": "Chromium", "version": major_version},
        ]
        brands_literal = json.dumps(brands)

        return (
            "(() => {"
            "  const overrideProperty = (object, property, value) => {"
            "    if (!object) { return; }"
            "    try {"
            "      Object.defineProperty(object, property, {"
            "        configurable: true,"
            "        get: () => value,"
            "      });"
            "    } catch (error) {}"
            "  };"
            "  try {"
            "    overrideProperty(navigator, 'webdriver', undefined);"
            f"    overrideProperty(navigator, 'languages', {lang_array_literal});"
            f"    overrideProperty(navigator, 'language', '{languages[0]}');"
            f"    overrideProperty(navigator, 'platform', '{platform_token}');"
            "    overrideProperty(navigator, 'maxTouchPoints', 0);"
            "    overrideProperty(navigator, 'hardwareConcurrency', 8);"
            "    overrideProperty(navigator, 'deviceMemory', 8);"
            "    overrideProperty(navigator, 'pdfViewerEnabled', true);"
            "    overrideProperty(navigator, 'onLine', true);"
            "    const fakePlugins = (() => {"
            "      const plugins = ["
            "        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },"
            "        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },"
            "        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },"
            "      ];"
            "      return Object.assign(plugins, {"
            "        length: plugins.length,"
            "        item: (index) => plugins[index],"
            "        namedItem: (name) => plugins.find((plugin) => plugin.name === name),"
            "      });"
            "    })();"
            "    overrideProperty(navigator, 'plugins', fakePlugins);"
            "    const fakeMimeTypes = (() => {"
            "      const mimeTypes = ["
            "        { type: 'application/pdf', suffixes: 'pdf', description: '', enabledPlugin: fakePlugins[0] },"
            "        { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: '', enabledPlugin: fakePlugins[1] },"
            "      ];"
            "      return Object.assign(mimeTypes, {"
            "        length: mimeTypes.length,"
            "        item: (index) => mimeTypes[index],"
            "        namedItem: (name) => mimeTypes.find((mime) => mime.type === name),"
            "      });"
            "    })();"
            "    overrideProperty(navigator, 'mimeTypes', fakeMimeTypes);"
            "    if (!window.chrome) {"
            "      window.chrome = { runtime: {}, app: { isInstalled: false }, webstore: { onInstallStageChanged: {}, onDownloadProgress: {} } };"
            "    } else {"
            "      if (!window.chrome.runtime) { window.chrome.runtime = {}; }"
            "    }"
            "    const originalPermissions = navigator.permissions;"
            "    if (originalPermissions && originalPermissions.query) {"
            "      const originalQuery = originalPermissions.query.bind(originalPermissions);"
            "      navigator.permissions.query = (parameters) => {"
            "        if (parameters && parameters.name === 'notifications') {"
            "          return Promise.resolve({ state: Notification.permission });"
            "        }"
            "        return originalQuery(parameters);"
            "      };"
            "    }"
            "    const connection = {"
            "      downlink: 10,"
            "      effectiveType: '4g',"
            "      rtt: 45,"
            "      saveData: false,"
            "    };"
            "    overrideProperty(navigator, 'connection', connection);"
            f"    const userAgentDataBrands = {brands_literal};"
            f"    const userAgentDataPlatform = '{platform_name}';"
            "    if (navigator.userAgentData) {"
            "      overrideProperty(navigator.userAgentData, 'brands', userAgentDataBrands);"
            "      overrideProperty(navigator.userAgentData, 'mobile', false);"
            "      overrideProperty(navigator.userAgentData, 'platform', userAgentDataPlatform);"
            "      if (navigator.userAgentData.getHighEntropyValues) {"
            "        const originalGetHighEntropyValues = navigator.userAgentData.getHighEntropyValues.bind(navigator.userAgentData);"
            "        navigator.userAgentData.getHighEntropyValues = (hints) => originalGetHighEntropyValues(hints).then((values) => {"
            f"          values.platform = userAgentDataPlatform;"
            f"          values.platformVersion = '{platform_version}';"
            f"          values.uaFullVersion = '{ua_version}';"
            "          values.architecture = 'x86';"
            "          values.bitness = '64';"
            "          values.model = '';"
            "          return values;"
            "        });"
            "      }"
            "    }"
            "  } catch (error) {"
            "    console.debug('Stealth script error', error);"
            "  }"
            "})();"
        )

    def _navigate(self, url: str, timeout_override: Optional[int] = None) -> None:
        """Navigates to a URL with error handling and human-like delay."""
        page = self._ensure_page()
        timeout = (
            timeout_override if timeout_override is not None else self.default_timeout
        )
        logger.debug(f"Navigating to {url} with timeout {timeout}ms.")
        try:
            page.goto(url, timeout=timeout)
            self._human_delay()
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout navigating to {url}: {e}")
            raise DataExtractionError(f"Timeout navigating to {url}")
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}", exc_info=self.debug_mode)
            raise DataExtractionError(f"Error navigating to {url}: {e}")

    def _click(
        self, selector: Union[str, Locator], timeout_override: Optional[int] = None
    ) -> None:
        """Clicks an element with error handling and human-like interaction."""
        page = self._ensure_page()
        timeout = (
            timeout_override if timeout_override is not None else self.default_timeout
        )
        logger.debug(f"Clicking selector '{str(selector)}' with timeout {timeout}ms.")
        try:
            element = page.locator(selector) if isinstance(selector, str) else selector
            element.first.wait_for(state="visible", timeout=timeout)
            element.first.hover(timeout=timeout)
            self._human_delay(min_override_ms=50, max_override_ms=150)
            element.first.click(timeout=timeout)
            self._human_delay()
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout clicking selector '{str(selector)}': {e}")
            raise DataExtractionError(f"Timeout clicking selector '{str(selector)}'")
        except Exception as e:
            logger.error(
                f"Error clicking selector '{str(selector)}': {e}",
                exc_info=self.debug_mode,
            )
            raise DataExtractionError(f"Error clicking selector '{str(selector)}': {e}")

    def _fill(
        self,
        selector: Union[str, Locator],
        text: str,
        delay: int = 50,
        timeout_override: Optional[int] = None,
    ) -> None:
        """Fills an input by clearing it and then typing character by character."""
        page = self._ensure_page()
        timeout = (
            timeout_override if timeout_override is not None else self.default_timeout
        )
        logger.debug(
            f"Filling selector '{str(selector)}' by typing with delay {delay}ms."
        )
        try:
            element = page.locator(selector) if isinstance(selector, str) else selector
            element.first.wait_for(state="visible", timeout=timeout)
            # Clear the input first, then type to simulate human behavior.
            element.first.fill("", timeout=timeout)
            element.first.type(text, delay=delay, timeout=timeout)
            self._human_delay()
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout filling selector '{str(selector)}': {e}")
            raise DataExtractionError(f"Timeout filling selector '{str(selector)}'")
        except Exception as e:
            logger.error(
                f"Error filling selector '{str(selector)}': {e}",
                exc_info=self.debug_mode,
            )
            raise DataExtractionError(f"Error filling selector '{str(selector)}': {e}")

    def _type(
        self,
        selector: Union[str, Locator],
        text: str,
        delay: int = 100,
        timeout_override: Optional[int] = None,
    ) -> None:
        """Types text into an element character by character."""
        page = self._ensure_page()
        timeout = (
            timeout_override if timeout_override is not None else self.default_timeout
        )
        logger.debug(f"Typing into selector '{str(selector)}'.")
        try:
            element = page.locator(selector) if isinstance(selector, str) else selector
            element.first.wait_for(state="visible", timeout=timeout)
            element.first.type(text, delay=delay, timeout=timeout)
            self._human_delay()
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout typing into selector '{str(selector)}': {e}")
            raise DataExtractionError(f"Timeout typing into selector '{str(selector)}'")
        except Exception as e:
            logger.error(
                f"Error typing into selector '{str(selector)}': {e}",
                exc_info=self.debug_mode,
            )
            raise DataExtractionError(
                f"Error typing into selector '{str(selector)}': {e}"
            )

    def _wait_for_selector(
        self,
        selector: Union[str, Locator],
        state: Literal["attached", "detached", "hidden", "visible"] = "visible",
        timeout_override: Optional[int] = None,
    ) -> Locator:
        """Waits for a selector to be in a specific state."""
        page = self._ensure_page()
        timeout = (
            timeout_override if timeout_override is not None else self.default_timeout
        )
        logger.debug(
            f"Waiting for selector '{str(selector)}' (state: {state}) with timeout {timeout}ms."
        )
        try:
            element = page.locator(selector) if isinstance(selector, str) else selector
            element.first.wait_for(state=state, timeout=timeout)
            return element
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout waiting for selector '{str(selector)}': {e}")
            raise DataExtractionError(f"Timeout waiting for selector '{str(selector)}'")
        except Exception as e:
            logger.error(
                f"Error waiting for selector '{str(selector)}': {e}",
                exc_info=self.debug_mode,
            )
            raise DataExtractionError(
                f"Error waiting for selector '{str(selector)}': {e}"
            )

    def _save_debug_info(self, step_name: str) -> None:
        """Saves a screenshot and the current page's HTML for debugging."""
        if not self.debug_mode or not self.page:
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bank_id = self._get_bank_id()
        debug_path = os.path.join(self.debug_dir, bank_id)
        os.makedirs(debug_path, exist_ok=True)

        screenshot_path = os.path.join(debug_path, f"{timestamp}_{step_name}.png")
        html_path = os.path.join(debug_path, f"{timestamp}_{step_name}.html")

        try:
            self.page.screenshot(path=screenshot_path, full_page=True)
            logger.debug(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save screenshot for {step_name}: {e}")

        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.page.content())
            logger.debug(f"HTML saved to: {html_path}")
        except Exception as e:
            logger.warning(f"Could not save HTML for {step_name}: {e}")

    def scrape(self, user: str, password: str) -> List[MovementModel]:
        """
        Executes the entire scraping process: starts the browser,
        logs in, and extracts the data.
        """
        self.user = user
        self.password = password

        with sync_playwright() as p:
            self.playwright = p
            try:
                self.browser = None
                self.browser_context = None
                self.page = None

                version_hint = getattr(self.playwright.chromium, "version", None)
                if version_hint:
                    version_str = str(version_hint).strip()
                    if version_str:
                        self._user_agent_version = version_str.split(" ")[-1]
                resolved_user_agent = self._resolve_user_agent()

                launch_options = {
                    "headless": self.headless,
                    "slow_mo": self.slow_mo,
                }

                info_parts: List[str] = []
                if self.browser_executable:
                    launch_options["executable_path"] = self.browser_executable
                    info_parts.append(f"executable: {self.browser_executable}")
                    if self.browser_channel:
                        logger.warning(
                            "Both SCRAPER_BROWSER_EXECUTABLE and SCRAPER_BROWSER_CHANNEL are set; "
                            "the executable path will take precedence."
                        )
                elif self.browser_channel:
                    launch_options["channel"] = self.browser_channel
                    info_parts.append(f"channel: {self.browser_channel}")
                else:
                    info_parts.append("channel: bundled-chromium")

                args = launch_options.setdefault("args", [])
                extra_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    f"--lang={self.locale}",
                    "--start-maximized",
                ]
                for arg in extra_args:
                    if arg not in args:
                        args.append(arg)

                ignore_defaults = launch_options.setdefault("ignore_default_args", [])
                if "--enable-automation" not in ignore_defaults:
                    ignore_defaults.append("--enable-automation")

                profile_label = (
                    f"profile: {self.chrome_user_data_dir}"
                    if self.chrome_user_data_dir
                    else "profile: ephemeral"
                )
                info_parts.append(profile_label)
                info_parts.append(
                    "ua: custom" if self.user_agent or resolved_user_agent else "ua: auto"
                )

                logger.info(
                    "Launching browser for {} (headless: {}, {})...",
                    self._get_bank_id(),
                    self.headless,
                    ", ".join(info_parts),
                )

                context_options = {
                    "viewport": self.viewport,
                    "locale": self.locale,
                    "timezone_id": self.timezone_id,
                }
                if resolved_user_agent:
                    context_options["user_agent"] = resolved_user_agent

                if self.chrome_user_data_dir:
                    os.makedirs(self.chrome_user_data_dir, exist_ok=True)
                    persistent_options = {**launch_options, **context_options}
                    self.browser_context = (
                        self.playwright.chromium.launch_persistent_context(
                            self.chrome_user_data_dir,
                            **persistent_options,
                        )
                    )
                    self.browser = self.browser_context.browser
                    for existing_page in list(self.browser_context.pages):
                        try:
                            existing_page.close()
                        except Exception:
                            pass
                else:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                    self.browser_context = self.browser.new_context(**context_options)

                if not self._effective_user_agent:
                    self._resolve_user_agent()

                self.browser_context.add_init_script(self._stealth_init_script())
                self.page = self.browser_context.new_page()
                self.page.set_default_timeout(self.default_timeout)

                try:
                    reported_user_agent = self.page.evaluate(
                        "() => navigator.userAgent"
                    )
                    logger.debug(
                        "navigator.userAgent reported as: {}", reported_user_agent
                    )
                    if self._effective_user_agent:
                        logger.debug(
                            "navigator.userAgent override in effect: {}",
                            self._effective_user_agent,
                        )
                except Exception as ua_err:
                    logger.debug(
                        "Could not read navigator.userAgent: {}", ua_err
                    )

                logger.info(f"Logging into {self._get_bank_id()}...")
                self._login()
                logger.info(f"Successfully logged into {self._get_bank_id()}.")

                logger.info(f"Extracting movements from {self._get_bank_id()}...")
                movements = self._scrape_movements()
                logger.info(
                    f"Extraction of {len(movements)} movements completed for {self._get_bank_id()}."
                )

                return movements

            except (LoginError, DataExtractionError):
                if self.page:
                    self._save_debug_info("scraping_error")
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error during scraping for {self._get_bank_id()}: {e}",
                    exc_info=True,
                )
                if self.page:
                    self._save_debug_info("unexpected_error")
                raise
            finally:
                try:
                    if self.browser_context:
                        self.browser_context.close()
                        logger.info(
                            f"Browser context closed for {self._get_bank_id()}."
                        )
                    elif self.browser:
                        self.browser.close()
                        logger.info(f"Browser closed for {self._get_bank_id()}.")
                finally:
                    self.browser_context = None
                    self.browser = None
        return []
