# SPHEREx Frontend

A React/Vite route host for the original Flask-rendered SPHEREx pages. The original page markup, styles, and interactions remain the visual source of truth; Flask also proxies the analysis API.

## Requirements

- Python 3
- Node.js and npm
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

Install the JavaScript packages from the project directory:

```bash
npm install
```

## Configure and run

Set the API address in `.env` (copy `.env.example` if needed). Flask proxies browser API requests through the frontend origin, so the API does not need to enable cross-origin browser access. For example:

```bash
cp .env.example .env
# Set SPHEREX_API_URL=http://127.0.0.1:8000 in .env
```

Start the analysis API separately, if you want the explorer, tracker, and FITS viewer to load live data. Start Flask in one terminal:

```bash
source .venv/bin/activate
python -c "import app; app.app.run(host='0.0.0.0', port=5050)"
```

In a second terminal, start the React development server:

```bash
npm run dev
```

Open the Vite URL printed in the terminal, usually <http://localhost:5173>. Vite forwards `/api` and `/geography` requests to Flask on port `5050`; Flask forwards API calls to the configured analysis API. The app loads settings from `.env` and also accepts environment variables. Set `SPHEREX_API_URL` to the API's base URL; a URL ending in `/api` is also accepted and normalized automatically.

For a production-style Flask run, build React and start Flask:

```bash
npm run build
python app.py
```

Flask then serves the built React app and its static assets.

The home page works without the analysis API. The Data Explorer, Live Tracker, and FITS Viewer need it for live data. The 3D view and fonts also load external resources, so they may be limited without internet access.

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
- **Port 5050 is already in use:** stop the process using it, or update the target in `vite.config.js` to match the port used by Flask.