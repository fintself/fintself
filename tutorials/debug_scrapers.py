import os
import sys
from dotenv import load_dotenv

from fintself import get_scraper
from fintself.utils.logging import logger
from fintself.utils.output import save_to_xlsx

# Carga las variables de entorno desde un archivo .env.
load_dotenv()

# --- Configuración de Depuración ---
# Modifica esta variable para elegir qué banco quieres depurar.
# Opciones disponibles: "cl_santander", "cl_banco_chile", "cl_cencosud"
# BANK_TO_DEBUG = "cl_santander"
# BANK_TO_DEBUG = "cl_cencosud"
BANK_TO_DEBUG = "cl_banco_chile"


def main():
    """
    Función principal para ejecutar un scraper específico en modo de depuración.
    Este modo muestra el navegador y guarda capturas de pantalla/HTML en `debug_output/`.
    """
    logger.info(f"--- Iniciando sesión de depuración para: {BANK_TO_DEBUG} ---")

    # Construye los nombres de las variables de entorno
    user_env_var = f"{BANK_TO_DEBUG.upper()}_USER"
    password_env_var = f"{BANK_TO_DEBUG.upper()}_PASSWORD"

    # Obtiene las credenciales
    user = os.getenv(user_env_var)
    password = os.getenv(password_env_var)

    if not user or not password:
        logger.error(
            f"Credenciales para {BANK_TO_DEBUG} no encontradas. "
            f"Asegúrate de definir {user_env_var} y {password_env_var} en tu archivo .env."
        )
        sys.exit(1)

    try:
        # Obtiene la instancia del scraper en modo de depuración.
        # Pasamos `debug_mode=True` explícitamente para forzar este modo,
        # sin importar lo que esté configurado en el archivo .env.
        # Esto automáticamente hace que headless sea False.
        scraper = get_scraper(BANK_TO_DEBUG, debug_mode=True)

        # Ejecuta el scraper
        movements = scraper.scrape(user=user, password=password)

        if movements:
            output_filename = f"outputs/{BANK_TO_DEBUG}_movements.xlsx"
            save_to_xlsx(movements, output_filename)
            logger.success(
                f"Depuración finalizada. Se encontraron y guardaron {len(movements)} movimientos para {BANK_TO_DEBUG} en '{output_filename}'."
            )
        else:
            logger.info(
                f"Depuración finalizada. No se encontraron movimientos para {BANK_TO_DEBUG}."
            )

        logger.info(
            "Revisa la carpeta 'debug_output' para ver las capturas de pantalla y archivos HTML."
        )

    except Exception as e:
        logger.error(
            f"Ocurrió un error durante la depuración de {BANK_TO_DEBUG}: {e}",
            exc_info=True,
        )
        logger.info(
            "Revisa la carpeta 'debug_output' para ver las capturas de pantalla y archivos HTML del error."
        )


if __name__ == "__main__":
    main()
