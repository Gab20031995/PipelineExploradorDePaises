import os
import httpx
import mysql.connector
import logging
import json 
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime 
from pipeline.flow import run_weather_pipeline, get_all_cca3_with_raw_data

logger = logging.getLogger("uvicorn.error")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL de la API pública de países
PUBLIC_API_URL = "https://restcountries.com/v3.1"
# URL de la API de clima (Open-Meteo)
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

# Configuración de la base de datos MySQL
DB_CONFIG = {
    'host': os.getenv("DB_HOST", "127.0.0.1"),
    'port': int(os.getenv("DB_PORT", 3307)),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", "123Queso."),
    'database': os.getenv("DB_NAME", "countries_db")
}

# Definir un timeout global para las solicitudes HTTPX
DEFAULT_API_TIMEOUT = 10.0 # 10 segundos

# Funciones de Base de Datos
def setup_database():
    """Asegura que la base de datos exista."""
    try:
        db = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = db.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        logger.info(f"Base de datos '{DB_CONFIG['database']}' verificada/creada.")
        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        logger.error(f"Error al configurar la base de datos: {err}")
        raise

def create_db_tables():
    """Crea las tablas necesarias si no existen."""
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_countries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cca3 VARCHAR(3) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                region VARCHAR(100),
                flag_url VARCHAR(255) 
            )
        """)
        logger.info("Tabla 'saved_countries' verificada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_raw_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cca3 VARCHAR(3) NOT NULL,
                city VARCHAR(100),
                temperature FLOAT,
                windspeed FLOAT,
                time VARCHAR(50),
                raw_json JSON,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Tabla 'weather_raw_data' verificada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_cleaned_data (
                cca3 VARCHAR(3) PRIMARY KEY,
                city VARCHAR(100),
                temperature FLOAT,
                windspeed FLOAT,
                time VARCHAR(50),
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        logger.info("Tabla 'weather_cleaned_data' verificada.")

        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        logger.error(f"Error al crear las tablas: {err}")
        raise

@app.on_event("startup")
def on_startup():
    """Ejecuta la configuración de la base de datos al iniciar la aplicación."""
    setup_database()
    create_db_tables()

def get_db_connection():
    """Retorna una nueva conexión a la base de datos."""
    return mysql.connector.connect(**DB_CONFIG)

# Modelos 
class CountrySave(BaseModel):
    cca3: str
    name: str
    region: str | None = None
    flag_url: str 

# Endpoints de la API 

@app.get("/api/countries/all")
async def get_all_countries():
    """Obtiene todos los países de la API externa."""
    async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client: 
        r = await client.get(f"{PUBLIC_API_URL}/all?fields=name,cca3,flags,region")
        r.raise_for_status()
        return r.json()

@app.get("/api/countries/by-name/{name}")
async def search_country_by_name(name: str):
    """Busca países por nombre en la API externa."""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client:
            r = await client.get(f"{PUBLIC_API_URL}/name/{name}?fields=name,cca3,flags,region")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"No se encontraron países con el nombre '{name}'")
        else:
            logger.error(f"Error al buscar por nombre: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Error al contactar la API de países.")

@app.get("/api/countries/by-region/{region}")
async def search_country_by_region(region: str):
    """Busca países por región en la API externa."""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client: 
            r = await client.get(f"{PUBLIC_API_URL}/region/{region}?fields=name,cca3,flags,region")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"No se encontraron países en la región '{region}'")
        else:
            logger.error(f"Error al buscar por región: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Error al contactar la API de países.")

@app.get("/api/countries/by-subregion/{subregion}")
async def search_country_by_subregion(subregion: str):
    """Busca países por subregión en la API externa."""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client: 
            r = await client.get(f"{PUBLIC_API_URL}/subregion/{subregion}?fields=name,cca3,flags,region")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"No se encontraron países en la subregión '{subregion}'")
        else:
            logger.error(f"Error al buscar por subregión: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Error al contactar la API de países.")

@app.get("/api/country/{code}")
async def get_country_details(code: str):
    """Obtiene detalles completos de un país por su código CCA3."""
    async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client:
        r = await client.get(f"{PUBLIC_API_URL}/alpha/{code}?fields=name,capital,population,currencies,languages,flags,region,cca3,latlng")
        r.raise_for_status()
        return r.json()

@app.post("/api/save-country")
async def save_country(country: CountrySave):
    """Guarda un país en la base de datos local."""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        query = "INSERT IGNORE INTO saved_countries (cca3, name, region, flag_url) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (country.cca3, country.name, country.region, country.flag_url))
        db.commit()
        message = f"'{country.name}' guardado." if cursor.rowcount > 0 else f"'{country.name}' ya estaba guardado."
        cursor.close()
        db.close()
        return {"message": message}
    except mysql.connector.Error as err:
        logger.error(f"Error en la base de datos al guardar país: {err}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")

@app.get("/api/saved-countries")
async def get_saved_countries():
    """Obtiene la lista de países guardados de la base de datos local."""
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT cca3, name, region, flag_url FROM saved_countries ORDER BY region, name")
        items = cursor.fetchall()
        cursor.close()
        db.close()
        return items
    except mysql.connector.Error as err:
        logger.error(f"Error en la base de datos al obtener países guardados: {err}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")

@app.delete("/api/delete-country/{cca3}")
async def delete_country(cca3: str):
    """Elimina un país de la base de datos local."""
    try:
        db = get_db_connection()
        cursor = db.cursor()
        query = "DELETE FROM saved_countries WHERE cca3 = %s"
        cursor.execute(query, (cca3,))
        db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="País no encontrado en la lista de guardados.")
        cursor.close()
        db.close()
        return {"message": f"País con código '{cca3}' eliminado correctamente."}
    except mysql.connector.Error as err:
        logger.error(f"Error en la base de datos al eliminar país: {err}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")

@app.get("/api/weather/{cca3}")
async def get_weather_for_country(cca3: str, background_tasks: BackgroundTasks):
    """
    Obtiene datos de clima para un país, los guarda, y dispara el pipeline de limpieza
    en segundo plano. Retorna los datos limpios si existen, o un placeholder.
    """
    logger.info(f"Solicitud de clima para CCA3: {cca3}")
    country_details = None
    async with httpx.AsyncClient(timeout=DEFAULT_API_TIMEOUT) as client: 
        try:
            r_country = await client.get(f"{PUBLIC_API_URL}/alpha/{cca3}?fields=name,latlng")
            r_country.raise_for_status()
            country_details = r_country.json()
            
            if not country_details or 'latlng' not in country_details or len(country_details['latlng']) != 2:
                logger.warning(f"Coordenadas no encontradas para {cca3}. No se obtendrá el clima.")
                db = get_db_connection()
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    "SELECT city, temperature, windspeed, time, last_updated FROM weather_cleaned_data WHERE cca3 = %s",
                    (cca3,)
                )
                cleaned_data = cursor.fetchone()
                cursor.close()
                db.close()
                if cleaned_data:
                    return cleaned_data
                else:
                    return {"city": "N/A", "temperature": "N/A", "windspeed": "N/A", "time": "N/A", "last_updated": "N/A", "message": "Coordenadas no disponibles para obtener clima."}
            
            latitude, longitude = country_details['latlng']
            country_name = country_details['name']['common']
            resp_weather = await client.get(
                WEATHER_API_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current_weather": "true",
                    "timezone": "auto" 
                },
                timeout=DEFAULT_API_TIMEOUT 
            )
            resp_weather.raise_for_status()
            current_weather_data = resp_weather.json().get("current_weather", {})
            
            if not current_weather_data:
                logger.warning(f"No se encontraron datos de clima actuales para {country_name} ({cca3}).")
                db = get_db_connection()
                cursor = db.cursor(dictionary=True)
                cursor.execute(
                    "SELECT city, temperature, windspeed, time, last_updated FROM weather_cleaned_data WHERE cca3 = %s",
                    (cca3,)
                )
                cleaned_data = cursor.fetchone()
                cursor.close()
                db.close()
                if cleaned_data:
                    return cleaned_data
                else:
                    return {"city": country_name, "temperature": "N/A", "windspeed": "N/A", "time": "N/A", "last_updated": "N/A", "message": "No hay datos de clima disponibles."}

            db = get_db_connection()
            cursor = db.cursor()
            query = """
                INSERT INTO weather_raw_data (cca3, city, temperature, windspeed, time, raw_json)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                cca3,
                country_name, 
                current_weather_data.get("temperature"),
                current_weather_data.get("windspeed"),
                current_weather_data.get("time"),
                json.dumps(current_weather_data) 
            ))
            db.commit()
            cursor.close()
            db.close()
            logger.info(f"Datos crudos de clima insertados para {country_name} ({cca3}).")
            background_tasks.add_task(run_weather_pipeline, cca3, DB_CONFIG)
            logger.info(f"Pipeline de clima disparado en segundo plano para {cca3}.")

            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                "SELECT city, temperature, windspeed, time, last_updated FROM weather_cleaned_data WHERE cca3 = %s",
                (cca3,)
            )
            cleaned_data = cursor.fetchone()
            cursor.close()
            db.close()

            if cleaned_data:
                return cleaned_data
            else:
                return {
                    "city": country_name,
                    "temperature": current_weather_data.get("temperature"),
                    "windspeed": current_weather_data.get("windspeed"),
                    "time": current_weather_data.get("time"),
                    "last_updated": datetime.now().isoformat(),
                    "message": "Datos de clima en procesamiento (se actualizarán en breve)."
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP al obtener clima o detalles de país: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Error al contactar API externa: {e.response.text}")
        except httpx.ConnectTimeout as e:
            logger.error(f"Error de conexión (timeout) al obtener clima para {cca3}: {e}")
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                "SELECT city, temperature, windspeed, time, last_updated FROM weather_cleaned_data WHERE cca3 = %s",
                (cca3,)
            )
            cleaned_data = cursor.fetchone()
            cursor.close()
            db.close()
            if cleaned_data:
                return cleaned_data
            else:
                raise HTTPException(status_code=500, detail=f"Error de conexión al obtener clima para {cca3}. Inténtalo de nuevo. ({e})")
        except mysql.connector.Error as e:
            logger.error(f"Error de DB al procesar clima: {e}")
            raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
        except Exception as e:
            logger.error(f"Error inesperado al obtener clima: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error interno al obtener datos de clima: {e}")

