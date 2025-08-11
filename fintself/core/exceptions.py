class FintselfException(Exception):
    """Base exception for all Fintself specific errors."""

    pass


class LoginError(FintselfException):
    """Exception raised when a bank login fails."""

    def __init__(
        self,
        message="Fallo al iniciar sesión. Credenciales incorrectas o problema en el sitio web.",
    ):
        self.message = message
        super().__init__(self.message)


class DataExtractionError(FintselfException):
    """Exception raised when data extraction from the bank fails."""

    def __init__(
        self,
        message="Fallo al extraer datos. La estructura del sitio web pudo haber cambiado.",
    ):
        self.message = message
        super().__init__(self.message)


class ScraperNotFound(FintselfException):
    """Exception raised when the requested scraper is not found."""

    def __init__(self, bank_id: str):
        self.message = f"Scraper '{bank_id}' no encontrado. Usa 'fintself list' para ver los disponibles."
        super().__init__(self.message)


class OutputError(FintselfException):
    """Exception raised when there is a problem generating the output file."""

    def __init__(self, message="Error al generar el archivo de salida."):
        self.message = message
        super().__init__(self.message)
