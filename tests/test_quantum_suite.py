"""
test_quantum_suite.py - Verification and Unit Tests for PulsePress Q.
Tests:
1. QuantumFeaturePipeline (TF-IDF + TruncatedSVD dimensionality reduction)
2. VariationalQuantumClassifier (PennyLane 4-qubit circuit simulation)
3. QuantumSentimentPredictor (Unified multi-model inference)
4. Flask Web Application & API endpoints (/quantum-lab, /api/analyze-headline, /api/quantum-benchmark)
"""

import os
import pytest
import numpy as np

from src.quantum.quantum_features import QuantumFeaturePipeline
from src.quantum.quantum_vqc import VariationalQuantumClassifier
from src.quantum_predictor import QuantumSentimentPredictor
from app import app


@pytest.fixture(scope="module")
def project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_quantum_feature_pipeline(project_root):
    pipe_path = os.path.join(project_root, "models", "quantum", "quantum_feature_pipeline.joblib")
    assert os.path.exists(pipe_path), f"Feature pipeline missing at {pipe_path}"
    pipeline = QuantumFeaturePipeline.load(pipe_path)
    
    test_texts = [
        "Record-breaking economic recovery brings unprecedented optimism",
        "Tragic disaster causes severe casualties and deep sorrow"
    ]
    features = pipeline.transform(test_texts)
    assert features.shape == (2, 4), f"Expected shape (2, 4), got {features.shape}"
    assert np.all(features >= -np.pi), "Features must be >= -pi"
    assert np.all(features <= np.pi), "Features must be <= pi"


def test_variational_quantum_classifier(project_root):
    vqc_path = os.path.join(project_root, "models", "quantum", "vqc_weights.joblib")
    assert os.path.exists(vqc_path), f"VQC artifact missing at {vqc_path}"
    vqc = VariationalQuantumClassifier.load(vqc_path)
    assert vqc.is_trained is True
    assert vqc.n_qubits == 4

    # Test single state evaluation
    dummy_x = np.array([0.5, -1.0, 1.2, -0.4])
    exp_z = float(vqc._circuit(dummy_x, vqc.weights))
    assert -1.0 <= exp_z <= 1.0, f"Pauli-Z expectation must be in [-1, 1], got {exp_z}"

    # Test batch probabilities
    probs = vqc.predict_proba([dummy_x, -dummy_x])
    assert len(probs) == 2
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)

    # Test circuit diagram generation
    ascii_diag = vqc.get_circuit_ascii()
    assert "0: " in ascii_diag, "ASCII diagram should display qubit wire 0"
    assert "AngleEmbedding" in ascii_diag, "ASCII diagram should display AngleEmbedding"


def test_quantum_sentiment_predictor(project_root):
    predictor = QuantumSentimentPredictor(base_dir=project_root)
    assert predictor.vqc_model is not None
    assert predictor.lr_model is not None
    assert predictor.distilbert_model is not None

    headline = "Breakthrough medical therapy approved after historic clinical success"
    res = predictor.analyze_headline(headline, model_choice="all")
    assert res["sentiment"] in ("Positive", "Negative", "Neutral")
    assert 0.0 <= res["confidence"] <= 100.0
    assert "vqc" in res["models"]
    assert "logistic_regression" in res["models"]
    assert "distilbert" in res["models"]
    assert "disclaimer" in res


def test_flask_routes(client):
    # 1. Main News Feed
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert b"PulsePress" in res_index.data

    # 2. Quantum Lab Page
    res_lab = client.get("/quantum-lab")
    assert res_lab.status_code == 200
    assert b"Quantum-Enhanced Sentiment Analysis Lab" in res_lab.data
    assert b"PennyLane default.qubit" in res_lab.data

    # 3. Benchmark API
    res_bm = client.get("/api/quantum-benchmark")
    assert res_bm.status_code == 200
    json_bm = res_bm.get_json()
    assert "evaluation_samples" in json_bm
    assert "Variational Quantum Classifier (VQC)" in json_bm["results"]

    # 4. Live Headline Analysis API
    res_api = client.get("/api/analyze-headline?headline=Historic+peace+treaty+signed")
    assert res_api.status_code == 200
    json_api = res_api.get_json()
    assert json_api["success"] is True
    assert "vqc" in json_api["models"]
    assert "logistic_regression" in json_api["models"]
    assert "distilbert" in json_api["models"]
