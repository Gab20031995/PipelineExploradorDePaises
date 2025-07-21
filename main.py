import os
import httpx
import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
PUBLIC_API_URL = "https://restcountries.com/v3.1"
DB_CONFIG = {
    'host': "127.0.0.1", 
    'port': "3307",
    'user': "root", 
    'password': "123Queso.",
    'database': "countries_db"
}

# BD 
def setup_database():
    try:
        db = mysql.connector.connect(host=DB_CONFIG['host'], port=DB_CONFIG['port'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
        cursor = db.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        print(f"Base de datos '{DB_CONFIG['database']}' verificada.")
        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        print(f"Error al configurar la base de datos: {err}")
        raise

def create_db_table():
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
        print("Tabla 'saved_countries' verificada con la nueva estructura.")
        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        print(f"Error al crear la tabla: {err}")
        raise

@app.on_event("startup")
def on_startup():
    setup_database()
    create_db_table()

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# Modelo Pydantic 
class CountrySave(BaseModel):
    cca3: str
    name: str
    region: str | None = None
    flag_url: str 

# Endpoints 
@app.get("/api/countries/all")
async def get_all_countries():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PUBLIC_API_URL}/all?fields=name,cca3,flags,region")
        r.raise_for_status()
        return r.json()

@app.get("/api/countries/by-name/{name}")
async def search_country_by_name(name: str):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{PUBLIC_API_URL}/name/{name}?fields=name,cca3,flags,region")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"No se encontraron países con el nombre '{name}'")
        else:
            raise HTTPException(status_code=e.response.status_code, detail="Error al contactar la API de países.")

@app.get("/api/countries/by-region/{region}")
async def search_country_by_region(region: str):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{PUBLIC_API_URL}/region/{region}?fields=name,cca3,flags,region")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"No se encontraron países en la región '{region}'")
        else:
            raise HTTPException(status_code=e.response.status_code, detail="Error al contactar la API de países.")

@app.get("/api/countries/by-subregion/{subregion}")
async def search_country_by_subregion(subregion: str):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{PUBLIC_API_URL}/subregion/{subregion}?fields=name,cca3,flags,region")
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"No se encontraron países en la subregión '{subregion}'")
        else:
            raise HTTPException(status_code=e.response.status_code, detail="Error al contactar la API de países.")

@app.get("/api/country/{code}")
async def get_country_details(code: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{PUBLIC_API_URL}/alpha/{code}?fields=name,capital,population,currencies,languages,flags,region,cca3")
        r.raise_for_status()
        return r.json()

@app.post("/api/save-country")
async def save_country(country: CountrySave):
    try:
        db = get_db()
        cursor = db.cursor()
        query = "INSERT IGNORE INTO saved_countries (cca3, name, region, flag_url) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (country.cca3, country.name, country.region, country.flag_url))
        db.commit()
        message = f"'{country.name}' guardado." if cursor.rowcount > 0 else f"'{country.name}' ya estaba guardado."
        cursor.close()
        db.close()
        return {"message": message}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")

@app.get("/api/saved-countries")
async def get_saved_countries():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT cca3, name, region, flag_url FROM saved_countries ORDER BY region, name")
        items = cursor.fetchall()
        cursor.close()
        db.close()
        return items
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")

@app.delete("/api/delete-country/{cca3}")
async def delete_country(cca3: str):
    try:
        db = get_db()
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
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err}")