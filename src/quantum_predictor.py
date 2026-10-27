"""
quantum_predictor.py - Unified Quantum & Classical Sentiment Prediction Engine for PulsePress Q.

Streamlined 3-Model Collection:
1. Model A: Classical Baseline - Logistic Regression (TF-IDF 5,000 features)
2. Model B: Deep Learning Contextual Baseline - DistilBERT Transformer (SST-2)
3. Model C: Quantum Machine Learning - Variational Quantum Classifier (4-Qubit PennyLane VQC on default.qubit CPU simulator)
"""

import os
import re
import time
import logging
from typing import Dict, Any, Optional, List

import numpy as np
import joblib

from src.quantum.quantum_features import QuantumFeaturePipeline
from src.quantum.quantum_vqc import VariationalQuantumClassifier
from src.models.distilbert_model import DistilBertSentimentClassifier

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
    "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself",
    "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
    "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves", "among", "across", "soon", "city", "said",
    "says", "reported", "report", "according", "people", "groups", "new", "also", "first", "one", "two",
    "three", "today", "yesterday", "going", "will", "say", "told", "tell", "may", "might"
}

POSITIVE_LEXICON = {
    "breakthrough", "cure", "cured", "triumph", "milestone", "peace", "rescue", "saved", "save",
    "healing", "heal", "record", "victory", "win", "wins", "won", "success", "successful", "thrive",
    "thriving", "growth", "growing", "boost", "boosts", "rally", "rallies", "profit", "profits",
    "prosper", "prosperity", "relief", "progress", "advance", "advances", "landmark", "award",
    "awarded", "honored", "honor", "solution", "hope", "hopeful", "rejoice", "celebrate", "celebrates",
    "hero", "heroic", "proud", "pride", "soar", "soaring", "gain", "gains", "favor", "favorable",
    "optimistic", "renewable", "historic", "agreement", "accord", "alliance", "treaty", "support",
    "innovation", "flourish", "masterpiece", "fantastic", "delight", "delightful", "heartwarming", "incredible"
}

NEGATIVE_LEXICON = {
    "kill", "killed", "kills", "killing", "dead", "death", "deaths", "die", "died", "dies", "dying",
    "fatal", "fatalities", "casualty", "casualties", "murder", "murdered", "suicide", "massacre",
    "genocide", "assassin", "assassination", "drown", "drowned", "poison", "crash", "crashes", "crashed",
    "collision", "wreck", "wreckage", "disaster", "tragedy", "tragic", "catastrophe", "catastrophic",
    "earthquake", "tsunami", "explosion", "explode", "exploded", "exploding", "bomb", "bombed", "bombing",
    "bombs", "drone", "strike", "strikes", "attack", "attacks", "attacked", "attacking", "hostage",
    "kidnap", "kidnapped", "terror", "terrorist", "terrorism", "war", "wars", "warfare", "vanish",
    "vanished", "abuse", "rape", "violence", "violent", "military", "plot", "reject", "rejects", "rejected",
    "delay", "delays", "delayed", "crisis", "dispute", "protest", "protests", "collapse", "collapsed",
    "arrest", "arrested", "charged", "convicted", "clash", "clashes", "threat", "threatens", "threatened",
    "danger", "dangerous", "warning", "warns", "warned", "escalate", "escalating", "escalation", "fear",
    "fears", "sanction", "sanctions", "funding", "illicit", "illegal", "scandal", "fraud", "awful",
    "terrible", "horrible", "boring", "pathetic", "unwatchable", "disastrous", "loss", "losses",
    "behead", "beheaded", "slain", "slay", "slaughter", "stab", "stabbed", "shooting", "shot"
}


