# Ukraine Alert Forecast

This project is a machine learning-powered system designed to predict air raid alert probabilities across Ukrainian regions for the upcoming 24 hours. It leverages data from various sources to train a model and provide forecasts via a REST API, with an interactive map for visualization.

**Live Demo:** [ukraine-alert-forecast.vercel.app](https://ukraine-alert-forecast.vercel.app)

---

## Project Overview

The core idea is to automate the collection of relevant data, process it into meaningful features, and use a trained model to forecast potential alerts. The system runs a daily pipeline to update predictions, ensuring timely and accurate information.

Key components include:
- Data gathering from alarms, weather, Telegram, and ISW sources
- Feature engineering and model retraining
- Prediction generation and API serving
- A user-friendly frontend for viewing forecasts

---

## Important Note on Data

Please be aware that the historical datasets needed for training are not part of this repository due to their complexity and size. Reconstructing them involves:
- Scraping alarm data from historical APIs
- Processing ISW reports
- Collecting Telegram history with proper credentials
- Fetching weather data

This process can be time-consuming. The repository serves as a blueprint for the system, with the live version operating on a pre-built dataset.

---

## System Architecture

### Backend (Hosted on AWS EC2)
- Automated cron jobs handle the nightly data pipeline
- Data collection, merging, feature creation, and model updates occur sequentially
- Predictions are stored in S3 and served through a Flask API

### Frontend (Deployed on Vercel)
- Built using React and Next.js
- Displays forecasts on an interactive map
- Communicates with the backend via authenticated API calls

### Daily Update Schedule (UTC)

| Time | Task |
|------|------|
| 02:00 | Gather alarm data |
| 02:45 | Collect Telegram messages |
| 03:15 | Fetch weather forecasts |
| 03:30 | Retrieve ISW updates |
| 04:00 | Merge datasets |
| 04:15 | Engineer features |
| 04:30 | Retrain the model |
| 05:00 | Generate and upload predictions |

---

## API Reference

The backend provides a straightforward API for accessing forecasts.

### Endpoints

- `GET /latest`: Retrieves the complete 24-hour prediction for all regions
- `GET /health`: Checks the service status

### Security

Requests to the forecast endpoint need an API key in the header:
```
x-api-key: YOUR_API_KEY
```

---

## Data Sources

The model relies on diverse data types:
- **Alarms**: Past alert records by region
- **Weather**: Forecasted conditions
- **Telegram**: Messages from monitored channels
- **ISW**: War institute reports
- **Merged Data**: Combined inputs for training

---

## Machine Learning Model

- **Framework**: LightGBM for multi-output classification
- **Objective**: Predict alert probabilities hourly per region
- **Inputs**: Historical lags, weather metrics, text features, time-based variables
- **Performance** (averaged over retrains):
  - F1 Score: ~0.819
  - Precision: ~0.812
  - Recall: ~0.825
  - AUC-ROC: ~0.923
- **Update Frequency**: Daily retraining

---

## Frontend Application

Developed with React and Vite, hosted on Vercel.

Features include:
- Choropleth map showing alert risks
- Hourly forecast slider
- Detailed region views with charts
- Animation for time progression
- Daily updates at 06:00 UTC

---

## Project Structure

```
alarm_forecast.py                 # Main Flask server
app/
├── errors.py                     # Error management
└── core/
    ├── features/                 # Feature processing scripts
    │   ├── alarms_features.py
    │   ├── isw_features.py
    │   ├── merge_data.py
    │   ├── telegram_features.py
    │   └── weather_features.py
    ├── model_scripts/            # Training and prediction
    │   ├── lgbm_predict.py
    │   └── lgbm_retrain.py
    └── scraping/                 # Data scrapers
        ├── alarm.py
        ├── scraper_isw.py
        ├── telegram_parser.py
        └── weather_forecast.py
db/                               # Database handlers
models/                           # Saved models and preprocessors
data/                             # Datasets and predictions
eda/                              # Analysis notebooks
frontend/tactical-map/            # Next.js app
keys/                             # Credentials
machine learning/                 # Model experiments
requirements.txt                  # Dependencies
README.md                         # This file
```

---

## Installation and Setup

### Prerequisites
- Python 3.8+
- Node.js for frontend
- AWS account for deployment

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AlarmPrediction.git
   cd AlarmPrediction
   ```

2. Set up Python environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure environment variables (create `.env`):
   ```env
   ALARM_API_KEY=your-key
   WEATHER_API_KEY=your-key
   TG_API_ID=your-id
   API_HASH=your-hash
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   S3_BUCKET=your-bucket
   API_KEY=your-api-key
   ```

### API Credentials

- **Alerts.in.ua**: Obtain from their API page
- **Telegram**: Get API ID and hash from my.telegram.org
- **Weather**: Use Open-Meteo or similar
- **AWS S3**: Create bucket and IAM user with S3 permissions

### Backend Deployment (EC2)

1. Install system packages:
   ```bash
   sudo apt update
   sudo apt install python3-pip nginx
   ```

2. Set up the Flask service with systemd:
   - Create `/etc/systemd/system/flaskapp.service`
   - Configure Gunicorn to run the app

3. Configure Nginx as reverse proxy on port 80

4. Set up cron for daily pipeline

### Frontend Deployment (Vercel)

1. Navigate to frontend:
   ```bash
   cd frontend/tactical-map
   npm install
   npm run build
   ```

2. Connect to Vercel and set env vars:
   - `API_KEY`
   - `EC2_HOST`

---

## Acknowledgments

Data and inspiration from:
- alerts.in.ua for alert data
- Open-Meteo for weather
- Institute for the Study of War
- Various Telegram channels
- LightGBM documentation

---

## License

This project is for educational and research purposes. No datasets are included.