# README


## Project Overview

The Air Raid Alarm Prediction System is a full-stack machine learning application designed to forecast Ukraine air raid alerts for the next 24 hours. It combines historical alarm records, weather forecasts, Telegram channel signals, and ISW reports to produce region-level alert probability forecasts.

This repository contains the production backend, preprocessing and modeling code, saved model artifacts, and a Next.js frontend for interactive visualization.

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

## System Architecture

### Layers
- **Data Ingestion and Persistence:** `app/core/scraping/` and `db/` store raw and merged data into `app/db/database.db`.
- **Feature Engineering:** `app/core/features/` contains preprocessing functions for alarm, weather, Telegram, ISW data and merging logic.
- **Model Training and Inference:** `app/core/model_scripts/` includes `lgbm_retrain.py` and `lgbm_predict.py` scripts.
- **Production Backend:** `app/api/alarm_forecast.py` exposes a Flask REST API.
- **Frontend Presentation:** `frontend/tactical-map/` is a Next.js application that renders geospatial forecasts using Ukraine region boundary data.

### Production Components
- **Backend:** Flask app served with uWSGI on AWS EC2
- **Model:** Serialized LightGBM pipeline at `models/lgbm_pipeline.joblib`
- **Inference Output:** JSON predictions stored in `data/predictions/alarm_predictions.json`
- **Frontend:** Next.js tactical map application in `frontend/tactical-map/`

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

## Automation and Scheduling

### Prediction automation
- Generates new forecasts hourly using live data and the LightGBM inference engine.
- Example cron job:
  ```bash
  0 * * * * /home/ubuntu/AlarmForecast/.venv/bin/python3 -m app.core.model_scripts.lgbm_predict
  ```

### Retraining automation
- Retrains the model weekly to prevent drift.
- Example cron job:
  ```bash
  0 3 * * 1 /home/ubuntu/AlarmForecast/.venv/bin/python3 -m app.core.model_scripts.lgbm_retrain
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

## Production Setup

This guide covers deploying the AlarmForecast application on AWS EC2 instances. We deploy the backend and frontend on separate instances for better scalability and maintainability.

### Prerequisites
- AWS account with EC2 access
- Git access to the repository
- Environment file (.env) with required credentials
- Required data files (regions_list.json, regions.csv, database.db)

---

### Backend Setup on EC2

#### 1. Launch EC2 Instance
- Instance type: c7i-flex.large
- Storage: 30 GB
- Security group: Allow inbound traffic on port 8000 from anywhere

#### 2. System Dependencies and Environment Setup

Connect to your instance via SSH and run:

```bash
sudo apt update -y
sudo apt-get upgrade -y
sudo apt-get dist-upgrade -y
sudo apt-get install -y make build-essential zlib1g-dev libffi-dev libssl-dev \
  libbz2-dev libreadline-dev libsqlite3-dev liblzma-dev libncurses-dev tk-dev
```

#### 3. Install Python 3.13.8 using pyenv

```bash
curl https://pyenv.run | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
exec "$SHELL"

pyenv install 3.13.8
pyenv global 3.13.8
```

#### 4. Clone Repository and Install Dependencies

```bash
git clone https://github.com/GeoChernykh/AlarmForecast.git
cd AlarmForecast/
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

#### 5. Upload Required Files

Upload the following files to the EC2 instance:
- `.env` file → `~/AlarmForecast/`
- `regions.csv` → `~/AlarmForecast/data/alarms/`
- `regions_list.json` → `~/AlarmForecast/data/alarms/`
- `database.db` → `~/AlarmForecast/app/db/`

#### 6. Configure uWSGI

Create uWSGI configuration file:

```bash
nano ~/AlarmForecast/uwsgi.ini
```

Paste the following configuration:

```ini
[uwsgi]
chdir = /home/ubuntu/AlarmForecast
module = main:app
virtualenv = /home/ubuntu/AlarmForecast/.venv
master = true
processes = 2
threads = 2
http = 0.0.0.0:8000
pidfile = /tmp/myapp.pid
```

#### 7. Create Systemd Service

Create the systemd service file:

```bash
sudo nano /etc/systemd/system/alarmforecast.service
```

Paste the following configuration:

```ini
[Unit]
Description=AlarmForecast Flask App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/AlarmForecast
ExecStart=/home/ubuntu/AlarmForecast/.venv/bin/uwsgi --ini /home/ubuntu/AlarmForecast/uwsgi.ini
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 8. Start and Enable the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable alarmforecast
sudo systemctl start alarmforecast
```

#### 9. Configure Cron Jobs for Automated Tasks

Edit the crontab:

```bash
crontab -e
```

Add the following cron jobs (predictions hourly, retraining weekly on Mondays):

```bash
0 * * * * cd /home/ubuntu/AlarmForecast && .venv/bin/python -m app.core.model_scripts.lgbm_predict >> /home/ubuntu/AlarmForecast/cron.log 2>&1
30 * * * * cd /home/ubuntu/AlarmForecast && .venv/bin/python -m app.core.model_scripts.lgbm_predict >> /home/ubuntu/AlarmForecast/cron.log 2>&1
0 3 * * 1 cd /home/ubuntu/AlarmForecast && .venv/bin/python -m app.core.model_scripts.lgbm_retrain >> /home/ubuntu/AlarmForecast/cron.log 2>&1
```

#### 10. Test the Backend

Open a browser and navigate to:
```
http://<server-public-ipv4>:8000/forecast
```

---

### Frontend Setup on EC2

#### 1. Launch EC2 Instance
- Instance type: t3.small
- Storage: 15 GB
- Security group: Allow inbound traffic on port 3000 from anywhere

#### 2. System Dependencies and Environment Setup

Connect to your instance via SSH and run:

```bash
sudo apt update -y
sudo apt-get upgrade -y
sudo apt-get dist-upgrade -y
sudo apt-get install -y make build-essential zlib1g-dev libffi-dev libssl-dev \
  libbz2-dev libreadline-dev libsqlite3-dev liblzma-dev libncurses-dev tk-dev
```

#### 3. Install Python 3.13.8 using pyenv

```bash
curl https://pyenv.run | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
exec "$SHELL"

pyenv install 3.13.8
pyenv global 3.13.8
```

#### 4. Clone Repository with Sparse Checkout (Frontend Only)

```bash
git clone --depth=1 --no-checkout --filter=blob:none https://github.com/GeoChernykh/AlarmForecast.git
cd AlarmForecast
git sparse-checkout set frontend
git checkout main
```

#### 5. Install Frontend Dependencies

```bash
cd frontend/tactical-map
npm install --legacy-peer-deps
npm run build
```

#### 6. Install PM2 for Process Management

```bash
sudo npm install -g pm2
```

#### 7. Start the Application with PM2

```bash
pm2 start npm --name "tactical-map" -- start
```

Verify it's running:
```bash
curl http://localhost:3000
```

#### 8. Configure PM2 for Startup

```bash
pm2 save
pm2 startup
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu
```

#### 9. Test the Frontend

Open a browser and navigate to:
```
http://<server-public-ipv4>:3000
```

---

