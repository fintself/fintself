import os
from dotenv import load_dotenv

from fintself import get_scraper
from fintself.utils.logging import logger
from fintself.utils.output import save_to_xlsx

# Carga las variables de entorno desde un archivo .env.
# Asegúrate de tener tu archivo .env en la raíz del proyecto.
load_dotenv()

# Lista de todos los bancos que quieres procesar
BANKS_TO_SCRAPE = ["cl_santander", "cl_banco_chile", "cl_cencosud"]


def main():
    """
    Función principal que ejecuta los scrapers para todos los bancos.

    Para ejecutar en modo visible (viendo el navegador), asegúrate de tener la
    siguiente línea en tu archivo .env:
    SCRAPER_HEADLESS_MODE=false
    """
    for bank_id in BANKS_TO_SCRAPE:
        logger.info(f"--- Iniciando proceso para: {bank_id} ---")

        # Construye los nombres de las variables de entorno para las credenciales
        user_env_var = f"{bank_id.upper()}_USER"
        password_env_var = f"{bank_id.upper()}_PASSWORD"

        # Obtiene las credenciales desde el entorno
        user = os.getenv(user_env_var)
        password = os.getenv(password_env_var)

        if not user or not password:
            logger.warning(
                f"Credenciales para {bank_id} no encontradas en el archivo .env. Saltando..."
            )
            continue

        try:
            # Obtiene la instancia del scraper. La configuración (headless, debug)
            # se tomará del archivo .env
            scraper = get_scraper(bank_id, headless=False)

            # Ejecuta el scraper
            movements = scraper.scrape(user=user, password=password)

            if movements:
                output_filename = f"outputs/{bank_id}_movements.xlsx"
                save_to_xlsx(movements, output_filename)
                logger.success(
                    f"Se encontraron y guardaron {len(movements)} movimientos para {bank_id} en '{output_filename}'."
                )
            else:
                logger.info(f"No se encontraron movimientos para {bank_id}.")

        except Exception as e:
            logger.error(f"Ocurrió un error al procesar {bank_id}: {e}", exc_info=True)


if __name__ == "__main__":
    main()