def extract_keywords(text: str, top_k: int = 5) -> List[Dict[str, str]]:
    """Extract sentiment-bearing words from text."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    seen = set()
    keywords = []
    for w in words:
        if w in STOPWORDS or w in seen:
            continue
        if w in NEGATIVE_LEXICON:
            seen.add(w)
            keywords.append({"word": w, "polarity": "Negative"})
        elif w in POSITIVE_LEXICON:
            seen.add(w)
            keywords.append({"word": w, "polarity": "Positive"})
        if len(keywords) >= top_k:
            break
    return keywords


class QuantumSentimentPredictor:
    """
    Unified predictor supporting:
    - Model A: Logistic Regression (TF-IDF 5000 features)
    - Model B: DistilBERT Transformer (SST-2)
    - Model C: Variational Quantum Classifier (4-Qubit PennyLane on CPU simulator)
    """

    SIMULATION_DISCLAIMER = (
        "Notice: The Variational Quantum Classifier (VQC) executes on an ideal classical "
        "statevector simulator (PennyLane default.qubit) on CPU. It simulates quantum mechanical "
        "operations mathematically and does NOT represent physical NISQ quantum hardware."
    )

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir

        # 1. Model A: Classical Baseline - Logistic Regression
        self.lr_model = None
        self.tfidf_vectorizer = None
        self._load_classical_lr()

        # 2. Model B: Deep Contextual Baseline - DistilBERT
        self.distilbert_model = None
        self._load_distilbert()

        # 3. Model C: Quantum Machine Learning - 4-Qubit VQC
        self.q_pipeline = None
        self.vqc_model = None
        self._load_quantum_vqc()

    def _load_classical_lr(self):
        try:
            lr_path = os.path.join(self.base_dir, "models", "logistic_regression.joblib")
            tfidf_path = os.path.join(self.base_dir, "models", "tfidf_vectorizer.joblib")
            if os.path.exists(lr_path) and os.path.exists(tfidf_path):
                self.lr_model = joblib.load(lr_path)
                self.tfidf_vectorizer = joblib.load(tfidf_path)
                logger.info("[+] Loaded Classical Logistic Regression & TF-IDF Vectorizer.")
        except Exception as e:
            logger.warning(f"[-] Could not load Logistic Regression: {e}")

    def _load_distilbert(self):
        try:
            self.distilbert_model = DistilBertSentimentClassifier()
            logger.info("[+] Loaded DistilBERT SST-2 Transformer.")
        except Exception as e:
            logger.warning(f"[-] Could not load DistilBERT: {e}")

    def _load_quantum_vqc(self):
        try:
            pipe_path = os.path.join(self.base_dir, "models", "quantum", "quantum_feature_pipeline.joblib")
            vqc_path = os.path.join(self.base_dir, "models", "quantum", "vqc_weights.joblib")
            if os.path.exists(pipe_path) and os.path.exists(vqc_path):
                self.q_pipeline = QuantumFeaturePipeline.load(pipe_path)
                self.vqc_model = VariationalQuantumClassifier.load(vqc_path)
                logger.info("[+] Loaded 4-Qubit PennyLane VQC & Quantum Feature Pipeline.")
        except Exception as e:
            logger.warning(f"[-] Could not load Quantum VQC: {e}")

    def predict_vqc(self, text: str) -> Dict[str, Any]:
        """Inference with 4-Qubit Variational Quantum Classifier."""
        if self.vqc_model is None or self.q_pipeline is None:
            return {"error": "Quantum VQC model not loaded."}

        t0 = time.time()
        # Classical feature compression to 4 angles
        x_q = self.q_pipeline.transform([text])[0]
        # Pauli-Z expectation value from quantum simulation
        exp_z = float(self.vqc_model._circuit(x_q, self.vqc_model.weights))
        prob_pos = float((exp_z + 1.0) / 2.0)
        prob_neg = float(1.0 - prob_pos)
        latency_ms = (time.time() - t0) * 1000.0

        sentiment = "Positive" if prob_pos >= 0.5 else "Negative"
        confidence = prob_pos if sentiment == "Positive" else prob_neg

        # Feature explanation (rotation angles mapped to qubits)
        qubit_rotations = [
            {"qubit": i, "angle_radians": round(float(angle), 4), "angle_degrees": round(float(np.degrees(angle)), 1)}
            for i, angle in enumerate(x_q)
        ]

        return {
            "model_name": "Variational Quantum Classifier (4-Qubit VQC)",
            "model_id": "vqc",
            "sentiment": sentiment,
            "confidence": round(confidence * 100.0, 1),
            "prob_positive": round(prob_pos * 100.0, 1),
            "prob_negative": round(prob_neg * 100.0, 1),
            "pauli_z_expectation": round(exp_z, 4),
            "qubit_angles": qubit_rotations,
            "latency_ms": round(latency_ms, 2),
            "qubits": 4,
            "simulator": "PennyLane default.qubit (CPU)",
            "circuit_ascii": self.vqc_model.get_circuit_ascii(),
            "hardware_type": "Ideal Classical Simulation (CPU)"
        }

    def predict_logistic_regression(self, text: str) -> Dict[str, Any]:
        """Inference with classical Logistic Regression baseline."""
        if self.lr_model is None or self.tfidf_vectorizer is None:
            return {"error": "Logistic Regression model not loaded."}

        t0 = time.time()
        vec = self.tfidf_vectorizer.transform([text])
        probs = self.lr_model.predict_proba(vec)[0]
        prob_neg = float(probs[0])
        prob_pos = float(probs[1])
        latency_ms = (time.time() - t0) * 1000.0

        sentiment = "Positive" if prob_pos >= 0.5 else "Negative"
        confidence = prob_pos if sentiment == "Positive" else prob_neg

        # Find top active TF-IDF features
        feature_names = self.tfidf_vectorizer.get_feature_names_out()
        nonzero_idx = vec.nonzero()[1]
        feature_contributions = []
        if hasattr(self.lr_model, "coef_"):
            coefs = self.lr_model.coef_[0]
            for idx in nonzero_idx:
                score = float(vec[0, idx] * coefs[idx])
                feature_contributions.append({
                    "word": feature_names[idx],
                    "weight": round(score, 3),
                    "tendency": "Positive" if score > 0 else "Negative"
                })
            feature_contributions.sort(key=lambda item: abs(item["weight"]), reverse=True)

        return {
            "model_name": "Logistic Regression (TF-IDF Classical Baseline)",
            "model_id": "logistic_regression",
            "sentiment": sentiment,
            "confidence": round(confidence * 100.0, 1),
            "prob_positive": round(prob_pos * 100.0, 1),
            "prob_negative": round(prob_neg * 100.0, 1),
            "latency_ms": round(latency_ms, 2),
            "features_used": 5000,
            "top_features": feature_contributions[:5],
            "hardware_type": "Standard CPU Linear Classifier"
        }

    def predict_distilbert(self, text: str) -> Dict[str, Any]:
        """Inference with DistilBERT contextual Transformer."""
        if self.distilbert_model is None:
            return {"error": "DistilBERT model not loaded."}

        t0 = time.time()
        out = self.distilbert_model.predict_single(text)
        latency_ms = (time.time() - t0) * 1000.0

        prob_pos = float(out["positive_probability"])
        prob_neg = float(1.0 - prob_pos)
        sentiment = out["label"]
        confidence = float(out["confidence"]) / 100.0

        return {
            "model_name": "DistilBERT Transformer (Bidirectional Self-Attention)",
            "model_id": "distilbert",
            "sentiment": sentiment,
            "confidence": round(confidence * 100.0, 1),
            "prob_positive": round(prob_pos * 100.0, 1),
            "prob_negative": round(prob_neg * 100.0, 1),
            "latency_ms": round(latency_ms, 2),
            "architecture": "6-layer, 768-hidden, 12-heads, 66M parameters",
            "hardware_type": "PyTorch CPU Transformer Engine"
        }

    def analyze_headline(self, text: str, model_choice: str = "all") -> Dict[str, Any]:
        """
        Unified headline analysis supporting model selection:
        model_choice: 'all' | 'vqc' | 'logistic_regression' | 'distilbert'
        """
        t0 = time.time()
        results: Dict[str, Any] = {}

        if model_choice in ("all", "vqc"):
            results["vqc"] = self.predict_vqc(text)
        if model_choice in ("all", "logistic_regression"):
            results["logistic_regression"] = self.predict_logistic_regression(text)
        if model_choice in ("all", "distilbert"):
            results["distilbert"] = self.predict_distilbert(text)

        total_latency_ms = (time.time() - t0) * 1000.0

        # Consensus determination
        sentiments = [res["sentiment"] for res in results.values() if "sentiment" in res]
        if sentiments:
            pos_count = sentiments.count("Positive")
            neg_count = sentiments.count("Negative")
            if pos_count > neg_count:
                consensus_sentiment = "Positive"
            elif neg_count > pos_count:
                consensus_sentiment = "Negative"
            else:
                # Break tie with highest confidence or Transformer baseline
                bert_res = results.get("distilbert")
                if bert_res and "sentiment" in bert_res:
                    consensus_sentiment = bert_res["sentiment"]
                else:
                    consensus_sentiment = "Neutral"
            
            # Confidence across available models
            confs = [res["confidence"] for res in results.values() if "confidence" in res]
            avg_confidence = float(np.mean(confs)) if confs else 50.0
            unanimous = (pos_count == len(sentiments)) or (neg_count == len(sentiments))
            consensus_type = "Unanimous Consensus" if unanimous else "Majority Consensus"
        else:
            consensus_sentiment = "Neutral"
            avg_confidence = 50.0
            consensus_type = "Fallback"

        keywords = extract_keywords(text)

        return {
            "headline": text,
            "sentiment": consensus_sentiment,
            "confidence": round(avg_confidence, 1),
            "consensus": consensus_type,
            "models": results,
            "top_keywords": keywords,
            "total_latency_ms": round(total_latency_ms, 2),
            "selected_model": model_choice,
            "disclaimer": self.SIMULATION_DISCLAIMER
        }
