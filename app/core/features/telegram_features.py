"""
preprocess_telegram.py
----------------------
End-to-end preprocessing pipeline for Telegram alert data.

Pipeline steps (matching eda_telegram.ipynb):
  1.  Date parsing & timezone conversion  (Cell 9)
  2.  Drop rows with missing date / text   (Cell 9)
  3.  Deduplication                        (Cell 9)
  4.  Time features                        (Cell 12)
  5.  Text-length feature                  (Cell 17)
  6.  Text cleaning (links, mentions,
      punctuation, digits, stopwords)      (Cells 20-22)
  7.  Threat-keyword flag                  (Cells 25-27)
  8.  Hourly aggregation                   (Cells 42-43)
  9.  NLP features (CountVectorizer)       (Cells 45-46)
  10. Rolling / diff features              (Cell 48)

Public API
----------
preprocess(df, vectorizer=None, fit_vectorizer=True)
    -> (hourly_df, fitted_vectorizer)

clean_text(text)          – stand-alone text cleaner
has_threat(text)          – stand-alone threat detector
"""

import re
import warnings

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
import joblib

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIMEZONE = "Europe/Kiev"

STOP_WORDS: set[str] = {
    "і", "в", "на", "з", "що", "як", "до", "та", "це", "за", "по", "про", "від",
    "для", "а", "ми", "вони", "є", "чи", "або", "але", "тут", "там", "у",
    "и", "с", "что", "как", "к", "это", "о", "от", "які", "який", "все",
    "цього", "буде", "вже", "так", "також", "типу", "нас", "нам",
    "слідкуйте", "подальшими", "повідомленнями",
    "новину", "надіслати", "підписатися",
    "зверніть", "увагу", "район", "область", "територіальна", "громада",
    "м_нікополь_та_нікопольська_територіальна_громада",
    "підписка", "канал", "адмін", "джерело", "посилання", "наслідки",
}

THREAT_KEYWORDS: list[str] = [
    "пуск", "виліт", "баліст", "мопед", "шахед", "ракет",
    "укриття", "увага", "зліт", "міг", "кінжал", "бпла", "загроз",
]

NLP_MAX_FEATURES = 15
NLP_NGRAM_RANGE = (1, 2)

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

VECTORIZER = joblib.load("app/models/preprocessing/tg_vectorizer.joblib")


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def _parse_and_clean_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convert 'date' to datetime, localise to Kyiv time, drop invalid rows."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.tz_convert(TIMEZONE)
    return df


def _drop_missing_and_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows without text and deduplicate on (text, date)."""
    df = df.dropna(subset=["text"])
    df = df.drop_duplicates(subset=["text", "date"])
    return df.reset_index(drop=True)


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive hour, day_of_week, month_year from the date column."""
    df = df.copy()
    df["hour"] = df["date"].dt.hour
    df["day_of_week"] = df["date"].dt.day_name()
    df["month_year"] = df["date"].dt.to_period("M")
    return df


def _add_text_length(df: pd.DataFrame) -> pd.DataFrame:
    """Compute character length of each message."""
    df = df.copy()
    df["text_length"] = df["text"].astype(str).apply(len)
    return df


def clean_text(text: str) -> str:
    """
    Clean a single Telegram message:
      - lowercase
      - strip URLs
      - strip @mentions and # symbols
      - strip punctuation
      - replace underscores with spaces
      - strip digits
      - remove stopwords and very short tokens
    """
    text = str(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)   # remove URLs
    text = re.sub(r"@\w+|#", "", text)                  # remove mentions / hashtags
    text = re.sub(r"[^\w\s]", "", text)                 # remove punctuation
    text = text.replace("_", " ")
    text = re.sub(r"\d+", "", text)                     # remove digits
    words = [
        w for w in text.split()
        if w not in STOP_WORDS and len(w) > 2
    ]
    return " ".join(words)


def has_threat(text: str) -> int:
    """Return 1 if any threat keyword appears in *text*, else 0."""
    text = str(text)
    return int(any(kw in text for kw in THREAT_KEYWORDS))


def _apply_text_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'clean_text' and 'has_threat_keyword' columns."""
    df = df.copy()
    df["clean_text"] = df["text"].apply(clean_text)
    df["has_threat_keyword"] = df["clean_text"].apply(has_threat)
    return df


def _build_hourly_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate to continuous hourly buckets.

    Produces columns:
        datetime, messages_count, has_threat_sum, combined_text
    """
    df = df.copy()
    df["hour_rounded"] = df["date"].dt.floor("h").dt.tz_convert(TIMEZONE)

    hourly = (
        df.groupby("hour_rounded")
        .agg(
            messages_count=("text", "count"),
            has_threat_sum=("has_threat_keyword", "sum"),
            combined_text=("clean_text", lambda x: " ".join(x)),
        )
        .reset_index()
    )

    full_range = pd.date_range(
        start=hourly["hour_rounded"].min(),
        end=hourly["hour_rounded"].max(),
        freq="h",
        tz=TIMEZONE,
    )

    hourly = (
        hourly
        .set_index("hour_rounded")
        .reindex(full_range)
        .fillna({"messages_count": 0, "has_threat_sum": 0, "combined_text": ""})
        .reset_index()
        .rename(columns={"index": "datetime"})
    )

    return hourly


