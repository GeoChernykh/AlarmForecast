# Ukraine Alert Forecast

A machine learning system that forecasts air raid alert probabilities across all Ukrainian regions for the next 24 hours. Predictions are served via a REST API and visualized on an interactive map updated regularly.

**Live:** [Deployed on Vercel and AWS EC2]

---

## Overview

The system collects data from multiple sources, merges it, engineers features, and generates predictions using a LightGBM model. The frontend displays the forecast as a heatmap over a Ukraine map with hourly resolution. Predictions are updated every 30 minutes via cron job.

---

## ⚠️ Data Collection Notice

The historical dataset required to train the model is **not included** in this repository and is non-trivial to reconstruct:

- **Alarm data** — requires running the historical scraper from scratch
- **ISW** — requires downloading and processing ISW reports
- **Telegram** — requires an active Telegram account, API credentials, and time to collect history
- **Weather** — relatively straightforward via the provided scripts

Full historical backfill can take significant time and disk space. The pipeline assumes this data already exists.

**This repo is primarily a reference implementation.**

---

## Architecture

### Backend (AWS EC2)
- Cron job runs lgbm_predict.py every 30 minutes to generate fresh predictions
- Flask app serves the `/forecast` endpoint, reading predictions from `data/predictions/alarm_predictions.json`

### Frontend (Vercel)
- Next.js app
- Fetches data from backend API with API key authentication

### Prediction Pipeline

Predictions are generated every 30 minutes via cron:
- Run `python model_scripts/lgbm_predict.py` to generate new predictions

---

## API

The backend exposes a simple REST API for retrieving the latest forecast.

### Endpoints

#### `GET /forecast`
> Returns the full 24-hour forecast for all regions.

### Authentication

All requests require an API key:

```http
x-api-key: <ALARM_API_KEY>
```

---

## Data

| Type | Description |
|------|-------------|
| **Alarms** | Historical air raid alert records per region |
| **Weather** | Weather forecast data per region |
| **Telegram** | Telegram channel monitoring |
| **ISW** | Institute for the Study of War reports |
| **Merged** | Combined dataset for modeling |

---

## Model

- **Algorithm:** LightGBM
- **Task:** Forecasting alert probabilities per region per hour
- **Features:** Engineered from alarm history, weather, NLP signals, temporal features
- **Retraining:** Manual or as needed
- **Inference:** Runs every 30 minutes

---

## Frontend

Built with **Next.js**, deployed on **Vercel**.

- Interactive choropleth map colored by alert probability
- 24-hour forecast visualization
- Per-region details

---

## Repository Structure

```
DS_lab/
├── alarm_forecast.py          # Flask API server
├── app/                       # Backend modules
│   ├── errors.py              # Error handling
│   └── core/
│       ├── features/          # Feature engineering
│       │   ├── alarms_features.py
│       │   ├── isw_features.py
│       │   ├── merge_data.py
│       │   ├── telegram_features.py
│       │   └── weather_features.py
│       ├── model_scripts/     # Model training and prediction
│       │   ├── lgbm_predict.py
│       │   └── lgbm_retrain.py
│       └── scraping/          # Data collection scripts
│           ├── alarm.py
│           ├── scraper_isw.py
│           ├── telegram_parser.py
│           └── weather_forecast.py
├── db/                        # Database modules
├── models/                    # Model artifacts
├── data/                      # Data files
├── eda/                       # Exploratory data analysis notebooks
├── frontend/
│   └── tactical-map/          # Next.js frontend
├── keys/                      # API keys and credentials
├── machine learning/          # ML experiments
├── requirements.txt           # Python dependencies
└── README.md
```

---

## Setup & Deployment

### 1. Clone & Environment

```bash
git clone <your-repo-url>
cd DS_lab
python -m venv .venv
.venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

Copy and configure environment variables:

```bash
cp .env.example .env  # If exists, or create .env
# Fill in credentials
```

---

### 2. API Keys & Credentials

#### Telegram API
For Telegram data collection:

```env
TG_API_ID=your-telegram-api-id
API_HASH=your-telegram-api-hash
```

#### Weather API
```env
WEATHER_API_KEY=your-weather-api-key
```

#### Alarm API
```env
ALARM_API_KEY=your-alarm-api-key
```

---

### 3. Backend (AWS EC2)

#### Install dependencies

```bash
sudo apt update
sudo apt install python3 python3-pip
pip install -r requirements.txt
```

#### Set up cron for predictions

Edit crontab:

```bash
crontab -e
```

Add line to run every 30 minutes:

```
*/30 * * * * cd /path/to/DS_lab && .venv/bin/python model_scripts/lgbm_predict.py
```

#### Run Flask app

```bash
python alarm_forecast.py
```

For production, use Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 alarm_forecast:app
```

---

### 4. Frontend (Vercel)

```bash
cd frontend/tactical-map
npm install
npm run dev  # Local development
npm run build  # Production build
```

Deploy by connecting the repo to Vercel. Set environment variables:

- `API_BASE_URL`: EC2 instance URL (e.g., `http://your-ec2-ip:5000`)
- `API_KEY`: Must match `ALARM_API_KEY` on backend

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ALARM_API_KEY` | API key for backend authentication |
| `WEATHER_API_KEY` | Weather API key |
| `TG_API_ID` | Telegram API ID |
| `API_HASH` | Telegram API hash |

---

## Credits & Sources

- Alerts data from alerts.in.ua
- Weather data from Open-Meteo
- ISW reports
- Telegram channels
- LightGBM for modeling

---

## License

This is a learning/research project.