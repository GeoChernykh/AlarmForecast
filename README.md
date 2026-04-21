# Alarm Forecasting Project

This project is a data science application for forecasting air raid alarms in Ukraine. It integrates multiple data sources including alarm data, Institute for the Study of War (ISW) reports, Telegram messages, and weather forecasts to predict alarm occurrences using machine learning models.

## Project Structure

```
alarm_forecast.py          # Main Flask application entry point
README.md                  # This file
requirements.txt           # Python dependencies
test.ipynb                 # Test notebook
app/                       # Flask application
├── errors.py              # Custom error handlers
└── core/
    ├── features/          # Feature engineering modules
    │   ├── alarms_features.py     # Alarm data feature extraction
    │   ├── isw_features.py        # ISW report feature extraction
    │   ├── merge_data.py          # Data merging utilities
    │   ├── telegram_features.py   # Telegram data feature extraction
    │   └── weather_features.py    # Weather data feature extraction
    ├── model_scripts/     # Machine learning scripts
    │   ├── lgbm_predict.py        # Prediction script using LightGBM
    │   └── lgbm_retrain.py        # Model retraining script
    └── scraping/           # Data scraping modules
        ├── alarm.py               # Alarm data scraper
        ├── scraper_isw.py         # ISW report scraper
        ├── telegram_parser.py     # Telegram data parser
        └── weather_forecast.py    # Weather data scraper
db/                        # Database modules
├── alarms_db.py           # Alarm data database handler
├── database.py            # Main database interface
├── isw_db.py              # ISW data database handler
├── telegram_db.py         # Telegram data database handler
└── weather_db.py          # Weather data database handler
models/                    # Trained machine learning models
├── lgbm_pipeline.joblib   # LightGBM pipeline model
└── preprocessing/         # Preprocessing artifacts
    ├── isw_kmeans.joblib
    ├── isw_ohe.joblib
    ├── isw_pca.joblib
    ├── isw_vectorizer.joblib
    ├── merged_df_encoder.joblib
    └── tg_vectorizer.joblib
data/                      # Data files
├── alarms/                # Alarm data
├── isw/                   # ISW report data
├── merged/                # Merged datasets
├── predictions/           # Prediction outputs
├── telegram/              # Telegram data
└── weather/               # Weather data
eda/                       # Exploratory data analysis notebooks
frontend/                  # Frontend application
└── tactical-map/          # Next.js tactical map visualization
machine learning/          # Machine learning experiment notebooks
```

## Module Descriptions

### Core Application (`app/`)
- **`alarm_forecast.py`**: Main Flask application that serves forecast data via REST API endpoints.
- **`errors.py`**: Custom exception handling for the Flask application.

### Features (`app/core/features/`)
- **`alarms_features.py`**: Processes alarm data, including exploding alarm periods by hour and calculating features like alarm duration and regional counts.
- **`isw_features.py`**: Extracts features from ISW reports, including text vectorization and clustering.
- **`merge_data.py`**: Utilities for merging data from different sources into a unified dataset.
- **`telegram_features.py`**: Processes Telegram messages, extracting sentiment and temporal features.
- **`weather_features.py`**: Handles weather forecast data, including regional mapping and feature engineering.

### Model Scripts (`app/core/model_scripts/`)
- **`lgbm_predict.py`**: Loads the trained LightGBM model and generates predictions for current hour.
- **`lgbm_retrain.py`**: Retrains the LightGBM model with new data.

### Scraping (`app/core/scraping/`)
- **`alarm.py`**: Scrapes real-time alarm data from Ukraine Alarm API.
- **`scraper_isw.py`**: Scrapes ISW daily reports from their website.
- **`telegram_parser.py`**: Parses Telegram channel messages for relevant information.
- **`weather_forecast.py`**: Fetches weather forecast data from APIs.

### Database (`db/`)
- **`database.py`**: Main database class that manages connections and provides unified interface to all data tables.
- **`alarms_db.py`**: Handles alarm data storage and retrieval.
- **`isw_db.py`**: Manages ISW report data.
- **`telegram_db.py`**: Handles Telegram message data.
- **`weather_db.py`**: Manages weather forecast data.

### Frontend (`frontend/tactical-map/`)
A Next.js application that provides a tactical map visualization of alarm forecasts and historical data.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd DS_lab
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file with necessary API keys (e.g., `ALARM_API_KEY`).

