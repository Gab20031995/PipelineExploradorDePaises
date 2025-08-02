import os
import logging
from datetime import datetime
import pandas as pd
import mysql.connector

BASE_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(BASE_PIPELINE_DIR, exist_ok=True) 

log_file_path = os.path.join(BASE_PIPELINE_DIR, "pipeline_flow.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_db_connection_pipeline(db_config: dict):
    """Retorna una nueva conexión a la base de datos para el pipeline."""
    return mysql.connector.connect(**db_config)

def get_all_cca3_with_raw_data(db_config: dict) -> list:
    """
    Obtiene una lista de todos los CCA3 únicos de países que tienen datos
    en la tabla weather_raw_data o saved_countries.
    """
    conn = None
    cca3_list = []
    try:
        conn = get_db_connection_pipeline(db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT cca3 FROM weather_raw_data")
        raw_cca3 = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT cca3 FROM saved_countries")
        saved_cca3 = [row[0] for row in cursor.fetchall()]
        cca3_list = list(set(raw_cca3 + saved_cca3))
        cursor.close()
    except mysql.connector.Error as err:
        logging.error(f"Error al obtener CCA3s para el pipeline: {err}", exc_info=True)
    finally:
        if conn:
            conn.close()
    return cca3_list

def run_weather_pipeline(cca3: str = None, db_config: dict = None):
    """
    Ejecuta el pipeline de limpieza y carga para los datos de clima.
    Si cca3 es None, procesa todos los países con datos crudos.
    """
    if db_config is None:
        logging.error("run_weather_pipeline: db_config no proporcionado.")
        return

    conn = None
    try:
        conn = get_db_connection_pipeline(db_config)
        cursor = conn.cursor()
        cca3_to_process = [cca3] if cca3 else get_all_cca3_with_raw_data(db_config)
        
        if not cca3_to_process:
            logging.info("Pipeline: No hay CCA3s para procesar en esta ejecución.")
            return

        total_records_read = 0
        total_records_cleaned = 0
        total_records_removed = 0
        backup_files = []

        for current_cca3 in cca3_to_process:
            logging.info(f"--- Procesando pipeline para CCA3: {current_cca3} ---")
            query_extract = f"SELECT * FROM weather_raw_data WHERE cca3 = '{current_cca3}' ORDER BY timestamp DESC LIMIT 1"
            df_raw = pd.read_sql(query_extract, conn)
            
            if df_raw.empty:
                logging.info(f"Pipeline: No hay datos crudos recientes para {current_cca3} para procesar.")
                continue

            records_read = len(df_raw)
            total_records_read += records_read
            logging.info(f"Pipeline: Extraídos {records_read} registros crudos para {current_cca3}.")
            df_clean = df_raw.dropna(subset=["temperature", "windspeed"])
            df_clean = df_clean[df_clean["temperature"].between(-50, 60)] 
            records_cleaned = len(df_clean)
            records_removed = records_read - records_cleaned
            total_records_cleaned += records_cleaned
            total_records_removed += records_removed
            logging.info(f"Pipeline: Transformados datos para {current_cca3}. Eliminados: {records_removed}, Quedan: {records_cleaned}")

            if not df_clean.empty:
                for index, row in df_clean.iterrows():
                    insert_or_update_query = """
                        INSERT INTO weather_cleaned_data (cca3, city, temperature, windspeed, time)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            city = VALUES(city),
                            temperature = VALUES(temperature),
                            windspeed = VALUES(windspeed),
                            time = VALUES(time),
                            last_updated = CURRENT_TIMESTAMP
                    """
                    cursor.execute(insert_or_update_query, (
                        row['cca3'],
                        row['city'],
                        row['temperature'],
                        row['windspeed'],
                        row['time']
                    ))
                conn.commit()
                logging.info(f"Pipeline: Datos limpios para {current_cca3} cargados/actualizados en 'weather_cleaned_data'.")
            else:
                logging.warning(f"Pipeline: No hay datos limpios para cargar para {current_cca3} después de la transformación.")

            backup_dir = os.path.join(BASE_PIPELINE_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"backup_raw_weather_{current_cca3}_{timestamp}.csv")
            df_raw.to_csv(backup_file, index=False)
            backup_files.append(backup_file)
            logging.info(f"Pipeline: Backup de datos crudos para {current_cca3} guardado en {backup_file}")
        
        logging.info("--- Resumen de la Ejecución del Pipeline ---")
        logging.info(f"Total registros leídos: {total_records_read}")
        logging.info(f"Total registros limpiados/eliminados: {total_records_removed}")
        logging.info(f"Total registros cargados (limpios): {total_records_cleaned}")
        logging.info(f"Rutas de backups CSV: {', '.join(backup_files) if backup_files else 'Ninguno'}")

        cursor.close()

    except mysql.connector.Error as err:
        logging.error(f"Pipeline Error de MySQL: {err}", exc_info=True)
    except Exception as e:
        logging.error(f"Pipeline Error inesperado: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
