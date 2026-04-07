import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import joblib

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.preprocessing import OneHotEncoder
from scipy.spatial.distance import cosine
from scipy.stats import entropy as scipy_entropy

import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt_tab')

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer

import os
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")


pd.set_option("display.max_columns", None)

models_path = Path("app/models/preprocessing/")

vectorizer = joblib.load(models_path / "isw_vectorizer.joblib")
kmeans = joblib.load(models_path / "isw_kmeans.joblib")
pca = joblib.load(models_path / "isw_pca.joblib")
ohe = joblib.load(models_path / "isw_ohe.joblib")

TODAY = datetime.today().date()

stop_words = {
 'a',
 'about',
 'above',
 'after',
 'again',
 # 'against',
 'ain',
 'all',
 'am',
 'an',
 'and',
 'any',
 'are',
 'aren',
 # "aren't",
 'as',
 'at',
 'be',
 'because',
 'been',
 'before',
 'being',
 'below',
 'between',
 'both',
 'but',
 'by',
 'can',
 # 'couldn',
 # "couldn't",
 'd',
 'did',
 # 'didn',
 # "didn't",
 'do',
 'does',
 # 'doesn',
 # "doesn't",
 'doing',
 'don',
 # "don't",
 'down',
 'during',
 'each',
 'few',
 'for',
 'from',
 'further',
 'had',
 # 'hadn',
 # "hadn't",
 'has',
 # 'hasn',
 # "hasn't",
 'have',
 # 'haven',
 # "haven't",
 'having',
 'he',
 "he'd",
 "he'll",
 "he's",
 'her',
 'here',
 'hers',
 'herself',
 'him',
 'himself',
 'his',
 'how',
 'i',
 "i'd",
 "i'll",
 "i'm",
 "i've",
 'if',
 'in',
 'into',
 'is',
 # 'isn',
 # "isn't",
 'it',
 "it'd",
 "it'll",
 "it's",
 'its',
 'itself',
 'just',
 'll',
 'm',
 'ma',
 'me',
 'mightn',
 # "mightn't",
 'more',
 'most',
 # 'mustn',
 # "mustn't",
 'my',
 'myself',
 # 'needn',
 # "needn't",
 # 'no',
 # 'nor',
 # 'not',
 'now',
 'o',
 'of',
 'off',
 'on',
 'once',
 'only',
 'or',
 'other',
 'our',
 'ours',
 'ourselves',
 'out',
 'over',
 'own',
 're',
 's',
 'same',
 'shan',
 "shan't",
 'she',
 "she'd",
 "she'll",
 "she's",
 'should',
 "should've",
 # 'shouldn',
 # "shouldn't",
 'so',
 'some',
 'such',
 't',
 'than',
 'that',
 "that'll",
 'the',
 'their',
 'theirs',
 'them',
 'themselves',
 'then',
 'there',
 'these',
 'they',
 "they'd",
 "they'll",
 "they're",
 "they've",
 'this',
 'those',
 'through',
 'to',
 'too',
 'under',
 'until',
 'up',
 've',
 'very',
 'was',
 # 'wasn',
 # "wasn't",
 'we',
 "we'd",
 "we'll",
 "we're",
 "we've",
 'were',
 'weren',
 "weren't",
 'what',
 'when',
 'where',
 'which',
 'while',
 'who',
 'whom',
 'whose',
 'why',
 'will',
 'with',
 'won',
 # "won't",
 # 'wouldn',
 # "wouldn't",
 'y',
 'you',
 "you'd",
 "you'll",
 "you're",
 "you've",
 'your',
 'yours',
 'yourself',
 'yourselves',
 "dot"}

