"""
Phase 2: Topic & Aspect Extraction
Identifies what customers are talking about using keyword extraction and clustering.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from config import EMBEDDING_MODEL, USE_GPU, PROCESSED_DIR

_KEYBERT_MODEL = None


def _get_keybert():
    """Lazy-load KeyBERT model."""
    global _KEYBERT_MODEL
    if _KEYBERT_MODEL is None:
        from keybert import KeyBERT
        print(f"[topics] Loading KeyBERT with {EMBEDDING_MODEL} ...")
        _KEYBERT_MODEL = KeyBERT(model=EMBEDDING_MODEL)
        print("[topics] KeyBERT loaded.")
    return _KEYBERT_MODEL


def extract_keywords_keybert(texts: List[str], top_n: int = 10, ngram_range: tuple = (1, 2)) -> List[List[Tuple[str, float]]]:
    """Extract keywords using KeyBERT (multilingual embeddings)."""
    kw_model = _get_keybert()
    keywords = kw_model.extract_keywords(
        texts,
        keyphrase_ngram_range=ngram_range,
        stop_words="english",
        top_n=top_n,
        use_mmr=True,
        diversity=0.3,
    )
    return keywords


def extract_keywords_tfidf(texts: List[str], top_n: int = 20) -> List[Tuple[str, float]]:
    """Fast TF-IDF keyword extraction (no ML model needed)."""
    tfidf = TfidfVectorizer(
        max_features=2000,
        ngram_range=(1, 2),
        stop_words="english",
        max_df=0.85,
        min_df=2,
    )

    try:
        tfidf_matrix = tfidf.fit_transform(texts)
    except ValueError:
        return []

    scores = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
    top_indices = scores.argsort()[-top_n:][::-1]
    feature_names = tfidf.get_feature_names_out()

    return [(feature_names[i], float(scores[i])) for i in top_indices]


def extract_keywords_per_place(df: pd.DataFrame, method: str = "tfidf") -> Dict[str, List[Tuple[str, float]]]:
    """Extract top keywords for each place separately."""
    place_keywords = {}
    for place_name, group in df.groupby("place_name"):
        texts = group["clean_text"].tolist()
        if len(texts) < 3:
            place_keywords[place_name] = []
            continue

        if method == "keybert":
            kw_list = extract_keywords_keybert(texts, top_n=15)
            flat_keywords = Counter()
            for kw_set in kw_list:
                for kw, score in kw_set:
                    flat_keywords[kw] += score
            place_keywords[place_name] = flat_keywords.most_common(15)
        else:
            place_keywords[place_name] = extract_keywords_tfidf(texts, top_n=15)

    return place_keywords


def extract_global_keywords(df: pd.DataFrame, method: str = "tfidf") -> List[Tuple[str, float]]:
    """Extract global keywords across all reviews."""
    texts = df["clean_text"].tolist()
    if method == "keybert":
        all_kw = extract_keywords_keybert(texts, top_n=30)
        flat = Counter()
        for kw_set in all_kw:
            for kw, score in kw_set:
                flat[kw] += score
        return flat.most_common(30)
    return extract_keywords_tfidf(texts, top_n=30)


def run_topic_modeling(df: pd.DataFrame, n_topics: int = 5) -> Dict:
    """
    Run LDA topic modeling to discover latent topics in reviews.

    Returns:
        Dict with topic words and topic distribution per review.
    """
    texts = df["clean_text"].tolist()
    if len(texts) < 10:
        return {"topics": [], "topic_distribution": None}

    vectorizer = CountVectorizer(
        max_features=3000,
        ngram_range=(1, 2),
        stop_words="english",
        max_df=0.8,
        min_df=3,
    )

    try:
        dtm = vectorizer.fit_transform(texts)
    except ValueError:
        return {"topics": [], "topic_distribution": None}

    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        learning_method="online",
        n_jobs=-1,
    )

    try:
        lda.fit(dtm)
    except Exception:
        return {"topics": [], "topic_distribution": None}

    feature_names = vectorizer.get_feature_names_out()
    topics = {}
    for topic_idx, topic in enumerate(lda.components_):
        top_words_idx = topic.argsort()[:-11:-1]
        top_words = [(feature_names[i], float(topic[i])) for i in top_words_idx]
        topics[f"topic_{topic_idx + 1}"] = {
            "words": [w for w, _ in top_words],
            "word_weights": {w: s for w, s in top_words},
        }

    topic_dist = lda.transform(dtm)
    df_topic = pd.DataFrame(
        topic_dist,
        columns=[f"topic_{i + 1}" for i in range(n_topics)],
        index=df.index,
    )

    dominant_topic = df_topic.idxmax(axis=1)
    topic_counts = dominant_topic.value_counts().to_dict()

    result = {
        "topics": topics,
        "topic_distribution": df_topic,
        "dominant_topic_per_review": dominant_topic,
        "topic_counts": topic_counts,
        "n_topics": n_topics,
    }

    print(f"[topics] LDA extracted {n_topics} topics: {topic_counts}")
    return result


def get_phrase_frequencies(df: pd.DataFrame, ngram: int = 3, top_n: int = 25) -> List[Tuple[str, int]]:
    """Get most common n-grams across all reviews."""
    texts = df["clean_text"].tolist()
    vec = CountVectorizer(
        ngram_range=(ngram, ngram),
        stop_words="english",
        max_features=5000,
        max_df=0.8,
        min_df=2,
    )

    try:
        counts = vec.fit_transform(texts)
    except ValueError:
        return []

    sum_counts = np.asarray(counts.sum(axis=0)).flatten()
    top_indices = sum_counts.argsort()[-top_n:][::-1]
    words = vec.get_feature_names_out()

    return [(words[i], int(sum_counts[i])) for i in top_indices]


def generate_word_frequencies(df: pd.DataFrame, top_n: int = 100) -> Dict[str, int]:
    """Generate word frequency distribution across all reviews."""
    all_tokens = []
    for tokens in df["tokens"]:
        if isinstance(tokens, list):
            all_tokens.extend(tokens)
    return Counter(all_tokens).most_common(top_n)


def keyword_sentiment_correlation(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Find keywords that correlate most with positive/negative sentiment.
    """
    if "sentiment_label_num" not in df.columns:
        return pd.DataFrame()

    positive_reviews = " ".join(df[df["sentiment"] == "positive"]["clean_text"].tolist())
    negative_reviews = " ".join(df[df["sentiment"] == "negative"]["clean_text"].tolist())

    pos_keywords = extract_keywords_tfidf([positive_reviews], top_n=top_n) if positive_reviews else []
    neg_keywords = extract_keywords_tfidf([negative_reviews], top_n=top_n) if negative_reviews else []

    data = []
    pos_dict = {kw: score for kw, score in pos_keywords}
    neg_dict = {kw: score for kw, score in neg_keywords}
    all_kw = set(pos_dict.keys()) | set(neg_dict.keys())

    for kw in all_kw:
        pos_score = pos_dict.get(kw, 0)
        neg_score = neg_dict.get(kw, 0)
        data.append({
            "keyword": kw,
            "positive_score": round(pos_score, 3),
            "negative_score": round(neg_score, 3),
            "sentiment_bias": round(pos_score - neg_score, 3),
        })

    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).sort_values("sentiment_bias", ascending=False)
