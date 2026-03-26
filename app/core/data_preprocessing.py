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

isw = pd.read_json("data/isw/temp.json", convert_dates=["date"]).sort_values("date", ascending=False).reset_index(drop=True)

isw["date"] = isw["date"].dt.date

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

def isw_preprocess(isw):
    isw = isw.loc[isw.date >= TODAY - timedelta(days=31)]
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

    # Якщо за день кілька рядків — усереднюємо
    daily = (
        isw.groupby("date")[pca_cols + ["cluster", "text_length"]]
        .agg({**{c: "mean" for c in pca_cols}, "cluster": lambda x: x.value_counts().idxmax(), "text_length": "sum"})
        .reset_index()
    )
    daily = daily.sort_values("date").reset_index(drop=True)

    date_range = pd.DataFrame({
        "date": pd.date_range(TODAY - timedelta(days=31), TODAY, freq="D")
    })

    date_range.date = date_range.date.dt.date

    daily = pd.merge(date_range, daily, how='left', on='date')

    daily.text_length = daily.text_length.fillna(0)

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

        for i, row in daily.iterrows():
            current_date = row["date"]
            start_date   = current_date - pd.Timedelta(days=W)

            mask_cur  = (daily["date"] >= start_date) & (daily["date"] < current_date)
            window_df = daily[mask_cur]

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
            mask_prev  = (daily["date"] >= prev_start) & (daily["date"] < start_date)
            prev_count = mask_prev.sum()
            news_velocity.append(len(window_df) - prev_count)

            prev_df = daily[mask_prev]
            if len(prev_df) > 0:
                prev_centroid = centroid(prev_df[pca_cols].values)
                centroid_shift.append(cosine_dist(win_centroid, prev_centroid))
            else:
                centroid_shift.append(np.nan)
            
            anom_count.append(anomaly_count(win_mat, win_centroid))

        daily[f"news_count_{W}d"]            = news_count
        daily[f"avg_dist_centroid_{W}d"]     = avg_dist_centroid
        daily[f"topic_entropy_{W}d"]         = t_entropy
        daily[f"dom_cluster_share_{W}d"]     = dom_cluster_share
        daily[f"news_velocity_{W}d"]         = news_velocity
        daily[f"centroid_shift_{W}d"]        = centroid_shift
        daily[f"anomaly_count_{W}d"]         = anom_count

    feature_cols = ["date", "text_length", "cluster"] + [
        c for c in daily.columns
        if any(c.endswith(f"_{W}d") for W in WINDOWS)
    ]

    isw = daily[feature_cols]

    encoded_clusters = ohe.transform(isw[["cluster"]])

    cluster_cols = [f"isw_{col}" for col in ohe.get_feature_names_out()]
    encoded_clusters = pd.DataFrame(encoded_clusters, columns=cluster_cols)

    isw = pd.concat([isw, encoded_clusters], axis=1).drop(columns="cluster")

    temp = isw.groupby("date")[["text_length"] + cluster_cols].sum()
    cols_to_merge = list(set(isw.columns) - {"text_length"} - set(cluster_cols))

    isw = pd.merge(temp, isw[cols_to_merge], how="left", left_index=True, right_on="date") \
                .reset_index(drop=True)