def create_features_isw(isw):
    isw['date'] = pd.to_datetime(isw['date']).dt.date
    isw = isw.loc[isw.date >= datetime(2022, 2, 24).date()]

    isw["text_length"] = isw['text'].apply(len)

    lemmatizer = WordNetLemmatizer()

    def nltk_preprocess(text):
        tokens = word_tokenize(text.lower())

        tokens = [
            lemmatizer.lemmatize(t)
            for t in tokens
            if t.isalpha() and t not in stop_words
        ]

        return tokens

    isw["preprocessed_text"] = isw["text"].apply(nltk_preprocess)
    isw["preprocessed_text"] = isw["preprocessed_text"].apply(" ".join)

    vectorized_text = vectorizer.transform(isw["preprocessed_text"])
    isw["vectorized_text"] = vectorized_text.toarray().tolist()

    cluster_labels = kmeans.predict(vectorized_text)

    pca_features = pca.transform(np.array(list(isw["vectorized_text"])))

    isw["cluster"] = cluster_labels

    pca_features = pd.DataFrame(pca_features, columns=[f"isw_PCA{i+1}" for i in range(pca_features.shape[1])])

    isw = pd.concat([isw, pca_features], axis=1)

    pca_cols = list(pca_features.columns)


    WINDOWS = [7, 30] # вікна в днях
    N_CLUSTERS = pd.Series(cluster_labels).nunique()

    nan_mask = isw[pca_cols].isnull().all(axis=1)
    isw = isw[~nan_mask].reset_index(drop=True)

    def centroid(mat):
        """Середній вектор по рядках матриці."""
        return mat.mean(axis=0)


    def cosine_dist(a, b):
        """Cosine distance між двома векторами (0 = ідентичні, 2 = протилежні)."""
        norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return np.nan
        return cosine(a, b)


    def topic_entropy(cluster_labels):
        """Ентропія розподілу кластерів (вища = більш різноманітні теми)."""
        counts = np.bincount(cluster_labels, minlength=N_CLUSTERS)
        probs = counts / counts.sum()
        return float(scipy_entropy(probs + 1e-10))


    def anomaly_count(mat, centroid_vec, threshold_quantile=0.9):
        """Кількість рядків, що далеко від центроїду (потенційні breaking news)."""
        dists = np.array([cosine_dist(row, centroid_vec) for row in mat])
        dists = dists[~np.isnan(dists)]
        if len(dists) == 0:
            return 0
        threshold = np.quantile(dists, threshold_quantile)
        return int((dists >= threshold).sum())


    for W in WINDOWS:

        news_count       = []
        avg_dist_centroid = []
        t_entropy        = []
        dom_cluster_share = []
        news_velocity    = []
        centroid_shift   = []
        anom_count       = []

        for i, row in isw.iterrows():
            current_date = row["date"]
            start_date   = current_date - pd.Timedelta(days=W)

            mask_cur  = (isw["date"] >= start_date) & (isw["date"] < current_date)
            window_df = isw[mask_cur]

            if len(window_df) == 0:
                news_count.append(0)
                avg_dist_centroid.append(np.nan)
                t_entropy.append(np.nan)
                dom_cluster_share.append(np.nan)
                news_velocity.append(np.nan)
                centroid_shift.append(np.nan)
                anom_count.append(0)
                continue

            win_mat     = window_df[pca_cols].values
            win_centroid = centroid(win_mat)
            clusters_win = window_df["cluster"].values.astype(int)

            news_count.append(len(window_df))

            dists = [cosine_dist(r, win_centroid) for r in win_mat]
            avg_dist_centroid.append(float(np.nanmean(dists)))

            t_entropy.append(topic_entropy(clusters_win))

            dom_share = np.bincount(clusters_win, minlength=N_CLUSTERS).max() / len(clusters_win)
            dom_cluster_share.append(float(dom_share))

            prev_start = start_date - pd.Timedelta(days=W)
            mask_prev  = (isw["date"] >= prev_start) & (isw["date"] < start_date)
            prev_count = mask_prev.sum()
            news_velocity.append(len(window_df) - prev_count)

            prev_df = isw[mask_prev]
            if len(prev_df) > 0:
                prev_centroid = centroid(prev_df[pca_cols].values)
                centroid_shift.append(cosine_dist(win_centroid, prev_centroid))
            else:
                centroid_shift.append(np.nan)
            
            anom_count.append(anomaly_count(win_mat, win_centroid))

        isw[f"news_count_{W}d"]            = news_count
        isw[f"avg_dist_centroid_{W}d"]     = avg_dist_centroid
        isw[f"topic_entropy_{W}d"]         = t_entropy
        isw[f"dom_cluster_share_{W}d"]     = dom_cluster_share
        isw[f"news_velocity_{W}d"]         = news_velocity
        isw[f"centroid_shift_{W}d"]        = centroid_shift
        isw[f"anomaly_count_{W}d"]         = anom_count

    feature_cols = ["date", "text_length", "cluster"] + [
        c for c in isw.columns
        if any(c.endswith(f"_{W}d") for W in WINDOWS)
    ]

    isw = isw[feature_cols]

    encoded_clusters = ohe.transform(isw[["cluster"]])

    cluster_cols = [f"isw_{col}" for col in ohe.get_feature_names_out()]
    encoded_clusters = pd.DataFrame(encoded_clusters, columns=cluster_cols)

    isw = pd.concat([isw, encoded_clusters], axis=1).drop(columns="cluster")

    temp = isw.groupby("date")[["text_length"] + cluster_cols].sum().reset_index()

    cols_to_merge = list(set(isw.columns) - {"text_length"} - set(cluster_cols))

    isw = pd.merge(temp, isw[cols_to_merge].drop_duplicates(), how="left", on="date") \
                .reset_index(drop=True)

    date_range = pd.DataFrame({
        "date": pd.date_range(isw["date"].min(), TODAY, freq="D")
    }).date.dt.date

    isw = pd.merge(date_range, isw, how='left', on='date')

    zero_cols = ["text_length", "news_velocity_7d", "news_velocity_30d", "anomaly_count_7d", "anomaly_count_30d"] + cluster_cols

    ffill_cols = [
        "avg_dist_centroid_7d", "avg_dist_centroid_30d",
        "topic_entropy_7d",     "topic_entropy_30d",
        "dom_cluster_share_7d", "dom_cluster_share_30d",
        "centroid_shift_7d",    "centroid_shift_30d",
        "news_count_7d",        "news_count_30d",
    ]

    isw[zero_cols]  = isw[zero_cols].fillna(0)
    isw[ffill_cols] = isw[ffill_cols].ffill()

    cols_to_int = ["text_length", "news_count_7d", "news_count_30d", "anomaly_count_7d", "anomaly_count_30d",
                "news_velocity_7d", "news_velocity_30d"] + cluster_cols

    isw[cols_to_int] = isw[cols_to_int].astype(int)

    return isw