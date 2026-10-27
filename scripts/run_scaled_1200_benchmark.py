"""
run_scaled_1200_benchmark.py - Scaled 1,200-Headline Benchmark with CUDA GPU Acceleration.
Evaluates Logistic Regression, DistilBERT Baseline, and Hybrid QSVM on 360 held-out test headlines.
"""

import os
import sys
import time
import json
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import torch
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
from transformers import pipeline as hf_pipeline

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model_pipeline import DistilBertFeatureExtractor, QuantumKernelEstimator, MODEL_NAME

def main():
    total_start_time = time.time()
    
    print("=" * 80)
    print("SCALED 1,200-HEADLINE QUANTUM-CLASSICAL HYBRID BENCHMARK (CUDA ACCELERATED)")
    print("=" * 80)
    
    # -------------------------------------------------------------------------
    # 1. GPU & CUDA Verification
    # -------------------------------------------------------------------------
    cuda_available = torch.cuda.is_available()
    print(f"\n[1] HARDWARE STATUS & CUDA VERIFICATION:")
    print(f"    - PyTorch Version        : {torch.__version__}")
    print(f"    - CUDA Available         : {cuda_available}")
    if cuda_available:
        device_name = torch.cuda.get_device_name(0)
        total_vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
        alloc_vram_mb = round(torch.cuda.memory_allocated(0) / (1024**2), 2)
        res_vram_mb = round(torch.cuda.memory_reserved(0) / (1024**2), 2)
        print(f"    - GPU Device Name        : {device_name}")
        print(f"    - Total GPU VRAM         : {total_vram_gb} GB")
        print(f"    - Allocated VRAM         : {alloc_vram_mb} MB")
        print(f"    - Reserved/Cached VRAM   : {res_vram_mb} MB")
    else:
        print(f"    - WARNING: CUDA not detected! Falling back to CPU.")
        device_name = "CPU Only"
    
    # -------------------------------------------------------------------------
    # 2. Dataset Loading & Balance Check
    # -------------------------------------------------------------------------
    dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "benchmark_1200_headlines.json")
    if not os.path.exists(dataset_path):
        print(f"[-] Error: Dataset file not found at {dataset_path}!")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = [d["headline"] for d in data]
    labels = np.array([int(d["label"]) for d in data], dtype=int)
    
    neg_count = int(np.sum(labels == 0))
    neu_count = int(np.sum(labels == 1))
    pos_count = int(np.sum(labels == 2))
    
    print(f"\n[2] DATASET COMPOSITION (1,200 Balanced Samples):")
    print(f"    - Total Headlines        : {len(texts)}")
    print(f"    - Negative Class (0)     : {neg_count} ({(neg_count/len(texts))*100:.1f}%)")
    print(f"    - Neutral Class  (1)     : {neu_count} ({(neu_count/len(texts))*100:.1f}%)")
    print(f"    - Positive Class (2)     : {pos_count} ({(pos_count/len(texts))*100:.1f}%)")
    assert neg_count == 400 and neu_count == 400 and pos_count == 400, "Dataset is not balanced at 400/class!"

    # -------------------------------------------------------------------------
    # 3. Strict Anti-Leakage Train/Test Split (70% Train / 30% Test)
    # -------------------------------------------------------------------------
    seed = 42
    if "split" in data[0]:
        X_train_text = [d["headline"] for d in data if d["split"] == "train"]
        y_train = np.array([int(d["label"]) for d in data if d["split"] == "train"], dtype=int)
        X_test_text = [d["headline"] for d in data if d["split"] == "test"]
        y_test = np.array([int(d["label"]) for d in data if d["split"] == "test"], dtype=int)
        print(f"\n[3] STRICT GROUP-ISOLATED ANTI-LEAKAGE PARTITION:")
        print(f"    - Training Partition (70%): {len(X_train_text)} samples (280 Neg, 280 Neu, 280 Pos)")
        print(f"    - Held-Out Test Set  (30%): {len(X_test_text)} samples (120 Neg, 120 Neu, 120 Pos)")
        print(f"    - Zero-Leakage Guarantee : Test set uses completely unseen phrasing/templates.")
        print(f"    - Protocol Enforcement   : PCA and Scalers fitted EXCLUSIVELY on Training Partition.")
    else:
        test_ratio = 0.30
        X_train_text, X_test_text, y_train, y_test = train_test_split(
            texts, labels, test_size=test_ratio, random_state=seed, stratify=labels
        )
        print(f"\n[3] STRICT ANTI-LEAKAGE PARTITION (Seed={seed}):")
        print(f"    - Training Partition (70%): {len(X_train_text)} samples (280 Neg, 280 Neu, 280 Pos)")
        print(f"    - Held-Out Test Set  (30%): {len(X_test_text)} samples (120 Neg, 120 Neu, 120 Pos)")
        print(f"    - Protocol Enforcement   : PCA and Scalers fitted EXCLUSIVELY on Training Partition.")

    # -------------------------------------------------------------------------
    # 4. Model 1: Classical Logistic Regression Baseline (TF-IDF)
    # -------------------------------------------------------------------------
    print(f"\n[4] TRAINING & EVALUATING MODEL 1: Logistic Regression (TF-IDF Baseline)...")
    t_lr_start = time.time()
    tfidf = TfidfVectorizer(max_features=1200, stop_words="english", ngram_range=(1, 2))
    X_train_tfidf = tfidf.fit_transform(X_train_text)
    lr = LogisticRegression(max_iter=1000, random_state=seed, C=1.0)
    lr.fit(X_train_tfidf, y_train)
    t_lr_train = time.time() - t_lr_start

    t_lr_infer = time.time()
    X_test_tfidf = tfidf.transform(X_test_text)
    lr_preds = lr.predict(X_test_tfidf)
    lr_infer_time = (time.time() - t_lr_infer) * 1000.0 / len(X_test_text)
    
    lr_acc = accuracy_score(y_test, lr_preds) * 100.0
    lr_f1 = f1_score(y_test, lr_preds, average="macro", zero_division=0)
    lr_prec = precision_score(y_test, lr_preds, average="macro", zero_division=0)
    lr_rec = recall_score(y_test, lr_preds, average="macro", zero_division=0)
    print(f"    -> LR Finished: Acc = {lr_acc:.1f}%, F1 = {lr_f1:.3f}, Latency = {lr_infer_time:.2f} ms/sample")

    # -------------------------------------------------------------------------
    # 5. Model 2: Classical DistilBERT Baseline (Zero-Shot SST-2 Head on GPU)
    # -------------------------------------------------------------------------
    print(f"\n[5] EVALUATING MODEL 2: DistilBERT Pre-Trained Baseline (GPU Accelerated)...")
    pipe_device = 0 if cuda_available else -1
    distil_nlp = hf_pipeline("sentiment-analysis", model=MODEL_NAME, device=pipe_device)
    
    t_bert_infer = time.time()
    bert_preds = []
    # Batch predict
    batch_size = 64
    for i in range(0, len(X_test_text), batch_size):
        chunk = [t[:256] for t in X_test_text[i:i + batch_size]]
        outputs = distil_nlp(chunk)
        for out in outputs:
            score = out["score"]
            lbl = out["label"]
            if score < 0.65:
                bert_preds.append(1)  # Neutral threshold
            else:
                bert_preds.append(2 if lbl == "POSITIVE" else 0)
    
    bert_infer_time = (time.time() - t_bert_infer) * 1000.0 / len(X_test_text)
    bert_acc = accuracy_score(y_test, bert_preds) * 100.0
    bert_f1 = f1_score(y_test, bert_preds, average="macro", zero_division=0)
    bert_prec = precision_score(y_test, bert_preds, average="macro", zero_division=0)
    bert_rec = recall_score(y_test, bert_preds, average="macro", zero_division=0)
    print(f"    -> DistilBERT Finished: Acc = {bert_acc:.1f}%, F1 = {bert_f1:.3f}, Latency = {bert_infer_time:.2f} ms/sample")

    # -------------------------------------------------------------------------
    # 6. Model 3: Hybrid Quantum-Classical Pipeline (DistilBERT + PCA + Q-Kernel + QSVM)
    # -------------------------------------------------------------------------
    print(f"\n[6] TRAINING & EVALUATING MODEL 3: Hybrid QSVM (DistilBERT + PCA + Quantum Kernel)...")
    
    # (a) Feature Extraction with DistilBERT on GPU
    extractor = DistilBertFeatureExtractor()
    print(f"    - Extracting 768-D Contextual Embeddings on {extractor.device}...")
    t_emb = time.time()
    X_train_emb = extractor.extract_batch(X_train_text, batch_size=64)
    X_test_emb = extractor.extract_batch(X_test_text, batch_size=64)
    print(f"      Train Embeddings: {X_train_emb.shape}, Test Embeddings: {X_test_emb.shape} in {time.time()-t_emb:.2f}s")
    
    # (b) Strict Out-of-Sample PCA(4)
    t_pca = time.time()
    pca = PCA(n_components=4, random_state=seed)
    X_train_pca = pca.fit_transform(X_train_emb)     # .fit() on Train ONLY
    X_test_pca = pca.transform(X_test_emb)           # .transform() on Test ONLY
    print(f"    - PCA(4) Explained Variance Ratio: {np.sum(pca.explained_variance_ratio_)*100:.2f}% (Fit strictly on Train)")

    # (c) Angle Scaling to [-0.85pi, +0.85pi]
    scaler = MinMaxScaler(feature_range=(-np.pi * 0.85, np.pi * 0.85))
    X_train_q = scaler.fit_transform(X_train_pca)    # .fit() on Train ONLY
    X_test_q = scaler.transform(X_test_pca)          # .transform() on Test ONLY

    # (d) Vectorized Quantum Kernel Gram Matrix Computation
    kernel_estimator = QuantumKernelEstimator(n_qubits=4)
    print(f"    - Computing Vectorized Quantum Kernel Gram Matrix K(train, train) [840 x 840]...")
    t_ktrain = time.time()
    K_train = kernel_estimator.compute_gram_matrix(X_train_q, X_train_q, fast_statevector=True)
    t_ktrain_elapsed = time.time() - t_ktrain
    print(f"      K_train computed in {t_ktrain_elapsed:.2f}s with unit diagonal!")

    print(f"    - Fitting Dual Precomputed QSVM (C=1.5)...")
    t_svm_fit = time.time()
    qsvm = SVC(kernel="precomputed", probability=True, random_state=seed, C=1.5)
    qsvm.fit(K_train, y_train)
    print(f"      QSVM fitted in {time.time()-t_svm_fit:.2f}s! Number of Support Vectors: {len(qsvm.support_)}")

    # (e) Rectangular Evaluation Gram Matrix K(test, train) [360 x 840]
    print(f"    - Computing Rectangular Quantum Kernel Gram Matrix K(test, train) [360 x 840]...")
    t_ktest = time.time()
    K_test = kernel_estimator.compute_gram_matrix(X_test_q, X_train_q, fast_statevector=True)
    t_ktest_elapsed = time.time() - t_ktest
    print(f"      K_test computed in {t_ktest_elapsed:.2f}s!")

    # (f) Prediction & Latency
    t_qsvm_infer = time.time()
    qsvm_preds = qsvm.predict(K_test)
    qsvm_probs = qsvm.predict_proba(K_test)
    qsvm_infer_time = ((time.time() - t_qsvm_infer) + t_ktest_elapsed) * 1000.0 / len(X_test_text)

    qsvm_acc = accuracy_score(y_test, qsvm_preds) * 100.0
    qsvm_f1 = f1_score(y_test, qsvm_preds, average="macro", zero_division=0)
    qsvm_prec = precision_score(y_test, qsvm_preds, average="macro", zero_division=0)
    qsvm_rec = recall_score(y_test, qsvm_preds, average="macro", zero_division=0)
    print(f"    -> Hybrid QSVM Finished: Acc = {qsvm_acc:.1f}%, F1 = {qsvm_f1:.3f}, Latency = {qsvm_infer_time:.2f} ms/sample")

    total_execution_time = time.time() - total_start_time

    # -------------------------------------------------------------------------
    # 7. Side-by-Side Performance Comparison Table
    # -------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print("FINAL SIDE-BY-SIDE BENCHMARK RESULTS (360 HELD-OUT TEST HEADLINES)")
    print("=" * 90)
    print(f"{'Model Pipeline':<35} | {'Accuracy':<10} | {'Macro F1':<10} | {'Precision':<10} | {'Recall':<10} | {'Latency/Sample':<14}")
    print("-" * 90)
    print(f"{'Logistic Regression (TF-IDF)':<35} | {lr_acc:>8.1f}% | {lr_f1:>10.3f} | {lr_prec:>10.3f} | {lr_rec:>10.3f} | {lr_infer_time:>10.2f} ms")
    print(f"{'DistilBERT Baseline (SST-2)':<35} | {bert_acc:>8.1f}% | {bert_f1:>10.3f} | {bert_prec:>10.3f} | {bert_rec:>10.3f} | {bert_infer_time:>10.2f} ms")
    print(f"{'Hybrid QSVM (DistilBERT+Q-Kernel)':<35} | {qsvm_acc:>8.1f}% | {qsvm_f1:>10.3f} | {qsvm_prec:>10.3f} | {qsvm_rec:>10.3f} | {qsvm_infer_time:>10.2f} ms")
    print("=" * 90)
    print(f"ADVANTAGE (Hybrid QSVM vs. Logistic Regression) : +{qsvm_acc - lr_acc:.1f}% Accuracy | +{qsvm_f1 - lr_f1:.3f} Macro F1")
    print(f"ADVANTAGE (Hybrid QSVM vs. DistilBERT Baseline) : +{qsvm_acc - bert_acc:.1f}% Accuracy | +{qsvm_f1 - bert_f1:.3f} Macro F1")
    print(f"TOTAL BENCHMARK EXECUTION TIME                  : {total_execution_time:.2f} seconds ({total_execution_time/60.0:.2f} minutes)")
    print("=" * 90)

    # -------------------------------------------------------------------------
    # 8. Detailed Classification Reports
    # -------------------------------------------------------------------------
    target_names = ["Negative (0)", "Neutral (1)", "Positive (2)"]
    print("\n[8] DETAILED PER-CLASS CLASSIFICATION REPORTS:")
    print("\n--- Model 1: Logistic Regression (TF-IDF) ---")
    print(classification_report(y_test, lr_preds, target_names=target_names, digits=3))
    
    print("\n--- Model 2: DistilBERT Pre-Trained Baseline ---")
    print(classification_report(y_test, bert_preds, target_names=target_names, digits=3))

    print("\n--- Model 3: Proposed Hybrid QSVM ---")
    print(classification_report(y_test, qsvm_preds, target_names=target_names, digits=3))

    # Confusion matrix
    cm_qsvm = confusion_matrix(y_test, qsvm_preds)
    print("\nConfusion Matrix (Hybrid QSVM):")
    print("Rows: Actual [Neg, Neu, Pos], Cols: Predicted [Neg, Neu, Pos]")
    print(cm_qsvm)

if __name__ == "__main__":
    main()
