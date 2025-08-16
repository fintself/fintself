class FintselfException(Exception):
    """Base exception for all Fintself specific errors."""

    pass


class LoginError(FintselfException):
    """Exception raised when a bank login fails."""

    def __init__(
        self,
        message="Login failed. Incorrect credentials or website issue.",
    ):
        self.message = message
        super().__init__(self.message)


class DataExtractionError(FintselfException):
    """Exception raised when data extraction from the bank fails."""

    def __init__(
        self,
        message="Data extraction failed. The website structure may have changed.",
    ):
        self.message = message
        super().__init__(self.message)


class ScraperNotFound(FintselfException):
    """Exception raised when the requested scraper is not found."""

    def __init__(self, bank_id: str):
        self.message = f"Scraper '{bank_id}' not found. Use 'fintself list' to see available ones."
        super().__init__(self.message)


class OutputError(FintselfException):
    """Exception raised when there is a problem generating the output file."""

    def __init__(self, message="Error generating output file."):
        self.message = message
        super().__init__(self.message)
