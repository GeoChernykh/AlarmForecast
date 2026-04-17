# README


## Project Overview

The Air Raid Alarm Prediction System is a full-stack machine learning application designed to forecast Ukraine air raid alerts for the next 24 hours. It combines historical alarm records, weather forecasts, Telegram channel signals, and ISW reports to produce region-level alert probability forecasts.

This repository contains the production backend, preprocessing and modeling code, saved model artifacts, and a Next.js frontend for interactive visualization.

---

## System Architecture

### Layers
- **Data Ingestion and Persistence:** `app/core/scraping/` and `db/` store raw and merged data into `app/db/database.db`.
- **Feature Engineering:** `app/core/features/` contains alarm, weather, Telegram, ISW, and merge logic.
- **Model Training and Inference:** `app/core/model_scripts/` includes `lgbm_retrain.py` and `lgbm_predict.py`.
- **Production Backend:** `app/api/alarm_forecast.py` exposes a Flask REST API.
- **Frontend Presentation:** `frontend/tactical-map/` is a Next.js application that renders geospatial forecasts using Ukraine region boundary data.

### Production Components
- **Backend:** Flask app served with uWSGI on AWS EC2
- **Model:** Serialized LightGBM pipeline at `models/lgbm_pipeline.joblib`
- **Inference Output:** JSON predictions stored in `data/predictions/alarm_predictions.json`
- **Frontend:** Next.js tactical map application in `frontend/tactical-map/`

---

## Deployment Process

The system was deployed to AWS EC2 with the following phases:

1. **Infrastructure provisioning**
   - Provisioned an EC2 instance for the backend and frontend.
   - Configured security groups to allow HTTP/HTTPS and protected SSH.
   - Used the SSH key for secure access.

2. **Environment configuration**
   - Installed Python 3.13.8, Node.js, and npm on the EC2 instance.
   - Cloned the repository to the server.

3. **Backend deployment**
   - Created a Python virtual environment and installed backend dependencies.
   - Configured uWSGI to run the Flask app at `app/api/alarm_forecast.py`.
   - Used uWSGI as the WSGI bridge for concurrent inference requests.

4. **Frontend deployment**
   - Installed frontend packages in `frontend/tactical-map/`.
   - Built the Next.js application for production.
   - Started the frontend with `npm start`.

5. **Process management**
   - Used PM2 to keep the backend and frontend processes running after logout.

Recommended to use different instances for frontend and backend

---

## Data Flow Pipeline

1. **Data ingestion**
   - Scraping modules collect raw data from Telegram, ISW reports, weather APIs, and alarm feeds.

2. **Persistence**
   - The `db/` layer stores historical and merged data in the SQLite database.

3. **Feature engineering**
   - The system builds spatial and temporal features, including neighbor-region alarm status and weather-related features.

4. **Preprocessing**
   - Serialized preprocessing artifacts are loaded from `models/preprocessing/`.
   - Categorical encoding, scaling, and time-based transformations are applied.

5. **Inference**
   - `app/core/model_scripts/lgbm_predict.py` loads the model and computes hourly alert probabilities.

6. **API serving**
   - The Flask API returns the forecast JSON to clients.

7. **Frontend rendering**
   - The Next.js app consumes API data and shows alerts on a geographic map.

---

## Architectural Evolution

### Changes since H/W #2
- **Non-linear production model:** moved from baseline linear/logistic regression to a serialized LightGBM pipeline.
- **Decoupled pipeline:** separated experimental notebooks in `machine learning/` from production code in `app/` and `models/`.
- **Frontend integration:** added a dedicated Next.js layer for map-based visualization instead of static analysis outputs.

---

## Challenges and Lessons Learned

### What went wrong compared to the original plan
- **Data merging complexity:** aligning asynchronous sources such as ISW, weather forecasts, and alarm timestamps required more careful timestamp handling than initially planned.
- **High-dimensional NLP feature processing:** combining sparse text features from Telegram/ISW with tabular data increased dataset complexity and made simple models inadequate.
- **Forecast input constraints:** delivering live spatial/temporal features for continuous deployment required a stronger inference engine and more robust preprocessing than the original design assumed.

---

## Automation and Scheduling

### Prediction automation
- Generates new forecasts every 30 minutes using live data and the LightGBM inference engine.
- Example cron job:
  ```bash
  */30 * * * * /home/ubuntu/AlarmForecast/.venv/bin/python3 -m app.core.model_scripts.lgbm_predict
  ```

### Retraining automation
- Retrains the model weekly to prevent drift.
- Example cron job:
  ```bash
  0 3 * * 1 /home/ubuntu/AlarmForecast/.venv/bin/python3 -m app.core.model_scripts.lgbm_retrain
  ```

---

## Repository Structure

```
app/
  api/alarm_forecast.py
  core/
    features/
    model_scripts/
    scraping/
  errors.py
  db/
models/
  lgbm_pipeline.joblib
  preprocessing/
data/
  predictions/alarm_predictions.json
eda/
frontend/tactical-map/
keys/
machine learning/
README.md
requirements.txt
```

---

## Local Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/GeoChernykh/AlarmForecast.git
   cd AlarmPrediction
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install frontend dependencies:
   ```bash
   cd frontend/tactical-map
   npm install
   ```

5. Run the backend:
   ```bash
   cd ../../
   python app/api/alarm_forecast.py
   ```

6. Build and run the frontend:
   ```bash
   cd frontend/tactical-map
   npm run build
   npm start
   ```

---