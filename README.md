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
   - Installed Python 3.x, Node.js, and npm on the EC2 instance.
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

## Remote Setup on EC2 Instance

### Prerequisites
- AWS account with permissions to launch EC2 instances
- SSH key pair for secure access

### Step 1: Launch an EC2 Instance
1. Log in to the AWS Management Console.
2. Navigate to the EC2 dashboard.
3. Click "Launch Instance".
4. Choose an Amazon Machine Image (AMI):
   - Recommended: Amazon Linux 2 or Ubuntu Server (free tier eligible).
5. Select instance type:
   - t2.micro (free tier) for testing, or t3.medium/t3.large for production.
6. Configure instance details:
   - Number of instances: 1
   - Network: Default VPC
   - Auto-assign Public IP: Enable
7. Add storage:
   - Default 8GB is sufficient for this project.
8. Configure security group:
   - Create a new security group or select existing.
   - Add rules:
     - SSH (port 22) from your IP or 0.0.0.0/0 (less secure)
     - HTTP (port 80) from 0.0.0.0/0
     - HTTPS (port 443) from 0.0.0.0/0
     - Custom TCP (port 5000) from 0.0.0.0/0 (for Flask app)
     - Custom TCP (port 3000) from 0.0.0.0/0 (for Next.js app)
9. Review and launch.
10. Select or create a key pair, download the .pem file.

### Step 2: Connect to Your EC2 Instance
1. Open a terminal on your local machine.
2. Change permissions on the key file:
   ```bash
   chmod 400 your-key-pair.pem
   ```
3. Connect via SSH:
   ```bash
   ssh -i your-key-pair.pem ec2-user@your-instance-public-ip
   ```
   - For Ubuntu instances, use `ubuntu@` instead of `ec2-user@`.

### Step 3: Update the System
- For Amazon Linux 2:
  ```bash
  sudo yum update -y
  ```
- For Ubuntu:
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```

### Step 4: Install Required Software
1. Install Python 3 and pip:
   - Amazon Linux 2:
     ```bash
     sudo yum install python3 python3-pip -y
     ```
   - Ubuntu:
     ```bash
     sudo apt install python3 python3-pip python3-venv -y
     ```

2. Install Node.js and npm using Node Version Manager (NVM):
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   source ~/.bashrc
   nvm install node
   nvm use node
   ```

3. Install Git:
   - Amazon Linux 2:
     ```bash
     sudo yum install git -y
     ```
   - Ubuntu:
     ```bash
     sudo apt install git -y
     ```

### Step 5: Clone the Repository
```bash
git clone https://github.com/GeoChernykh/AlarmForecast.git
cd AlarmForecast
```

### Step 6: Set Up the Backend
1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Step 7: Set Up the Frontend
1. Navigate to the frontend directory:
   ```bash
   cd frontend/tactical-map
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Build the application:
   ```bash
   npm run build
   ```

4. Return to the project root:
   ```bash
   cd ../..
   ```

### Step 8: Run the Application
1. Start the backend (Flask API):
   ```bash
   source .venv/bin/activate
   python app/api/alarm_forecast.py &
   ```

2. Start the frontend (Next.js):
   ```bash
   cd frontend/tactical-map
   npm start &
   ```

### Step 9: Access the Application
- Backend API: http://your-instance-public-ip:5000
- Frontend: http://your-instance-public-ip:3000

### Step 10: Production Configuration (Optional)
For a production setup, consider:
1. Install PM2 for process management:
   ```bash
   npm install -g pm2
   ```

2. Use PM2 to run applications:
   ```bash
   pm2 start "source .venv/bin/activate && python app/api/alarm_forecast.py" --name backend
   pm2 start "cd frontend/tactical-map && npm start" --name frontend
   pm2 save
   pm2 startup
   ```

3. Set up a reverse proxy with Nginx:
   - Install Nginx
   - Configure proxy_pass for ports 5000 and 3000
   - Enable SSL with Let's Encrypt

4. Configure environment variables and secrets securely.

5. Set up monitoring and logging.

---

## Notes

- The repository does not include the full historical training datasets.
- The project is intended for educational and research purposes.
- Model artifacts and database files are expected to be generated or restored in the live deployment environment.
'