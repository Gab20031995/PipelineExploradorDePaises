![LOGO ULEAD](https://github.com/user-attachments/assets/6f54a45a-9049-4952-8bd9-ffe2d4983bf3)

# **2025- II Programación Web**
# **Entregable grupal #4**

## Profesor: Alejandro Zamora Esquivel

Alumnos:
- Gabriel Corrales Mora.
- Jeralin Mayerlin Flores Hernández.
- Jean Rabbat Sánchez.

# 🌎 Explorador de Países

**DEMO:**

Un proyecto de aplicación web full-stack que permite a los usuarios explorar, buscar y guardar información sobre países de todo el mundo. La aplicación consume datos de la API pública [REST Countries](https://restcountries.com/) y utiliza una base de datos propia para gestionar la lista de países favoritos de cada usuario. **Además, ahora podrás consultar el clima actual en tiempo real de cada país, con datos actualizados y procesados por un robusto pipeline de datos.**

## Características

* **Exploración Global:** Visualiza una lista completa de países con sus banderas.
* **Búsqueda Dinámica:** Busca países específicos por su nombre.
* **Filtros Avanzados:** Filtra la lista de países por región (África, América, Asia, etc.) y subregión (Norteamérica, Caribe, etc.).
* **Detalles del País:** Haz clic en un país para ver información detallada como su capital, población, moneda e idioma principal.
* **Información Meteorológica en Tiempo Real:** Consulta la temperatura, velocidad del viento y hora de la última medición para cada país. Los datos se actualizan automáticamente cada minuto y pueden ser forzados con un botón de "Consultar Clima" en el modal de detalles. Se incluye un indicador visual de carga (spinner) mientras se obtienen los datos.
* **Pipeline de Datos Integrado (ETL):** Un sistema ETL (Extracción, Transformación, Carga) automatizado se encarga de procesar los datos meteorológicos crudos obtenidos de la [Open-Meteo API](https://open-meteo.com/). Este pipeline limpia, valida y almacena los datos de forma optimizada en una tabla separada, además de generar backups y logs de calidad.
* **Gestión de Favoritos:** Guarda tus países preferidos en una lista personalizada y elimínalos cuando quieras.
* **Modales Personalizados:** Los mensajes de confirmación y alerta ahora se muestran en modales personalizados para una mejor experiencia de usuario.
* **Interfaz Limpia y Responsiva:** Diseño moderno y adaptable a diferentes tamaños de pantalla.

## Tecnologías Utilizadas

Este proyecto está construido con las siguientes tecnologías:

### Frontend
* **HTML:** Para la estructura semántica de la aplicación.
* **CSS:** Para el diseño y la apariencia visual, incluyendo animaciones para el spinner y modales.
* **JavaScript (ES6+):** Para la interactividad, la manipulación del DOM y la comunicación con el backend.

### Backend
* **Python:** Como lenguaje de programación del servidor.
* **FastAPI:** Un framework web moderno y de alto rendimiento para construir APIs con Python.
* **Uvicorn:** Como servidor ASGI para correr la aplicación FastAPI.
* **httpx:** Cliente HTTP asíncrono para realizar peticiones a APIs externas (REST Countries, Open-Meteo).

### Base de Datos
* **MySQL:** Para almacenar la lista de países guardados por el usuario, así como los datos meteorológicos crudos y limpios.
* **mysql-connector-python:** Conector de Python para interactuar con MySQL.

### Pipeline de Datos (ETL)
* **Python Scripting:** Implementado como un script Python puro (`pipeline/flow.py`) para las etapas de Extracción, Transformación y Carga (ETL) de los datos meteorológicos.
* **Pandas:** Utilizado para la manipulación y limpieza eficiente de los datos dentro del pipeline.

## Instalación y Puesta en Marcha

Para ejecutar este proyecto en tu máquina local, sigue estos pasos:

### Prerrequisitos

Asegúrate de tener instalado:
* **Python 3.8 o superior**
* **pip** (el gestor de paquetes de Python)
* Un servidor de **MySQL** en ejecución

### 1. Configuración del Backend

Primero, clona el repositorio y configura el servidor de Python.

```bash
# 1. Clona el repositorio si lo tienes en Git
git clone https://github.com/Gab20031995/PipelineExploradorDePaises.git
cd <NOMBRE_DE_LA_CARPETA>

# 2. Crea y activa un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # En Windows usa: venv\Scripts\activate

# 3. Instala todas las dependencias de Python desde el archivo requirements.txt
pip install -r requirements.txt

4. Configura las Variables de Entorno de la Base de Datos
Importante: Para la seguridad y flexibilidad, las credenciales de la base de datos se leen de variables de entorno, no están codificadas en el código. Debes configurarlas en tu terminal antes de iniciar el servidor.

En Linux / macOS:

export DB_HOST="127.0.0.1"
export DB_PORT="3307" # Asegúrate de que este sea el puerto correcto de tu MySQL
export DB_USER="root"
export DB_PASSWORD="tu_contraseña_mysql"
export DB_NAME="countries_db"

En Windows (PowerShell):

$env:DB_HOST="127.0.0.1"
$env:DB_PORT="3307"
$env:DB_USER="root"
$env:DB_PASSWORD="tu_contraseña_mysql"
$env:DB_NAME="countries_db"

(Si cierras la terminal, estas variables se perderán. Para una solución más persistente en desarrollo, puedes investigar el uso de la librería python-dotenv.)

5. Inicia el servidor Backend
uvicorn main:app --reload

El backend ahora estará corriendo en http://127.0.0.1:8000. La aplicación creará automáticamente la base de datos countries_db (si no existe) y las tablas saved_countries, weather_raw_data, y weather_cleaned_data al iniciar.

6. Disparo Manual del Pipeline (Opcional)
Puedes forzar la ejecución del pipeline de clima para todos los países con datos crudos o guardados enviando una petición POST a este endpoint:

curl -X POST [http://127.0.0.1:8000/api/pipeline/run-weather-etl](http://127.0.0.1:8000/api/pipeline/run-weather-etl)

2. Iniciar el Frontend
Simplemente abre el archivo index.html en tu navegador web preferido. El JavaScript está configurado para comunicarse con el servidor local que acabas de iniciar.

Estructura del Proyecto
├── index.html          # Archivo principal de la interfaz
├── style.css           # Hoja de estilos
├── script.js           # Lógica del frontend y llamadas a la API
├── main.py             # Servidor backend con FastAPI y lógica de negocio
├── pipeline/           # Contiene el script del pipeline de datos
│   └── flow.py         # Lógica de Extracción, Transformación y Carga (ETL) para el clima
├── requirements.txt    # Lista de dependencias de Python
└── README.md           # Este archivo
