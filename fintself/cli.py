import os
from getpass import getpass
from typing import Optional

import typer
from dotenv import load_dotenv

load_dotenv()

from fintself.core.exceptions import FintselfException
from fintself.scrapers import get_scraper, list_available_scrapers
from fintself.utils.logging import logger
from fintself.utils.output import (
    get_output_data,
    save_to_csv,
    save_to_json,
    save_to_xlsx,
)

app = typer.Typer(
    name="fintself",
    help="Fintself: Scraper de movimientos bancarios open source y colaborativo.",
    add_completion=False,
    rich_markup_mode="markdown",
)


@app.command(name="list")
def list_scrapers_command():
    """
    Lists all available bank scrapers.
    """
    logger.info("Scrapers de bancos disponibles:")
    scrapers = list_available_scrapers()
    if not scrapers:
        logger.warning("No se encontraron scrapers disponibles.")
        return

    for bank_id, description in scrapers.items():
        typer.echo(f"- {typer.style(bank_id, fg=typer.colors.GREEN)}: {description}")


@app.command(name="scrape")
def scrape_bank_command(
    bank_id: str = typer.Argument(
        ..., help="El identificador del banco a scrapear (ej: cl_santander)."
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output-file",
        "-o",
        help="Ruta al archivo de salida (ej: mis_datos.xlsx). El formato se infiere de la extensión.",
    ),
    output_format: Optional[str] = typer.Option(
        None,
        "--output-format",
        "-f",
        help="Formato de salida para la consola si no se usa un archivo. Opciones: json, csv.",
        case_sensitive=False,
    ),
    debug_mode: Optional[bool] = typer.Option(
        None,
        "--debug/--no-debug",
        help="Habilita o deshabilita el modo de depuración, sobreescribiendo la configuración del .env.",
        show_default=False,
    ),
    headless: Optional[bool] = typer.Option(
        None,
        "--headless/--no-headless",
        help="Ejecuta o no el navegador en modo headless, sobreescribiendo la configuración del .env.",
        show_default=False,
    ),
):
    """
    Executes a scraper to extract bank movements.
    """
    if not output_file and not output_format:
        logger.error(
            "Debe especificar --output-file para guardar la salida o --output-format para imprimirla en consola."
        )
        raise typer.Exit(code=1)

    if output_file and output_format:
        logger.warning(
            "Se especificaron --output-file y --output-format. Se priorizará --output-file."
        )
        output_format = None

    file_format = None
    if output_file:
        _, ext = os.path.splitext(output_file)
        ext = ext.lower()
        if ext == ".xlsx":
            file_format = "xlsx"
        elif ext == ".csv":
            file_format = "csv"
        elif ext == ".json":
            file_format = "json"
        else:
            logger.error(
                f"Extensión de archivo '{ext}' no soportada. Use .xlsx, .csv, o .json."
            )
            raise typer.Exit(code=1)

    user_env_var = f"{bank_id.upper().replace('-', '_')}_USER"
    password_env_var = f"{bank_id.upper().replace('-', '_')}_PASSWORD"

    user = os.getenv(user_env_var)
    password = os.getenv(password_env_var)

    if not user:
        user = typer.prompt(f"Usuario para {bank_id}")
    if not password:
        password = getpass(f"Contraseña para {bank_id}: ")

    try:
        # Pass overrides to scraper factory. If None, settings from .env will be used.
        scraper = get_scraper(bank_id, headless=headless, debug_mode=debug_mode)
        movements = scraper.scrape(user=user, password=password)

        if not movements:
            logger.info("No se encontraron movimientos.")
            raise typer.Exit(code=0)

        if output_file:
            if file_format == "xlsx":
                save_to_xlsx(movements, output_file)
            elif file_format == "csv":
                save_to_csv(movements, output_file)
            elif file_format == "json":
                save_to_json(movements, output_file)
            logger.info(f"Scraping completado. Datos guardados en {output_file}")
        elif output_format in ["json", "csv"]:
            output_data = get_output_data(movements, output_format)
            typer.echo(output_data)
            logger.info("Scraping completado. Datos impresos en consola.")
        else:
            logger.error(
                f"Formato de salida '{output_format}' no válido. Use 'json' o 'csv'."
            )
            raise typer.Exit(code=1)

    except FintselfException as e:
        logger.error(f"Error en el scraping: {e.message}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado: {e}", exc_info=debug_mode)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
