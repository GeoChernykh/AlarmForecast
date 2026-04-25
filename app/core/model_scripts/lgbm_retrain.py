import pandas as pd
import numpy as np
import datetime as dt
import joblib
from pathlib import Path

from app.db.database import Database

from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score, f1_score, matthews_corrcoef
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TODAY = dt.datetime.now()

# Loading data
db_path = Path("app/db/database.db")
data_start_date = (TODAY - dt.timedelta(days=450)).strftime("%Y-%m-%d")
with Database(db_path) as db:
    data = db.get_merged(start_date=data_start_date)

# Loading previous model if one exists
model_path = Path("app/models/lgbm_pipeline.joblib")
if model_path.exists():
    prev_pipeline = joblib.load(model_path)
else:
    print(f"Model not found on pass: {model_path}")
    prev_pipeline = None


# Splitting data
target = "alarm"
X = data.copy()
y = X.pop(target)

split_date = (TODAY - dt.timedelta(days=7)).strftime("%Y-%m-%d %H")
train_mask = X.time < split_date
test_mask = X.time > split_date

X_train, y_train = X[train_mask], y[train_mask]
X_test, y_test = X[test_mask], y[test_mask]


# Defining model
params = {
    'n_estimators': 592,
    'max_depth': 7,
    'num_leaves': 60,
    'min_child_samples': 38,
    'learning_rate': 0.14983796743221423,
    'subsample': 0.9337915945737416,
    'colsample_bytree': 0.7747804530512956,
    'reg_alpha': 0.04542552662628247,
    'reg_lambda': 0.3468310912329435,
    'min_split_gain': 0.061736013814935646
}

new_model = LGBMClassifier(**params, random_state=42, verbose=-1)

cat_cols = list(X.select_dtypes(include=["category", "object"], exclude=["datetime"]).columns)
num_cols = [col for col in X.select_dtypes(include="number").columns if col not in cat_cols]

preprocessor = ColumnTransformer(transformers=[
    ('scale', StandardScaler(), num_cols),
    ("drop_cols", "drop", ["time"]),
], remainder='passthrough')

new_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('model', new_model)
])

# Training and evaluating new model
def calculate_transition_weights(X, y):
    is_change = X['alarm_status_1h_ago'].values != y.values
    n_same = (~is_change).sum()
    n_change = is_change.sum()
    weight_change = n_same / n_change
    sample_weights = np.where(is_change, weight_change, 1.0)
    return sample_weights

def combined_weights(X, y):
    transition_weights = calculate_transition_weights(X, y)
    
    n_neg = (y == 0).sum()
    n_pos = (y == 1).sum()
    
    class_w = np.where(y == 1, n_neg / n_pos, 1.0)
    sample_weights = transition_weights * class_w
    return sample_weights

weights = combined_weights(X_train, y_train)
new_pipeline.fit(X_train, y_train, model__sample_weight=weights)

y_preds = new_pipeline.predict(X_test)
y_pred_probs = new_pipeline.predict_proba(X_test)[:, 1]
f1_score_ = f1_score(y_test, y_preds)
roc_auc_score_ = roc_auc_score(y_test, y_pred_probs)
mcc_score = matthews_corrcoef(y_test, y_preds)
print(f"New | f1: {f1_score_:.4f}, roc_auc: {roc_auc_score_:.4f}, mcc: {mcc_score:.4f}")

# Evaluate previous model if one exists, else save new model
if prev_pipeline is None:
    print(f"Previous model does not exists. Saving new model to {model_path}")
    if not model_path.parent.exists():
            model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(new_pipeline, model_path)
else:
    y_preds_prev = prev_pipeline.predict(X_test)
    y_pred_probs_prev = prev_pipeline.predict_proba(X_test)[:, 1]
    f1_score_prev = f1_score(y_test, y_preds_prev)
    roc_auc_score_prev = roc_auc_score(y_test, y_pred_probs_prev)
    mcc_score_prev = matthews_corrcoef(y_test, y_preds_prev)
    print(f"Old | f1: {f1_score_prev:.4f}, roc_auc: {roc_auc_score_prev:.4f}, mcc: {mcc_score_prev:.4f}")

    # Save new model if f1, mcc and roc auc is higher than previous model
    if f1_score_ > f1_score_prev and roc_auc_score_ > roc_auc_score_prev and mcc_score > mcc_score_prev:
        print(f"New model have higher results. Saving to {model_path}")
        joblib.dump(new_pipeline, model_path)
    else:
        print(f"Old model perform better.")