5. Initialize the database:
   ```bash
   python -c "from app.db.database import Database; db = Database('app/db/database.db'); db.close()"
   ```

6. For the frontend:
   ```bash
   cd frontend/tactical-map
   npm install
   ```

## Usage

### Running the Backend
```bash
python alarm_forecast.py
```
This starts the Flask server on `http://localhost:5000`.

### API Endpoints
- `GET /forecast`: Returns current alarm forecast data in JSON format.

### Running the Frontend
```bash
cd frontend/tactical-map
npm run dev
```
Open `http://localhost:3000` to view the tactical map.

### Data Scraping
Run individual scrapers as needed:
```bash
python -c "from app.core.scraping.alarm import get_alarm_status; print(get_alarm_status())"
```

### Model Prediction
```bash
python app/core/model_scripts/lgbm_predict.py
```

## Deployment to AWS

### Prerequisites
- AWS account with appropriate permissions
- AWS CLI installed and configured
- Git repository accessible

### Backend Deployment (Flask App)

#### Option 1: AWS Elastic Beanstalk
1. Install EB CLI:
   ```bash
   pip install awsebcli
   ```

2. Initialize EB:
   ```bash
   eb init -p python-3.9 alarm-forecast
   ```

3. Create environment:
   ```bash
   eb create alarm-forecast-env
   ```

4. Deploy:
   ```bash
   eb deploy
   ```

#### Option 2: AWS EC2
1. Launch EC2 instance (Ubuntu 20.04, t2.micro or larger).

2. SSH into the instance and install dependencies:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip git
   ```

3. Clone the repository:
   ```bash
   git clone <repository-url>
   cd DS_lab
   ```

4. Set up virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

5. Set environment variables (API keys) in `.env` file.

6. Run the application:
   ```bash
   python alarm_forecast.py
   ```

7. Use systemd to run as service:
   Create `/etc/systemd/system/alarm-forecast.service`:
   ```
   [Unit]
   Description=Alarm Forecast Flask App
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/DS_lab
   ExecStart=/home/ubuntu/DS_lab/.venv/bin/python alarm_forecast.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl enable alarm-forecast
   sudo systemctl start alarm-forecast
   ```

8. Configure security group to allow inbound traffic on port 5000.

### Frontend Deployment (Next.js App)

#### AWS Amplify
1. Go to AWS Amplify Console.

2. Connect your Git repository.

3. Select the `frontend/tactical-map` folder as the app root.

4. Configure build settings:
   - Build command: `npm run build`
   - Output directory: `.next`

5. Add environment variables if needed.

6. Deploy.

#### Alternative: S3 + CloudFront
1. Build the Next.js app:
   ```bash
   cd frontend/tactical-map
   npm run build
   npm run export  # If using static export
   ```

2. Upload `out/` directory to S3 bucket.

3. Configure CloudFront distribution pointing to the S3 bucket.

4. Set up custom domain if needed.

### Database
The current setup uses SQLite, which is suitable for development. For production:

1. Migrate to AWS RDS (PostgreSQL recommended).

2. Update database connection strings in the code.

3. Run database migrations if needed.

### Scheduled Tasks (Scraping)
To run scraping scripts periodically:

1. Set up cron jobs on EC2:
   ```bash
   crontab -e
   ```
   Add lines like:
   ```
   0 * * * * /home/ubuntu/DS_lab/.venv/bin/python -c "from app.core.scraping.alarm import scrape_and_store; scrape_and_store()"
   0 6 * * * /home/ubuntu/DS_lab/.venv/bin/python -c "from app.core.scraping.scraper_isw import scrape_isw; scrape_isw()"
   ```

2. Alternatively, use AWS Lambda with CloudWatch Events for serverless scraping.

### Monitoring and Logging
- Use AWS CloudWatch for logs and monitoring.
- Set up alarms for EC2 instance health.
- Consider AWS X-Ray for tracing if needed.

### Security Considerations
- Store API keys and secrets in AWS Systems Manager Parameter Store or Secrets Manager.
- Use HTTPS (configure SSL certificate).
- Implement proper authentication/authorization if needed.
- Regularly update dependencies and apply security patches.

### Cost Optimization
- Use appropriate EC2 instance types.
- Set up auto-scaling if traffic varies.
- Use reserved instances for predictable workloads.
- Monitor usage with AWS Cost Explorer.