"""
explain.py - Token-level feature attribution and interpretability module.
Provides prediction explanations for:
1. Logistic Regression: Learned feature coefficients for active tokens.
2. Multinomial Naive Bayes: Word log-likelihood ratio (Log Odds: log P(w|Pos) - log P(w|Neg)).
3. PyTorch LSTM: Word occlusion / perturbation attribution (Marginal probability delta).
"""

import os
import re
import logging
from typing import List, Dict, Any, Tuple

import numpy as np
import joblib
import torch

from src.preprocessing import clean_text, TextTokenizer
from src.train_lstm import SentimentLSTM

logger = logging.getLogger(__name__)


def explain_logistic_regression(
    text: str,
    model: Any,
    vectorizer: Any,
    top_k: int = 6
) -> Dict[str, Any]:
    """
    Explain Logistic Regression prediction by inspecting model coefficients
    for all n-grams present in the user text.
    """
    cleaned = clean_text(text)
    feature_names = np.array(vectorizer.get_feature_names_out())
    coefs = model.coef_[0]

    # Transform text to sparse vector
    tfidf_vec = vectorizer.transform([cleaned])
    nonzero_indices = tfidf_vec.nonzero()[1]

    if len(nonzero_indices) == 0:
        return {
            "method": "Logistic Regression Coefficients",
            "active_tokens": [],
            "top_positive": [],
            "top_negative": [],
            "summary": "No registered vocabulary terms found in input text."
        }

    # For each active term, calculate contribution = tfidf_value * coefficient
    words = feature_names[nonzero_indices]
    values = tfidf_vec.data
    term_coefs = coefs[nonzero_indices]
    contributions = values * term_coefs

    sorted_indices = np.argsort(contributions)

    # Negative terms (lowest negative values)
    top_neg_idx = sorted_indices[:top_k]
    # Positive terms (highest positive values)
    top_pos_idx = sorted_indices[::-1][:top_k]

    top_positive = [
        {"word": words[i], "score": float(contributions[i]), "coefficient": float(term_coefs[i])}
        for i in top_pos_idx if contributions[i] > 0
    ]

    top_negative = [
        {"word": words[i], "score": float(contributions[i]), "coefficient": float(term_coefs[i])}
        for i in top_neg_idx if contributions[i] < 0
    ]

    all_active = [
        {"word": words[i], "score": float(contributions[i]), "coefficient": float(term_coefs[i])}
        for i in sorted_indices[::-1]
    ]

    return {
        "method": "Linear Model Coefficients & TF-IDF Weights",
        "active_tokens": all_active,
        "top_positive": top_positive,
        "top_negative": top_negative,
        "summary": f"Identified {len(nonzero_indices)} active vocabulary tokens influencing the classification."
    }


def explain_naive_bayes(
    text: str,
    model: Any,
    vectorizer: Any,
    top_k: int = 6
) -> Dict[str, Any]:
    """
    Explain Multinomial Naive Bayes prediction using token log-likelihood ratio:
    Log Ratio = log P(w | Positive) - log P(w | Negative)
    Positive values push toward Positive sentiment; Negative values push toward Negative sentiment.
    """
    cleaned = clean_text(text)
    feature_names = np.array(vectorizer.get_feature_names_out())

    # class 0 = negative, class 1 = positive
    # model.feature_log_prob_ has shape (2, n_features)
    log_probs_neg = model.feature_log_prob_[0]
    log_probs_pos = model.feature_log_prob_[1]
    log_odds_ratio = log_probs_pos - log_probs_neg

    tfidf_vec = vectorizer.transform([cleaned])
    nonzero_indices = tfidf_vec.nonzero()[1]

    if len(nonzero_indices) == 0:
        return {
            "method": "Naive Bayes Log-Odds Ratio",
            "active_tokens": [],
            "top_positive": [],
            "top_negative": [],
            "summary": "No registered vocabulary terms found in input text."
        }

    words = feature_names[nonzero_indices]
    token_log_odds = log_odds_ratio[nonzero_indices]

    sorted_indices = np.argsort(token_log_odds)

    top_neg_idx = sorted_indices[:top_k]
    top_pos_idx = sorted_indices[::-1][:top_k]

    top_positive = [
        {"word": words[i], "score": float(token_log_odds[i])}
        for i in top_pos_idx if token_log_odds[i] > 0
    ]

    top_negative = [
        {"word": words[i], "score": float(token_log_odds[i])}
        for i in top_neg_idx if token_log_odds[i] < 0
    ]

    all_active = [
        {"word": words[i], "score": float(token_log_odds[i])}
        for i in sorted_indices[::-1]
    ]

    return {
        "method": "Naive Bayes Log-Likelihood Ratio [log P(w|Pos) - log P(w|Neg)]",
        "active_tokens": all_active,
        "top_positive": top_positive,
        "top_negative": top_negative,
        "summary": f"Identified {len(nonzero_indices)} active vocabulary tokens contributing to posterior odds."
    }


def explain_lstm_occlusion(
    text: str,
    model: SentimentLSTM,
    tokenizer: TextTokenizer,
    base_prob: float,
    top_k: int = 6
) -> Dict[str, Any]:
    r"""
    Explain LSTM prediction using word-level occlusion (perturbation attribution).
    For each word w_i in the input, computes delta_p = P(Pos | full_text) - P(Pos | text \ {w_i}).
    Positive delta indicates the word supported the positive prediction.
    Negative delta indicates the word supported the negative prediction.
    """
    cleaned = clean_text(text)
    words = cleaned.split()

    if len(words) <= 1:
        return {
            "method": "Word Occlusion Attribution",
            "active_tokens": [{"word": w, "score": 0.0} for w in words],
            "top_positive": [],
            "top_negative": [],
            "summary": "Input text too brief for comparative perturbation analysis."
        }

    # Generate perturbed texts by omitting one word at a time
    perturbed_texts = []
    for i in range(len(words)):
        perturbed = " ".join([words[j] for j in range(len(words)) if j != i])
        perturbed_texts.append(perturbed)

    # Batch transform and run model inference
    X_perturbed = tokenizer.transform(perturbed_texts)
    with torch.no_grad():
        x_tensor = torch.tensor(X_perturbed, dtype=torch.long)
        perturbed_probs = model.predict_proba(x_tensor).cpu().numpy().flatten()

    # Delta probability: positive if omitting drops the positive score
    deltas = base_prob - perturbed_probs

    active_tokens = []
    for i, word in enumerate(words):
        active_tokens.append({"word": word, "score": float(deltas[i])})

    # Sort tokens by impact
    sorted_tokens = sorted(active_tokens, key=lambda x: x["score"], reverse=True)

    top_positive = [t for t in sorted_tokens if t["score"] > 0.001][:top_k]
    top_negative = [t for t in sorted(active_tokens, key=lambda x: x["score"]) if t["score"] < -0.001][:top_k]

    return {
        "method": "Word Occlusion Attribution [ΔP = P(Full) - P(Occluded)]",
        "active_tokens": sorted_tokens,
        "top_positive": top_positive,
        "top_negative": top_negative,
        "summary": f"Analyzed marginal contribution across {len(words)} tokens via systematic occlusion."
    }
