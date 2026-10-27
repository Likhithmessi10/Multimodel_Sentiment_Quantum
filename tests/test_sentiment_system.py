"""
test_sentiment_system.py - Unit and Integration Tests for Sentiment Analysis System & News Aggregator
Tests preprocessing, tokenization, model loading, predictions, explanations, and edge cases.
"""

import os
import pytest
import numpy as np
import joblib

from src.preprocessing import clean_text, TextTokenizer
from src.predict import SentimentPredictor


@pytest.fixture(scope="module")
def predictor():
    """Shared fixture providing initialized SentimentPredictor."""
    return SentimentPredictor()


def test_clean_text():
    """Verify that text cleaning removes HTML tags, expands contractions, and strips special characters."""
    raw = "<br /><br />This isn't a bad movie! It's actually GREAT... http://example.com"
    cleaned = clean_text(raw)
    assert "<br" not in cleaned
    assert "http" not in cleaned
    assert "is not" in cleaned
    assert "it is" in cleaned
    assert cleaned.islower()


def test_text_tokenizer():
    """Verify vocabulary building, sequence conversion, padding, and truncation."""
    corpus = [
        "the quick brown fox",
        "jumps over the lazy dog",
        "the quick dog"
    ]
    tok = TextTokenizer(max_vocab_size=10, max_seq_len=6)
    tok.fit(corpus)

    assert tok.pad_idx == 0
    assert tok.unk_idx == 1
    assert "the" in tok.word2idx

    # Test sequence conversion
    seq = tok.text_to_sequence("the quick mysterious animal")
    assert seq[0] == tok.word2idx["the"]
    assert seq[1] == tok.word2idx["quick"]
    assert seq[2] == tok.unk_idx  # mysterious is OOV
    assert seq[3] == tok.unk_idx  # animal is OOV

    # Test transform with padding
    transformed = tok.transform(["the quick"])
    assert transformed.shape == (1, 6)
    assert transformed[0, 0] == tok.word2idx["the"]
    assert transformed[0, 1] == tok.word2idx["quick"]
    assert transformed[0, 2] == 0  # pad


def test_logistic_regression_prediction(predictor):
    """Verify Logistic Regression outputs valid sentiment and probabilities."""
    res_pos = predictor.predict("An absolutely fantastic, thrilling masterpiece!", model_name="Logistic Regression")
    assert res_pos["sentiment"] == "Positive"
    assert res_pos["confidence"] > 0.5
    assert 0.0 <= res_pos["prob_positive"] <= 1.0

    res_neg = predictor.predict("A totally boring, pathetic, and unwatchable disaster.", model_name="Logistic Regression")
    assert res_neg["sentiment"] == "Negative"
    assert res_neg["confidence"] > 0.5


def test_naive_bayes_prediction(predictor):
    """Verify Multinomial Naive Bayes outputs valid sentiment and probabilities."""
    res_pos = predictor.predict("A wonderful, heartwarming and delightful experience.", model_name="Multinomial Naive Bayes")
    assert res_pos["sentiment"] == "Positive"
    assert res_pos["confidence"] > 0.5
    assert 0.0 <= res_pos["prob_positive"] <= 1.0

    res_neg = predictor.predict("Awful acting, terrible screenplay, and horrible directing.", model_name="Multinomial Naive Bayes")
    assert res_neg["sentiment"] == "Negative"
    assert res_neg["confidence"] > 0.5


def test_explainability_payload(predictor):
    """Verify feature attribution produces tokens with positive and negative scores."""
    res = predictor.predict("Excellent cinematography but terrible pacing and awful script.", model_name="Logistic Regression")
    explanation = res["explanation"]
    assert "active_tokens" in explanation
    assert len(explanation["active_tokens"]) > 0
    assert any(t["word"] in ["excellent", "terrible", "awful"] for t in explanation["active_tokens"])


def test_lstm_prediction(predictor):
    """Verify Bidirectional LSTM outputs valid sentiment and occlusion attribution."""
    res = predictor.predict("A truly incredible, charming, and delightful film.", model_name="Bidirectional LSTM")
    assert res["sentiment"] in ["Positive", "Negative"]
    assert 0.0 <= res["confidence"] <= 1.0
    assert 0.0 <= res["prob_positive"] <= 1.0
    assert "explanation" in res
    assert "active_tokens" in res["explanation"]


def test_empty_input_handling(predictor):
    """Verify appropriate exception is raised on empty or whitespace inputs."""
    with pytest.raises(ValueError):
        predictor.predict("   ")


def test_analyze_news_headline_consensus(predictor):
    """Verify multi-model news headline consensus logic and tragedy safety override."""
    # Positive headline
    res_pos = predictor.analyze_news_headline("Scientists achieve landmark breakthrough with renewable solar energy record")
    assert res_pos["sentiment"] == "Positive"
    assert "models" in res_pos
    assert "distilbert" in res_pos["models"]
    assert "text_cnn" in res_pos["models"]
    assert "bidirectional_lstm" in res_pos["models"]

    # Critical tragedy override
    res_neg = predictor.analyze_news_headline("Deadly train crash kills 40 passengers after catastrophic explosion")
    assert res_neg["sentiment"] == "Negative"
    assert res_neg["confidence"] >= 0.95
    assert "Tragedy Override" in res_neg["consensus"]


def test_flask_news_routes():
    """Verify Flask web server routes and API endpoint."""
    from app import app
    client = app.test_client()

    # Home route
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"PulsePress" in resp.data

    # Live API analysis endpoint
    resp_api = client.get("/api/analyze-headline?q=Global+peace+summit+reaches+historic+accord")
    assert resp_api.status_code == 200
    data = resp_api.get_json()
    assert data["success"] is True
    assert "models" in data
    assert data["sentiment"] in ["Positive", "Negative", "Neutral"]