@app.post("/api/pipeline/run-weather-etl")
async def run_weather_etl_manually(background_tasks: BackgroundTasks):
    """
    Endpoint para disparar el pipeline de clima manualmente para todos los países
    que tengan datos crudos o guardados.
    """
    logger.info("Solicitud de ejecución manual del pipeline de clima.")
    
    cca3_list = get_all_cca3_with_raw_data(DB_CONFIG) 
    
    if not cca3_list:
        return {"message": "No hay países con datos crudos o guardados para procesar."}

    for cca3 in cca3_list:
        background_tasks.add_task(run_weather_pipeline, cca3, DB_CONFIG)
        logger.info(f"Disparado pipeline para {cca3} en segundo plano (ejecución manual).")
    
    return {"message": f"Pipeline de clima disparado para {len(cca3_list)} países en segundo plano."}

@app.get("/api/weather/cleaned/{cca3}")
async def get_cleaned_weather_data(cca3: str):
    """
    Endpoint para leer exclusivamente los datos limpios de clima para un país.
    """
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT city, temperature, windspeed, time, last_updated FROM weather_cleaned_data WHERE cca3 = %s",
            (cca3,)
        )
        cleaned_data = cursor.fetchone()
        cursor.close()
        db.close()

        if not cleaned_data:
            raise HTTPException(status_code=404, detail=f"No hay datos de clima limpios para {cca3}.")
        
        return cleaned_data
    except mysql.connector.Error as err:
        logger.error(f"Error de DB al obtener datos limpios de clima: {err}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")
    except Exception as e:
        logger.error(f"Error inesperado al obtener datos limpios de clima: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno al obtener datos limpios de clima: {e}")
