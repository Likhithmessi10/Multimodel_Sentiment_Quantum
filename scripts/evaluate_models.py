import os
import sys
import time
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.quantum.quantum_features import QuantumFeaturePipeline
from src.quantum.quantum_vqc import VariationalQuantumClassifier
from src.models.distilbert_model import DistilBertSentimentClassifier

def run_evaluation():
    print("=" * 75)
    print("EVALUATION & COMPARATIVE BENCHMARK: QUANTUM VS. CLASSICAL")
    print("=" * 75)
    
    test_file = os.path.join(project_root, "data", "processed", "test.csv")
    df_test = pd.read_csv(test_file)
    
    pos_test = df_test[df_test['label'] == 1]
    neg_test = df_test[df_test['label'] == 0]
    
    # 100 test samples (50 Pos, 50 Neg) for identical, rigorous comparison across all models
    n_eval = 50
    test_sub = pd.concat([
        pos_test.sample(n=n_eval, random_state=42),
        neg_test.sample(n=n_eval, random_state=42)
    ]).sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    text_col = 'cleaned_review' if 'cleaned_review' in df_test.columns else 'review'
    test_texts = test_sub[text_col].tolist()
    y_true = test_sub['label'].to_numpy(dtype=int)
    
    print(f"[*] Evaluating on {len(test_sub)} test samples (50 Pos, 50 Neg)...")
    
    # -------------------------------------------------------------
    # 1. Load Pretrained Artifacts
    # -------------------------------------------------------------
    # Quantum pipeline & VQC
    pipeline_path = os.path.join(project_root, "models", "quantum", "quantum_feature_pipeline.joblib")
    vqc_path = os.path.join(project_root, "models", "quantum", "vqc_weights.joblib")
    
    q_pipeline = QuantumFeaturePipeline.load(pipeline_path)
    vqc = VariationalQuantumClassifier.load(vqc_path)
    
    # Transform test set to 4 features
    X_test_q = q_pipeline.transform(test_texts)
    
    # Classical Logistic Regression (Original Full TF-IDF)
    lr_orig_path = os.path.join(project_root, "models", "logistic_regression.joblib")
    tfidf_orig_path = os.path.join(project_root, "models", "tfidf_vectorizer.joblib")
    
    has_orig_lr = os.path.exists(lr_orig_path) and os.path.exists(tfidf_orig_path)
    if has_orig_lr:
        lr_orig = joblib.load(lr_orig_path)
        tfidf_orig = joblib.load(tfidf_orig_path)
        X_test_tfidf = tfidf_orig.transform(test_texts)
    
    # Classical Logistic Regression on the SAME 4 SVD Features (Direct Fair Baseline)
    from sklearn.linear_model import LogisticRegression
    # Fit on training data with 4 features to compare directly
    train_file = os.path.join(project_root, "data", "processed", "train.csv")
    df_train = pd.read_csv(train_file)
    train_sub = pd.concat([
        df_train[df_train['label'] == 1].sample(n=100, random_state=42),
        df_train[df_train['label'] == 0].sample(n=100, random_state=42)
    ]).reset_index(drop=True)
    
    X_train_q = q_pipeline.transform(train_sub[text_col].tolist())
    y_train = train_sub['label'].to_numpy(dtype=int)
    
    lr_4feat = LogisticRegression(random_state=42)
    lr_4feat.fit(X_train_q, y_train)
    
    # DistilBERT
    distilbert = DistilBertSentimentClassifier()
    
    # -------------------------------------------------------------
    # 2. Benchmark Each Model
    # -------------------------------------------------------------
    results = {}
    conf_matrices = {}
    
    # (A) Variational Quantum Classifier (VQC)
    print("\n[*] Benchmarking Model: Variational Quantum Classifier (4-Qubit VQC)...")
    t0 = time.time()
    vqc_probs = vqc.predict_proba(X_test_q)
    vqc_total_time = (time.time() - t0) * 1000.0
    vqc_latency = vqc_total_time / len(X_test_q)
    vqc_preds = (vqc_probs >= 0.5).astype(int)
    
    results["Variational Quantum Classifier (VQC)"] = {
        "Accuracy (%)": round(accuracy_score(y_true, vqc_preds) * 100.0, 2),
        "Precision (%)": round(precision_score(y_true, vqc_preds, zero_division=0) * 100.0, 2),
        "Recall (%)": round(recall_score(y_true, vqc_preds, zero_division=0) * 100.0, 2),
        "F1-Score": round(f1_score(y_true, vqc_preds, zero_division=0), 4),
        "ROC-AUC": round(roc_auc_score(y_true, vqc_probs), 4),
        "Latency (ms/sample)": round(vqc_latency, 2),
        "Features Used": "4 SVD Components (Angle Encoded)",
        "Hardware Mode": "CPU Quantum Simulator (default.qubit)"
    }
    conf_matrices["Variational Quantum Classifier (VQC)"] = confusion_matrix(y_true, vqc_preds).tolist()
    
    # (B) Classical Logistic Regression on Fair 4-Feature Input
    print("[*] Benchmarking Model: Logistic Regression (4-Feature Classical Baseline)...")
    t0 = time.time()
    lr4_probs = lr_4feat.predict_proba(X_test_q)[:, 1]
    lr4_total_time = (time.time() - t0) * 1000.0
    lr4_latency = lr4_total_time / len(X_test_q)
    lr4_preds = lr_4feat.predict(X_test_q)
    
    results["Logistic Regression (4-Feature Classical Baseline)"] = {
        "Accuracy (%)": round(accuracy_score(y_true, lr4_preds) * 100.0, 2),
        "Precision (%)": round(precision_score(y_true, lr4_preds, zero_division=0) * 100.0, 2),
        "Recall (%)": round(recall_score(y_true, lr4_preds, zero_division=0) * 100.0, 2),
        "F1-Score": round(f1_score(y_true, lr4_preds, zero_division=0), 4),
        "ROC-AUC": round(roc_auc_score(y_true, lr4_probs), 4),
        "Latency (ms/sample)": round(lr4_latency, 2),
        "Features Used": "Same 4 SVD Components (Direct Classical Control)",
        "Hardware Mode": "Standard CPU Linear Classifier"
    }
    conf_matrices["Logistic Regression (4-Feature Classical Baseline)"] = confusion_matrix(y_true, lr4_preds).tolist()
    
    # (C) Full Logistic Regression (TF-IDF 5000 features)
    if has_orig_lr:
        print("[*] Benchmarking Model: Logistic Regression (Full TF-IDF 5000 features)...")
        t0 = time.time()
        lrf_probs = lr_orig.predict_proba(X_test_tfidf)[:, 1]
        lrf_total_time = (time.time() - t0) * 1000.0
        lrf_latency = lrf_total_time / len(test_texts)
        lrf_preds = lr_orig.predict(X_test_tfidf)
        
        results["Logistic Regression (Full TF-IDF 5000 features)"] = {
            "Accuracy (%)": round(accuracy_score(y_true, lrf_preds) * 100.0, 2),
            "Precision (%)": round(precision_score(y_true, lrf_preds, zero_division=0) * 100.0, 2),
            "Recall (%)": round(recall_score(y_true, lrf_preds, zero_division=0) * 100.0, 2),
            "F1-Score": round(f1_score(y_true, lrf_preds, zero_division=0), 4),
            "ROC-AUC": round(roc_auc_score(y_true, lrf_probs), 4),
            "Latency (ms/sample)": round(lrf_latency, 2),
            "Features Used": "Full TF-IDF Sparse Matrix (5,000 features)",
            "Hardware Mode": "Standard CPU Linear Classifier"
        }
        conf_matrices["Logistic Regression (Full TF-IDF 5000 features)"] = confusion_matrix(y_true, lrf_preds).tolist()
    
    # (D) DistilBERT Transformer
    print("[*] Benchmarking Model: DistilBERT Transformer...")
    bert_preds = []
    bert_probs = []
    t0 = time.time()
    for txt in test_texts:
        out = distilbert.predict_single(txt)
        bert_preds.append(out["class_id"])
        bert_probs.append(out["positive_probability"])
    bert_total_time = (time.time() - t0) * 1000.0
    bert_latency = bert_total_time / len(test_texts)
    
    results["DistilBERT Transformer"] = {
        "Accuracy (%)": round(accuracy_score(y_true, bert_preds) * 100.0, 2),
        "Precision (%)": round(precision_score(y_true, bert_preds, zero_division=0) * 100.0, 2),
        "Recall (%)": round(recall_score(y_true, bert_preds, zero_division=0) * 100.0, 2),
        "F1-Score": round(f1_score(y_true, bert_preds, zero_division=0), 4),
        "ROC-AUC": round(roc_auc_score(y_true, bert_probs), 4),
        "Latency (ms/sample)": round(bert_latency, 2),
        "Features Used": "Full Bidirectional Self-Attention Context",
        "Hardware Mode": "6-Layer Distilled Transformer on CPU"
    }
    conf_matrices["DistilBERT Transformer"] = confusion_matrix(y_true, bert_preds).tolist()
    
    # -------------------------------------------------------------
    # 3. Print Results Table
    # -------------------------------------------------------------
    print("\n" + "=" * 90)
    print(f"{'Model Architecture':<42} | {'Accuracy':<10} | {'F1-Score':<8} | {'ROC-AUC':<8} | {'Latency (ms)':<12}")
    print("-" * 90)
    for model_name, m in results.items():
        print(f"{model_name:<42} | {m['Accuracy (%)']:>8.2f}% | {m['F1-Score']:>8.4f} | {m['ROC-AUC']:>8.4f} | {m['Latency (ms/sample)']:>10.2f} ms")
    print("=" * 90)
    
    # -------------------------------------------------------------
    # 4. Save JSON & CSV Results
    # -------------------------------------------------------------
    metrics_json_path = os.path.join(project_root, "results", "metrics", "quantum_model_comparison.json")
    os.makedirs(os.path.dirname(metrics_json_path), exist_ok=True)
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "evaluation_samples": len(test_sub),
            "results": results,
            "confusion_matrices": conf_matrices
        }, f, indent=2)
    print(f"\n[+] Saved metrics JSON to {metrics_json_path}")
    
    # CSV Table
    df_results = pd.DataFrame.from_dict(results, orient='index')
    csv_path = os.path.join(project_root, "results", "metrics", "quantum_model_comparison.csv")
    df_results.to_csv(csv_path)
    print(f"[+] Saved comparison CSV to {csv_path}")
    
    # -------------------------------------------------------------
    # 5. Generate Publication-Quality Plots
    # -------------------------------------------------------------
    fig_dir = os.path.join(project_root, "results", "figures")
    os.makedirs(fig_dir, exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=300)
    
    # (a) Accuracy & F1 Bar Chart
    models_short = ["VQC (4-Qubit)", "LR (4-Feat)", "LR (Full TF-IDF)", "DistilBERT"]
    acc_vals = [
        results["Variational Quantum Classifier (VQC)"]["Accuracy (%)"],
        results["Logistic Regression (4-Feature Classical Baseline)"]["Accuracy (%)"],
        results.get("Logistic Regression (Full TF-IDF 5000 features)", {}).get("Accuracy (%)", 0.0),
        results["DistilBERT Transformer"]["Accuracy (%)"]
    ]
    f1_vals = [
        results["Variational Quantum Classifier (VQC)"]["F1-Score"] * 100.0,
        results["Logistic Regression (4-Feature Classical Baseline)"]["F1-Score"] * 100.0,
        results.get("Logistic Regression (Full TF-IDF 5000 features)", {}).get("F1-Score", 0.0) * 100.0,
        results["DistilBERT Transformer"]["F1-Score"] * 100.0
    ]
    
    x = np.arange(len(models_short))
    width = 0.35
    
    r1 = ax1.bar(x - width/2, acc_vals, width, label='Accuracy (%)', color='#7C3AED')
    r2 = ax1.bar(x + width/2, f1_vals, width, label='F1-Score (x100)', color='#059669')
    
    ax1.set_ylabel('Score (%)', fontweight='bold')
    ax1.set_title('(a) Accuracy & F1 Comparison (Test Set)', fontweight='bold', fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(models_short, rotation=15, ha='right', fontsize=9)
    ax1.set_ylim(0, 105)
    ax1.legend(loc='lower right', fontsize=8)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    
    for r in r1:
        h = r.get_height()
        ax1.annotate(f"{h:.1f}%", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 2),
                     textcoords='offset points', ha='center', va='bottom', fontsize=7.5, weight='bold')
    
    # (b) Latency Comparison (Log scale)
    latencies = [
        results["Variational Quantum Classifier (VQC)"]["Latency (ms/sample)"],
        results["Logistic Regression (4-Feature Classical Baseline)"]["Latency (ms/sample)"],
        results.get("Logistic Regression (Full TF-IDF 5000 features)", {}).get("Latency (ms/sample)", 0.01),
        results["DistilBERT Transformer"]["Latency (ms/sample)"]
    ]
    colors = ['#7C3AED', '#3B82F6', '#2563EB', '#10B981']
    bars = ax2.bar(models_short, latencies, color=colors, width=0.5, edgecolor='#334155')
    ax2.set_ylabel('Inference Latency (ms / sample) [Log Scale]', fontweight='bold')
    ax2.set_title('(b) Inference Latency (CPU Execution)', fontweight='bold', fontsize=11)
    ax2.set_yscale('log')
    ax2.set_xticklabels(models_short, rotation=15, ha='right', fontsize=9)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    
    for b in bars:
        h = b.get_height()
        ax2.annotate(f"{h:.2f} ms", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                     textcoords='offset points', ha='center', va='bottom', fontsize=8, weight='bold')
    
    plt.tight_layout()
    comp_plot_path = os.path.join(fig_dir, "quantum_vs_classical_comparison.png")
    plt.savefig(comp_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Saved comparison figure to {comp_plot_path}")

if __name__ == "__main__":
    run_evaluation()
