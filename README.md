# BCV Exchange Rate API

API RESTful para consulta y almacenamiento histórico de los tipos de cambio
oficiales del **Banco Central de Venezuela (BCV)**.

---

## Características

- **Scraper resiliente** con fallback multi-selector (sobrevive cambios menores en el HTML del BCV).
- **Persistencia JSON** con upsert diario (no duplica registros).
- **Dashboard web** con botón de actualización en tiempo real.
- **API REST** documentada con Swagger/OpenAPI.

---

## Requisitos

- Python **3.10+**
- pip

---

## Instalación

```bash
# 1. Clonar / descomprimir el proyecto
cd bcv-exchange-api

# 2. Crear entorno virtual (recomendado)
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Ejecución

```bash
uvicorn app.main:app --reload
```

La aplicación estará disponible en **http://127.0.0.1:8000**.

| URL                              | Descripción                                  |
|----------------------------------|----------------------------------------------|
| `GET /`                          | Dashboard web                                |
| `POST /api/v1/rates/refresh`     | Scrape BCV y guarda resultado                |
| `GET /api/v1/rates/latest`       | Último registro almacenado                   |
| `GET /api/v1/rates/history`      | Historial completo                           |
| `GET /api/v1/rates/{YYYY-MM-DD}` | Registro de una fecha específica             |
| `GET /docs`                      | Documentación Swagger                        |

---

## Estructura del proyecto

```
bcv-exchange-api/
├── app/
│   ├── main.py          # Punto de entrada FastAPI
│   ├── config.py        # Configuración global y selectores CSS
│   ├── models.py        # Modelos Pydantic
│   ├── services/
│   │   ├── scraper.py   # Lógica de scraping con fallback
│   │   └── storage.py   # Lectura / escritura del JSON
│   ├── routers/
│   │   ├── api.py       # Endpoints REST
│   │   └── web.py       # Dashboard HTML
│   └── templates/
│       └── dashboard.html
├── data/
│   └── exchange_rates.json   # Base de datos JSON (auto-creado)
├── requirements.txt
└── README.md
```

---

## Adaptación a cambios en el HTML del BCV

Los selectores están centralizados en `app/config.py` → `CURRENCY_SELECTORS`.
Si el BCV cambia su HTML, simplemente añada una nueva entrada al array de la
divisa afectada; el scraper intentará cada estrategia en orden.

```python
"USD": [
    {"method": "id",   "params": {"id": "dolar"}},          # selector actual
    {"method": "css",  "params": {"selector": "#nuevo .val"}}, # nuevo fallback
    {"method": "text", "params": {"label": "USD"}},          # último recurso
],
```

---

## Variables de configuración principales (`config.py`)

| Variable          | Valor por defecto             | Descripción                    |
|-------------------|-------------------------------|--------------------------------|
| `BCV_URL`         | `https://www.bcv.org.ve/`     | URL del sitio BCV              |
| `REQUEST_TIMEOUT` | `15`                          | Timeout de red (segundos)      |
| `HISTORY_LIMIT`   | `10`                          | Filas mostradas en dashboard   |
| `DB_FILE`         | `data/exchange_rates.json`    | Ruta de la base de datos       |

---

## Notas de producción

- Para múltiples workers (`--workers N`), reemplace el `threading.Lock` en
  `storage.py` por un lock a nivel de archivo (`fcntl` en Linux) o migre a
  SQLite/PostgreSQL.
- Considere ejecutar el refresh mediante un **cron job** o `APScheduler`
  para que las tasas se actualicen automáticamente cada día hábil.
