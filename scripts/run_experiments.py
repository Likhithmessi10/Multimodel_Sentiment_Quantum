"""
run_experiments.py - Runs empirical evaluation experiments requested for mini project questionnaire:
1. Evaluates DistilBERT on 7,500 IMDb test reviews.
2. Evaluates TextCNN, BiLSTM, LR, and MNB on the same 7,500 test set.
3. Performs Ablation Study on the Ensemble (Full, without BERT, without CNN, without LSTM).
4. Evaluates all models on a curated, hand-labeled news headlines test set (60 headlines).
Outputs metrics to results/experiment_results.json.
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
import torch
import joblib
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from transformers import pipeline

sys.path.insert(0, os.path.abspath("."))
from src.train_cnn import TextCNN
from src.train_lstm import SentimentLSTM
from src.preprocessing import clean_text

os.makedirs("results", exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load Test Dataset & Tokenizers
# ---------------------------------------------------------------------------
print("[*] Loading held-out IMDb test set (7,500 reviews)...")
test_df = pd.read_csv("data/processed/test.csv")
y_test = test_df["label"].values.astype(int)

tok = joblib.load("models/tokenizer.joblib")
X_test_seq = tok.transform(test_df["cleaned_review"].tolist())

tfidf = joblib.load("models/tfidf_vectorizer.joblib")
X_test_tfidf = tfidf.transform(test_df["cleaned_review"].tolist())

# ---------------------------------------------------------------------------
# 2. Evaluate Classical Baselines (LR and Naive Bayes)
# ---------------------------------------------------------------------------
print("[*] Evaluating Logistic Regression on 7,500 test reviews...")
lr_model = joblib.load("models/logistic_regression.joblib")
t0 = time.time()
lr_probs = lr_model.predict_proba(X_test_tfidf)[:, 1]
lr_latency = ((time.time() - t0) / len(y_test)) * 1000
lr_preds = (lr_probs >= 0.5).astype(int)

print("[*] Evaluating Multinomial Naive Bayes on 7,500 test reviews...")
nb_model = joblib.load("models/naive_bayes.joblib")
t0 = time.time()
nb_probs = nb_model.predict_proba(X_test_tfidf)[:, 1]
nb_latency = ((time.time() - t0) / len(y_test)) * 1000
nb_preds = (nb_probs >= 0.5).astype(int)

# ---------------------------------------------------------------------------
# 3. Evaluate PyTorch Deep Learning Models (BiLSTM and TextCNN)
# ---------------------------------------------------------------------------
print("[*] Evaluating BiLSTM on 7,500 test reviews...")
ckpt_lstm = torch.load("models/lstm_model.pt", map_location="cpu")
cfg_lstm = ckpt_lstm["model_config"]
lstm_model = SentimentLSTM(
    vocab_size=cfg_lstm["vocab_size"],
    embedding_dim=cfg_lstm["embedding_dim"],
    hidden_dim=cfg_lstm["hidden_dim"],
    num_layers=cfg_lstm["num_layers"],
    bidirectional=cfg_lstm["bidirectional"],
    dropout=0.0,
    padding_idx=cfg_lstm["padding_idx"]
)
lstm_model.load_state_dict(ckpt_lstm["state_dict"])
lstm_model.eval()

t0 = time.time()
with torch.no_grad():
    # Batch inference for speed
    lstm_probs = []
    bs = 256
    for i in range(0, len(X_test_seq), bs):
        bx = torch.tensor(X_test_seq[i:i+bs], dtype=torch.long)
        p = lstm_model.predict_proba(bx).numpy().flatten()
        lstm_probs.extend(p)
lstm_probs = np.array(lstm_probs)
lstm_latency = ((time.time() - t0) / len(y_test)) * 1000
lstm_preds = (lstm_probs >= 0.5).astype(int)

print("[*] Evaluating TextCNN on 7,500 test reviews...")
cnn_model = TextCNN(vocab_size=tok.max_vocab_size, embedding_dim=128, num_filters=64, filter_sizes=[2, 3, 4, 5], dropout=0.0)
cnn_model.load_state_dict(torch.load("models/text_cnn.pt", map_location="cpu"))
cnn_model.eval()

t0 = time.time()
with torch.no_grad():
    cnn_probs = []
    for i in range(0, len(X_test_seq), bs):
        bx = torch.tensor(X_test_seq[i:i+bs], dtype=torch.long)
        p = torch.sigmoid(cnn_model(bx)).numpy().flatten()
        cnn_probs.extend(p)
cnn_probs = np.array(cnn_probs)
cnn_latency = ((time.time() - t0) / len(y_test)) * 1000
cnn_preds = (cnn_probs >= 0.5).astype(int)

# ---------------------------------------------------------------------------
# 4. Evaluate DistilBERT on 7,500 test reviews
# ---------------------------------------------------------------------------
print("[*] Evaluating DistilBERT on 7,500 test reviews (in batches of 64)...")
classifier = pipeline("sentiment-analysis", model="distilbert/distilbert-base-uncased-finetuned-sst-2-english", device=-1, batch_size=64)

bert_texts = test_df["cleaned_review"].str.slice(0, 512).tolist()
t0 = time.time()
bert_raw_res = classifier(bert_texts)
bert_latency = ((time.time() - t0) / len(y_test)) * 1000

bert_probs = []
for r in bert_raw_res:
    p = float(r["score"]) if r["label"] == "POSITIVE" else float(1.0 - r["score"])
    bert_probs.append(p)
bert_probs = np.array(bert_probs)
bert_preds = (bert_probs >= 0.5).astype(int)

def calc_metrics(y_true, y_pred, y_prob):
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred) * 100), 2),
        "precision": round(float(precision_score(y_true, y_pred) * 100), 2),
        "recall": round(float(recall_score(y_true, y_pred) * 100), 2),
        "f1_score": round(float(f1_score(y_true, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4)
    }

metrics = {
    "Logistic Regression": {**calc_metrics(y_test, lr_preds, lr_probs), "latency_ms": round(lr_latency, 2)},
    "Multinomial Naive Bayes": {**calc_metrics(y_test, nb_preds, nb_probs), "latency_ms": round(nb_latency, 2)},
    "Bidirectional LSTM": {**calc_metrics(y_test, lstm_preds, lstm_probs), "latency_ms": round(lstm_latency, 2)},
    "TextCNN": {**calc_metrics(y_test, cnn_preds, cnn_probs), "latency_ms": round(cnn_latency, 2)},
    "DistilBERT": {**calc_metrics(y_test, bert_preds, bert_probs), "latency_ms": round(bert_latency, 2)}
}

print("\n=== Model Evaluation on 7,500 Held-Out IMDb Test Set ===")
for m_name, m_data in metrics.items():
    print(f"{m_name:25s} | Acc: {m_data['accuracy']}% | Prec: {m_data['precision']}% | Rec: {m_data['recall']}% | F1: {m_data['f1_score']} | AUC: {m_data['roc_auc']} | Lat: {m_data['latency_ms']} ms")

# ---------------------------------------------------------------------------
# 5. Ablation Study (Q72, Q73)
# ---------------------------------------------------------------------------
print("\n[*] Performing Ablation Study on 7,500 Test Set...")
# Full ensemble: 0.50 DistilBERT + 0.30 TextCNN + 0.20 BiLSTM
ens_full_probs = 0.50 * bert_probs + 0.30 * cnn_probs + 0.20 * lstm_probs
ens_full_preds = (ens_full_probs >= 0.5).astype(int)

# Ablation 1: Drop DistilBERT (CNN + LSTM only: 0.60 CNN + 0.40 LSTM)
ens_no_bert_probs = 0.60 * cnn_probs + 0.40 * lstm_probs
ens_no_bert_preds = (ens_no_bert_probs >= 0.5).astype(int)

# Ablation 2: Drop TextCNN (BERT + LSTM only: 0.70 BERT + 0.30 LSTM)
ens_no_cnn_probs = 0.70 * bert_probs + 0.30 * lstm_probs
ens_no_cnn_preds = (ens_no_cnn_probs >= 0.5).astype(int)

# Ablation 3: Drop BiLSTM (BERT + CNN only: 0.60 BERT + 0.40 CNN)
ens_no_lstm_probs = 0.60 * bert_probs + 0.40 * cnn_probs
ens_no_lstm_preds = (ens_no_lstm_probs >= 0.5).astype(int)

ablation_results = {
    "Full Ensemble (BERT + CNN + LSTM)": calc_metrics(y_test, ens_full_preds, ens_full_probs),
    "Ablation A: Drop DistilBERT (CNN + LSTM only)": calc_metrics(y_test, ens_no_bert_preds, ens_no_bert_probs),
    "Ablation B: Drop TextCNN (BERT + LSTM only)": calc_metrics(y_test, ens_no_cnn_preds, ens_no_cnn_probs),
    "Ablation C: Drop BiLSTM (BERT + CNN only)": calc_metrics(y_test, ens_no_lstm_preds, ens_no_lstm_probs)
}

print("=== Ablation Study Results ===")
for a_name, a_data in ablation_results.items():
    print(f"{a_name:45s} | Acc: {a_data['accuracy']}% | F1: {a_data['f1_score']} | AUC: {a_data['roc_auc']}")

# ---------------------------------------------------------------------------
# 6. Hand-Labeled News Headline Evaluation (60 Headlines, Q74-Q77)
# ---------------------------------------------------------------------------
print("\n[*] Evaluating Models on Curated Hand-Labeled News Headlines Benchmark (60 items)...")

labeled_headlines = [
    # Positive News (20 items)
    ("Global renewable energy capacity breaks all-time record with breakthrough solar investment", "Positive"),
    ("Doctors achieve landmark medical breakthrough with successful cancer cure", "Positive"),
    ("Historic peace treaty signed bringing relief and economic prosperity to region", "Positive"),
    ("Global economy rebounds sharply as inflation drops to three-year low", "Positive"),
    ("Scientists successfully restore coral reefs using innovative marine biotechnology", "Positive"),
    ("Airlines celebrate safest year in commercial aviation history", "Positive"),
    ("Billionaire pledges fortune to global clean water and education initiatives", "Positive"),
    ("New pediatric vaccine saves thousands of infant lives across developing nations", "Positive"),
    ("Solar and wind power supply more than half of European electricity in historic milestone", "Positive"),
    ("Tech startup unveils affordable prosthetic limb that restores full mobility", "Positive"),
    ("Endangered tiger population increases by forty percent after successful conservation", "Positive"),
    ("Diplomatic accord reaches breakthrough agreement on regional border dispute", "Positive"),
    ("Researchers develop biodegradable plastic alternative from ocean seaweed", "Positive"),
    ("City opens expansive urban solar park providing free power to schools", "Positive"),
    ("Volunteers rescue dozens of stranded sea turtles after winter storm", "Positive"),
    ("National poverty rate falls to record low following rural job guarantees", "Positive"),
    ("Olympic athlete shatters world record in thrilling sprint final victory", "Positive"),
    ("Farmers celebrate bumper harvest thanks to drought-resilient organic seeds", "Positive"),
    ("Community raises millions to rebuild historic town library and youth center", "Positive"),
    ("Breakthrough Alzheimer drug shows dramatic reversal of cognitive decline in trial", "Positive"),

    # Negative News (25 items)
    ("160 people reported killed in escalating drone attacks across Sudan", "Negative"),
    ("Children among six killed in Russian drone strike on Ukraine park", "Negative"),
    ("Tehran rejects any role in plot to kill leaders of German Jewish groups", "Negative"),
    ("Could your halal pension be funding Israel's military?", "Negative"),
    ("Egyptian parliament delays vote on military support for Saudi Arabia", "Negative"),
    ("Colombia illegal gold mine collapse kills 14 people", "Negative"),
    ("Deadly bus crash claims 28 lives on mountain highway in Peru", "Negative"),
    ("Wildfire sweeps through coastal town destroying hundreds of homes", "Negative"),
    ("Massive chemical leak forces evacuation of five thousand residents", "Negative"),
    ("Hostage crisis in central bank ends with three fatalities and multiple injuries", "Negative"),
    ("Catastrophic floods submerge southern agricultural belt causing widespread famine", "Negative"),
    ("Earthquake of magnitude 7.2 flattens rural villages in eastern province", "Negative"),
    ("Bomb explosion rocks crowded market square during evening prayer", "Negative"),
    ("Armed militants ambush military convoy killing twelve soldiers", "Negative"),
    ("Suicide bombing outside foreign embassy kills nine diplomatic guards", "Negative"),
    ("Hospital confirms twelve infants died following contaminated syrup distribution", "Negative"),
    ("Ferry sinks in rough storm with dozens feared drowned off island coast", "Negative"),
    ("Cyberattack shuts down national power grid and emergency hospital services", "Negative"),
    ("Severe drought leads to catastrophic livestock deaths and water rationing", "Negative"),
    ("Passenger train derails in high-speed collision with freight locomotive", "Negative"),
    ("Gunman opens fire at provincial shopping complex killing eight bystanders", "Negative"),
    ("Illegal toxic waste dumping poisons drinking water reservoir for months", "Negative"),
    ("Severe hurricane strengthens to category five threatening catastrophic destruction", "Negative"),
    ("Military junta sentences opposition journalists to twenty years of hard labor", "Negative"),
    ("Deadly stampede at stadium entrance leaves dozens crushed and injured", "Negative"),

    # Neutral Factual / Objective Quotes (15 items)
    ("Trump: 'Paris is going to be a Muslim city very soon'", "Neutral"),
    ("Hegseth meets Netanyahu in unannounced Israel visit", "Neutral"),
    ("Mahmoud Khalil takes deportation fight to the US Supreme Court", "Neutral"),
    ("Central bank leaves benchmark interest rate unchanged at four percent", "Neutral"),
    ("Parliamentary committee schedules formal hearing on postal service reforms", "Neutral"),
    ("Presidential election ballots dispatched to overseas diplomatic missions", "Neutral"),
    ("Ministry of transport publishes annual road maintenance infrastructure roadmap", "Neutral"),
    ("Census bureau releases updated demographic statistics for metropolitan districts", "Neutral"),
    ("Space agency reschedules satellite launch to next Wednesday due to cloud cover", "Neutral"),
    ("Municipal council debates proposed zoning bylaws for commercial district", "Neutral"),
    ("Finance minister delivers annual fiscal budget address to national assembly", "Neutral"),
    ("Meteorological department forecasts cloudy skies with intermittent rain across north", "Neutral"),
    ("Trade delegation departs for bilateral commerce talks in Tokyo", "Neutral"),
    ("Judicial panel begins deliberation on intellectual property copyright dispute", "Neutral"),
    ("University board appoints new vice chancellor following executive committee vote", "Neutral")
]

from src.predict import SentimentPredictor
pred_engine = SentimentPredictor()

headline_eval_results = []
correct_counts = {
    "Logistic Regression": 0,
    "Multinomial Naive Bayes": 0,
    "Bidirectional LSTM": 0,
    "TextCNN": 0,
    "DistilBERT": 0,
    "Deep Learning Ensemble (PulsePress)": 0
}

# Evaluate each model on the 60 headlines
for title, true_label in labeled_headlines:
    analysis = pred_engine.analyze_news_headline(title)
    
    # 1. LR prediction
    c_title = clean_text(title)
    lr_p = lr_model.predict_proba(tfidf.transform([c_title]))[0, 1]
    lr_pred = "Positive" if lr_p >= 0.55 else ("Negative" if lr_p <= 0.45 else "Neutral")
    
    # 2. NB prediction
    nb_p = nb_model.predict_proba(tfidf.transform([c_title]))[0, 1]
    nb_pred = "Positive" if nb_p >= 0.55 else ("Negative" if nb_p <= 0.45 else "Neutral")
    
    # 3. LSTM
    seq = tok.transform([c_title])
    with torch.no_grad():
        lstm_p = float(lstm_model.predict_proba(torch.tensor(seq, dtype=torch.long)).item())
    lstm_pred = "Positive" if lstm_p >= 0.55 else ("Negative" if lstm_p <= 0.45 else "Neutral")
    
    # 4. TextCNN
    with torch.no_grad():
        cnn_p = float(torch.sigmoid(cnn_model(torch.tensor(seq, dtype=torch.long))).item())
    cnn_pred = "Positive" if cnn_p >= 0.55 else ("Negative" if cnn_p <= 0.45 else "Neutral")
    
    # 5. DistilBERT
    b_res = classifier(title[:512])[0]
    b_p = float(b_res["score"]) if b_res["label"] == "POSITIVE" else float(1.0 - b_res["score"])
    bert_pred = "Positive" if b_p >= 0.55 else ("Negative" if b_p <= 0.45 else "Neutral")
    
    # 6. Ensemble (PulsePress)
    ens_pred = analysis["sentiment"]

    if lr_pred == true_label: correct_counts["Logistic Regression"] += 1
    if nb_pred == true_label: correct_counts["Multinomial Naive Bayes"] += 1
    if lstm_pred == true_label: correct_counts["Bidirectional LSTM"] += 1
    if cnn_pred == true_label: correct_counts["TextCNN"] += 1
    if bert_pred == true_label: correct_counts["DistilBERT"] += 1
    if ens_pred == true_label: correct_counts["Deep Learning Ensemble (PulsePress)"] += 1

total_headlines = len(labeled_headlines)
headline_accuracies = {
    m: round((count / total_headlines) * 100, 2)
    for m, count in correct_counts.items()
}

print(f"\n=== Headline Benchmark Results (Total: {total_headlines} Hand-Labeled News Headlines) ===")
for m, acc in headline_accuracies.items():
    print(f"{m:40s}: {acc}% ({correct_counts[m]}/{total_headlines} correct)")

# ---------------------------------------------------------------------------
# 7. Save All Results to JSON
# ---------------------------------------------------------------------------
final_payload = {
    "imdb_test_metrics_7500": metrics,
    "ablation_study_7500": ablation_results,
    "headline_benchmark_60": {
        "total_headlines": total_headlines,
        "class_breakdown": {"Positive": 20, "Negative": 25, "Neutral": 15},
        "accuracies": headline_accuracies,
        "correct_counts": correct_counts
    }
}

with open("results/experiment_results.json", "w", encoding="utf-8") as f:
    json.dump(final_payload, f, indent=2)

print("\n[+] Successfully saved all empirical results to results/experiment_results.json!")
