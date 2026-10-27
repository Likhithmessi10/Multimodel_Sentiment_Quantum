import os
import sys
import time
import json
import numpy as np
import pandas as pd

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ensure src is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.quantum.quantum_features import QuantumFeaturePipeline
from src.quantum.quantum_vqc import VariationalQuantumClassifier

def run_quantum_training():
    print("=" * 70)
    print("Quantum Machine Learning Training — Variational Quantum Classifier (VQC)")
    print("=" * 70)
    
    data_dir = os.path.join(project_root, "data", "processed")
    train_file = os.path.join(data_dir, "train.csv")
    val_file = os.path.join(data_dir, "val.csv")
    
    if not os.path.exists(train_file):
        raise FileNotFoundError(f"Training data not found at {train_file}")
    
    print(f"[*] Loading training data from {train_file}...")
    df_train = pd.read_csv(train_file)
    df_val = pd.read_csv(val_file)
    
    pos_train = df_train[df_train['label'] == 1]
    neg_train = df_train[df_train['label'] == 0]
    
    # 200 train samples (100 Pos, 100 Neg) and 60 val samples for fast, clean CPU simulation (~45s)
    n_train_subset = 100
    n_val_subset = 30
    
    train_sub = pd.concat([
        pos_train.sample(n=n_train_subset, random_state=42),
        neg_train.sample(n=n_train_subset, random_state=42)
    ]).sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    pos_val = df_val[df_val['label'] == 1]
    neg_val = df_val[df_val['label'] == 0]
    val_sub = pd.concat([
        pos_val.sample(n=n_val_subset, random_state=42),
        neg_val.sample(n=n_val_subset, random_state=42)
    ]).sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    print(f"[+] Selected stratified training subset: {len(train_sub)} samples (50:50 balanced)")
    print(f"[+] Selected validation subset: {len(val_sub)} samples (50:50 balanced)")
    
    text_col = 'cleaned_review' if 'cleaned_review' in df_train.columns else 'review'
    
    # 1. Classical Feature Extraction Pipeline
    pipeline = QuantumFeaturePipeline(n_components=4, max_features=5000, random_state=42)
    pipeline.fit(train_sub[text_col].tolist())
    
    X_train_q = pipeline.transform(train_sub[text_col].tolist())
    y_train = train_sub['label'].to_numpy(dtype=int)
    
    X_val_q = pipeline.transform(val_sub[text_col].tolist())
    y_val = val_sub['label'].to_numpy(dtype=int)
    
    pipeline_path = os.path.join(project_root, "models", "quantum", "quantum_feature_pipeline.joblib")
    pipeline.save(pipeline_path)
    
    # 2. Initialize and Train VQC
    vqc = VariationalQuantumClassifier(n_qubits=4, n_layers=2, learning_rate=0.08, random_state=42)
    
    circuit_ascii = vqc.get_circuit_ascii()
    print("\n--- 4-Qubit Quantum Circuit Architecture ---")
    safe_ascii = circuit_ascii.encode('ascii', errors='replace').decode('ascii')
    print(safe_ascii)
    print("--------------------------------------------\n")
    
    circuit_txt_path = os.path.join(project_root, "models", "quantum", "quantum_circuit_diagram.txt")
    with open(circuit_txt_path, "w", encoding="utf-8") as f:
        f.write(circuit_ascii)
    print(f"[+] Saved circuit diagram to {circuit_txt_path}")
    
    # Train
    t0 = time.time()
    vqc.fit(X_train_q, y_train, epochs=12, batch_size=25, validation_data=(X_val_q, y_val))
    train_duration = time.time() - t0
    
    vqc_path = os.path.join(project_root, "models", "quantum", "vqc_weights.joblib")
    vqc.save(vqc_path)
    
    val_probs = vqc.predict_proba(X_val_q)
    val_preds = (val_probs >= 0.5).astype(int)
    val_acc = np.mean(val_preds == y_val) * 100.0
    
    print("\n" + "=" * 70)
    print(f"TRAINING COMPLETE | Time: {train_duration:.2f}s | Final Val Accuracy: {val_acc:.2f}%")
    print("=" * 70)
    
    metrics = {
        "model": "VariationalQuantumClassifier",
        "n_qubits": 4,
        "n_layers": 2,
        "simulator": "default.qubit",
        "train_samples": len(train_sub),
        "val_samples": len(val_sub),
        "train_duration_sec": round(train_duration, 2),
        "final_val_accuracy": round(val_acc, 2),
        "history": vqc.training_history
    }
    metrics_path = os.path.join(project_root, "results", "metrics", "quantum_training_metrics.json")
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"[+] Saved training metrics to {metrics_path}")

if __name__ == "__main__":
    run_quantum_training()
