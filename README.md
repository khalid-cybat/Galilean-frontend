# SPHEREx Frontend

A Flask website for exploring the SPHEREx mission, its orbit, FITS observations, and candidate detections.

## Requirements

- Python 3
- The separate SPHEREx analysis API for live telemetry, FITS images, and candidate data

The API is not included in this repository. By default, the interactive pages expect it at `http://127.0.0.1:8000`.

## Install

From the project directory, create and activate a virtual environment, then install the Python packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` to activate the environment after creating it with `py -m venv .venv`.

## Configure and run

Set the API address in `.env` (copy `.env.example` if needed). Flask proxies browser API requests through the frontend origin, so the API does not need to enable cross-origin browser access. For example:

```bash
cp .env.example .env
# Set SPHEREX_API_URL=http://127.0.0.1:8000 in .env
```

Start the analysis API separately, if you want the explorer, tracker, and FITS viewer to load live data. Then, from the activated virtual environment, run:

```bash
python app.py
```

Open <http://127.0.0.1:5000>. The app loads settings from `.env` and also accepts environment variables. Set `SPHEREX_API_URL` to the API's base URL; a URL ending in `/api` is also accepted and normalized automatically. When it is not set, the frontend defaults to the API on port `8000` when served on ports `5000`, `5001`, or `5050`.

The home page works without the API. The Data Explorer, Live Tracker, and FITS Viewer need it for their live data and will show errors or empty data when it is unavailable. The 3D view and fonts also load external resources, so they may be limited without internet access.

## Optional geography files

The tracker can serve local GeoJSON files from a `geography` directory under `data` by default. To use a different data directory, set `SPHEREX_DATA_DIR` to the directory containing `geography` before starting the app. The supported files are `ne_50m_admin_0_countries.geojson` and `ne_50m_geography_marine_polys.geojson`.

## Routes

- `/` - mission home page
- `/explorer` - observation and candidate explorer
- `/tracker` - orbital tracker
- `/fits` - FITS viewer

## Troubleshooting

- **`ModuleNotFoundError` for Flask:** activate `.venv` and run `python -m pip install -r requirements.txt`.
- **API connection errors:** confirm the analysis API is running and that `SPHEREX_API_URL` points to it.
- **Port 5000 is already in use:** stop the process using it, or start Flask on another port, for example `python -c "import app; app.app.run(host='0.0.0.0', port=5050)"`. The automatic API fallback includes port `5050`; for other ports, set `SPHEREX_API_URL` explicitly.