def _add_nlp_features(
    hourly: pd.DataFrame,
    vectorizer: CountVectorizer | None,
    fit_vectorizer: bool,
) -> tuple[pd.DataFrame, CountVectorizer]:
    """
    Fit (or apply) a CountVectorizer on the 'combined_text' column and
    append the resulting token-count columns (prefixed with 'nlp_').

    Returns the updated dataframe and the (fitted) vectorizer.
    """
    hourly = hourly.copy()
    texts = hourly["combined_text"].fillna("")

    if fit_vectorizer or vectorizer is None:
        vectorizer = CountVectorizer(
            max_features=NLP_MAX_FEATURES,
            ngram_range=NLP_NGRAM_RANGE,
        )
        text_vectors = vectorizer.fit_transform(texts)
    else:
        text_vectors = vectorizer.transform(texts)

    feature_names = [
        f"nlp_{w.replace(' ', '_')}"
        for w in vectorizer.get_feature_names_out()
    ]
    nlp_df = pd.DataFrame(text_vectors.toarray(), columns=feature_names)

    hourly = pd.concat([hourly.reset_index(drop=True), nlp_df], axis=1)
    hourly = hourly.drop(columns=["combined_text"])

    return hourly, vectorizer


def _add_rolling_features(hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Add rolling message counts and a 1-hour threat difference.

    New columns:
        msg_count_last_3h   – rolling 3-hour message sum
        msg_count_last_24h  – rolling 24-hour message sum
        threat_diff_1h      – first difference of has_threat_sum
    """
    hourly = hourly.copy()
    hourly["msg_count_last_3h"] = (
        hourly["messages_count"].rolling(3, min_periods=1).sum()
    )
    hourly["msg_count_last_24h"] = (
        hourly["messages_count"].rolling(24, min_periods=1).sum()
    )
    hourly["threat_diff_1h"] = hourly["has_threat_sum"].diff().fillna(0)
    hourly = hourly.fillna(0)
    return hourly


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess(
    df: pd.DataFrame,
    vectorizer: CountVectorizer | None = VECTORIZER,
    fit_vectorizer: bool = False,
) -> tuple[pd.DataFrame, CountVectorizer]:
    """
    Apply the full preprocessing pipeline to a raw Telegram DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw data. Expected columns: 'date', 'text'.
        Additional columns are preserved through step 7 (row-level),
        then dropped during hourly aggregation (step 8).

    vectorizer : CountVectorizer or None
        - None (default) → a new vectorizer is always fitted.
        - Provided vectorizer + fit_vectorizer=True  → re-fit on this data.
        - Provided vectorizer + fit_vectorizer=False → transform only
          (use this for validation / inference sets).

    fit_vectorizer : bool
        Whether to fit the vectorizer on the current data.

    Returns
    -------
    hourly_df : pd.DataFrame
        Hourly-aggregated feature matrix, ready for modelling.

    vectorizer : CountVectorizer
        The fitted (or re-used) CountVectorizer instance.

    Pipeline stages
    ---------------
    1.  Date parsing & timezone conversion
    2.  Drop rows with missing date / text
    3.  Deduplication on (text, date)
    4.  Time features  (hour, day_of_week, month_year)
    5.  Text-length feature
    6.  Text cleaning  → 'clean_text'
    7.  Threat-keyword flag → 'has_threat_keyword'
    8.  Hourly aggregation  → continuous datetime index
    9.  NLP features via CountVectorizer
    10. Rolling / diff features
    """
    # --- row-level steps ---
    df = _parse_and_clean_dates(df)
    df = _drop_missing_and_duplicates(df)
    df = _add_time_features(df)
    df = _add_text_length(df)
    df = _apply_text_pipeline(df)

    # --- aggregation ---
    hourly = _build_hourly_dataframe(df)

    # --- feature engineering on hourly data ---
    hourly, vectorizer = _add_nlp_features(hourly, vectorizer, fit_vectorizer)
    hourly = _add_rolling_features(hourly)
    
    # shift by 1 to prevent data leakage
    cols_to_shift = [
        'messages_count',
        'has_threat_sum',
        'nlp_артобстрілу',
        'nlp_бпла',
        'nlp_відбій',
        'nlp_відбій_тривоги',
        'nlp_дніпропетровська',
        'nlp_донецька',
        'nlp_запорізька',
        'nlp_нікополь',
        'nlp_нікополь_нікопольська',
        'nlp_нікопольська',
        'nlp_повітряна',
        'nlp_повітряна_тривога',
        'nlp_тривога',
        'nlp_тривоги',
        'nlp_харківська',
        'msg_count_last_3h',
        'msg_count_last_24h',
        'threat_diff_1h'
        ]
    hourly[cols_to_shift] = hourly[cols_to_shift].shift(1).fillna(0)

    return hourly, vectorizer


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Minimal synthetic dataset to verify the pipeline runs end-to-end.
    sample = pd.DataFrame({
        "date": [
            "2024-01-10 08:15:00+00:00",
            "2024-01-10 08:20:00+00:00",
            "2024-01-10 09:05:00+00:00",
            "2024-01-10 09:05:00+00:00",   # duplicate
            "2024-01-10 10:00:00+00:00",
            None,                           # missing date
        ],
        "text": [
            "Увага! Пуск балістики з Білорусі https://t.me/example",
            "Шахед виявлено над Харківщиною #alert @channel",
            "Все спокійно в регіоні.",
            "Все спокійно в регіоні.",   # duplicate of row above
            "Міг-31 злетів з аеродрому",
            "This row has no date.",
        ],
    })


    result, vec = preprocess(sample)

    print("Shape:", result.shape)
    print(result.dtypes)
    print(result.head())