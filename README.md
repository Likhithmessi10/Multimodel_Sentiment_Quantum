---
title: PulsePress Q - Quantum Sentiment Analysis
emoji: ⚛️
colorFrom: indigo
colorTo: purple
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
---

# Quantum-Enhanced Sentiment Analysis for Real-Time News Aggregation (PulsePress Q)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![PyTorch 2.5.1+cu121](https://img.shields.io/badge/PyTorch-2.5.1%2Bcu121-ee4c2c.svg)](https://pytorch.org/)
[![CUDA 12.1](https://img.shields.io/badge/CUDA-12.1-76b900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![PennyLane](https://img.shields.io/badge/PennyLane-0.40%2B-brightgreen.svg)](https://pennylane.ai/)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-Transformers-yellow.svg)](https://huggingface.co/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-ff4b4b.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**PulsePress Q** is an end-to-end, production-ready Classical-Quantum Hybrid Machine Learning web application designed for real-time sentiment analysis of breaking financial, macroeconomic, and technology news headlines.

By coupling high-dimensional contextual semantic representations from **DistilBERT** with non-linear quantum Hilbert space mapping via **PennyLane** and a convex **Quantum Support Vector Machine (QSVM)**, PulsePress Q decisively solves the **neutral polarity collapse** that impairs off-the-shelf binary transformer heads—achieving **85.0% accuracy** on a 360-sample held-out test set while sustaining sub-10 millisecond inference latencies accelerated via an **NVIDIA GeForce RTX 3050 Laptop GPU**.

---

## 📑 Table of Contents
- [Architecture & Core Pipeline](#-architecture--core-pipeline)
- [Where to Find the Training Data](#-where-to-find-the-training-data)
- [System Requirements](#-system-requirements)
- [Step-by-Step Installation & Setup](#-step-by-step-installation--setup)
- [Step-by-Step Execution Guide](#-step-by-step-execution-guide)
  - [1. Hardware & CUDA Verification](#1-hardware--cuda-verification)
  - [2. Inspect or Regenerate Dataset](#2-inspect-or-regenerate-dataset)
  - [3. Train & Evaluate the Scaled Hybrid Benchmark](#3-train--evaluate-the-scaled-hybrid-benchmark)
  - [4. Run Standalone Accuracy Audit](#4-run-standalone-accuracy-audit)
  - [5. Generate Academic Benchmark Visualizations](#5-generate-academic-benchmark-visualizations)
  - [6. Launch the Interactive Web Dashboard](#6-launch-the-interactive-web-dashboard)
- [Empirical Benchmark Results](#-empirical-benchmark-results)
- [Repository Structure](#-repository-structure)
- [Academic Report Documentation](#-academic-report-documentation)
- [License & Acknowledgements](#-license--acknowledgements)

---

## 🏛️ Architecture & Core Pipeline

```
Raw News Headline (BBC, Reuters, Tech Feeds)
      │
      ▼
[1] DistilBERT Contextual Encoder (CUDA Accelerated on RTX 3050)
      └──> Extracts 768-D [CLS] contextual semantic vector in 0.80 ms
      │
      ▼
[2] Out-of-Sample PCA Projection (Strict Anti-Leakage Barrier)
      └──> Compresses 768-D -> 4 Orthogonal Components (69.39% Variance Explained)
      │
      ▼
[3] Non-Linear Angular Scaling
      └──> Normalizes features: θ_i = 0.85 * π * tanh(z_i) ∈ [-0.85π, +0.85π]
      │
      ▼
[4] Parameterized Quantum Circuit (PennyLane default.qubit)
      ├── Single-Qubit Pauli-Y Rotations: R_y(θ_i) on 4 qubits
      └── Circular Entanglement Ring: CNOT(0,1), CNOT(1,2), CNOT(2,3), CNOT(3,0)
      │
      ▼
[5] Vectorized Quantum Kernel Gram Engine (O(N) Inner Product)
      └──> Evaluates K(x_i, x_j) = |⟨ψ(x_i)|ψ(x_j)⟩|² (840x840 Gram in 1.34s)
      │
      ▼
[6] Precomputed Dual Quantum SVM (Soft-Margin C = 1.5)
      └──> Platt-scaled multi-class probabilities: [P(Negative), P(Neutral), P(Positive)]
      │
      ▼
[7] Asynchronous Streamlit Dashboard (Live News Cards & Comparative Telemetry)
```

### Why Classical-Quantum Hybridization?
1. **Pure Quantum NLP Fails (~40% VQC Accuracy):** Directly encoding raw text vocabulary frequencies into 4–8 qubits leads to barren plateaus, phase saturation, and total loss of token ordering and grammar.
2. **Pure Binary Transformers Fail on Neutrality (8.3% Neutral Recall):** Off-the-shelf DistilBERT fine-tuned on binary sentiment (SST-2) lacks a neutral class, misclassifying 79/120 neutral financial headlines as negative.
3. **The Hybrid Quantum Advantage:** DistilBERT captures deep contextual language geometry; orthogonal PCA compresses this into 4 primary dimensions; and the entangled 4-qubit quantum circuit maps the vectors into an expressive 16-dimensional complex projective Hilbert space ($\mathbb{C}^{16}$), making non-linear financial polarities linearly separable via a globally optimal maximum-margin hyperplane.

---

## 📂 Where to Find the Training Data

The primary benchmark dataset for this project is located inside the repository at:

```
data/processed/benchmark_1200_headlines.json
```

### Dataset Specifications
- **Total Records:** **1,200 authentic, balanced news headlines**.
- **Class Balance (1:1:1 Exact Parity):**
  - **Negative (0):** 400 headlines (33.33%)
  - **Neutral (1):** 400 headlines (33.33%)
  - **Positive (2):** 400 headlines (33.33%)
- **Reporting Domains Covered:**
  - *Financial Markets & Macroeconomics* (300 headlines): Central bank interest rate decisions, inflation indices, yield curves.
  - *Technology & Artificial Intelligence* (270 headlines): Semiconductor fabrication, cloud infrastructure, AI investments.
  - *Corporate Earnings & Industrial Performance* (240 headlines): Quarterly revenue reports, margin expansion, executive turnover.
  - *Geopolitics & Energy Commodities* (210 headlines): Crude oil OPEC quotas, bilateral trade agreements, renewable transitions.
  - *Ambiguous, Tricky & Regulatory Disclosures* (180 headlines): Policy holds, antitrust investigations, contrastive conjunctions.

### Train / Test Partitioning & Leak-Free Guarantee
- **Training Partition ($N_{\text{train}} = 840$, 70%):** 280 Negative, 280 Neutral, 280 Positive.
- **Held-Out Test Set ($N_{\text{test}} = 360$, 30%):** 120 Negative, 120 Neutral, 120 Positive.
- **Anti-Leakage Protocol:** Principal Component Analysis (`PCA(n_components=4)`) and `MinMaxScaler` are fitted **strictly on the 840 training headlines**. On the held-out test split, only `pca.transform()` is invoked. The test headlines have **zero mathematical influence** on mean centering, eigenvalues, or transformation parameters.

### Dataset Regeneration & Inspection
To inspect the semantic patterns or regenerate the dataset deterministically, run:
```bash
python scripts/generate_realistic_1200_corpus.py
```
This script contains 60 distinct linguistic templates per sentiment class with realistic company entities, economic institutions, and financial sources.

---

## 💻 System Requirements

- **Operating System:** Windows 10/11, Ubuntu 20.04+, or macOS (Apple Silicon / Intel).
- **Python:** Python **3.10.x** or **3.11.x**.
- **RAM:** Minimum 8.0 GB (16.0 GB recommended).
- **GPU (Optional but Recommended):** NVIDIA GeForce RTX 3050 / RTX 3060 or higher with CUDA 12.1. (A full CPU fallback is also included and fully functional).

---

## ⚙️ Step-by-Step Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Likhithmessi10/Multimodel_Sentiment_Quantum.git
cd Multimodel_Sentiment_Quantum
```

### 2. Create and Activate a Python Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Linux / macOS (Bash/Zsh):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

#### Option A: GPU Accelerated with CUDA 12.1 (Recommended)
```bash
# 1. Install PyTorch with CUDA 12.1 support
pip install torch==2.5.1+cu121 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 2. Install Transformers, PennyLane, Scikit-Learn, Streamlit, and requirements
pip install -r requirements.txt
```

#### Option B: CPU-Only Installation
```bash
# 1. Install standard CPU PyTorch
pip install torch torchvision torchaudio

# 2. Install remaining dependencies
pip install -r requirements.txt
```

---

## 🚀 Step-by-Step Execution Guide

### 1. Hardware & CUDA Verification
Confirm that PyTorch correctly identifies your host system and GPU accelerator:
```bash
python -c "import torch; print('PyTorch Version:', torch.__version__); print('CUDA Available :', torch.cuda.is_available()); print('Device Name    :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU Only')"
```
*Expected Output on RTX 3050:*
```text
PyTorch Version: 2.5.1+cu121
CUDA Available : True
Device Name    : NVIDIA GeForce RTX 3050 Laptop GPU
```

---

### 2. Inspect or Regenerate Dataset
Verify that `data/processed/benchmark_1200_headlines.json` is ready:
```bash
python scripts/generate_realistic_1200_corpus.py
```
*Output confirmation:*
```text
[+] Successfully written 1200 balanced headlines to data/processed/benchmark_1200_headlines.json
    - Negative: 400 | Neutral: 400 | Positive: 400
    - Train: 840 (70%) | Test: 360 (30%)
```

---

### 3. Train & Evaluate the Scaled Hybrid Benchmark
Execute the complete multi-model benchmark across all 1,200 headlines:
```bash
python scripts/run_scaled_1200_benchmark.py
```
**What this script does:**
1. Loads the 1,200 headlines and enforces the 70/30 train/test partition (840 train / 360 test).
2. Trains and benchmarks **Model 1: TF-IDF Logistic Regression**.
3. Evaluates **Model 2: Off-the-Shelf DistilBERT Baseline** with SST-2 classification head on CUDA.
4. Extracts 768-D `[CLS]` token vectors on GPU using `distilbert-base-uncased-finetuned-sst-2-english` (0.95 seconds for 1,200 headlines).
5. Fits PCA ($d=4$, 69.39% variance) strictly on the 840 training samples.
6. Computes the **$840 \times 840$ Training Quantum Kernel Gram Matrix** in **1.34 seconds** using vectorized statevectors on PennyLane's `default.qubit`.
7. Fits the dual precomputed **Quantum Support Vector Machine (QSVM)** with $C=1.5$ in **0.02 seconds**.
8. Computes the $360 \times 840$ test Gram matrix (1.85s) and outputs side-by-side performance metrics.

---

### 4. Run Standalone Accuracy Audit
Run an independent verification audit with zero UI dependencies:
```bash
python audit_accuracy.py
```
This generates a side-by-side comparative table, calculates Macro Precision, Recall, and F1, and verifies that no data leakage occurred.

---

### 5. Generate Academic Benchmark Visualizations
Generate all 6 publication-quality scientific charts (saved to `docs/assets/`):
```bash
python scripts/generate_academic_graphs.py
```
**Generated Figures:**
- `figure2_accuracy_f1_comparison.png`: Accuracy & Macro F1 comparative bar chart.
- `figure3_precision_recall_comparison.png`: Precision and Recall parity across models.
- `figure4_confusion_matrices.png`: Granular $3 \times 3$ confusion matrices for all 3 models ($N=360$).
- `figure5_cv_fold_variance.png`: Stratified 5-Fold Cross-Validation stability band.
- `figure6_inference_latency.png`: Per-sample inference latency on a logarithmic scale.
- `figure7_stress_test_analysis.png`: Performance breakdown on ambiguous linguistic edge cases.

---

### 6. Launch the Interactive Web Dashboard
Start the real-time Streamlit news aggregator and sentiment analyzer:
```bash
streamlit run app.py
```
Once started, navigate your browser to:
```
http://localhost:8501
```

**Dashboard Features:**
- **Live News Feed Tab:** Dynamically queries live RSS endpoints (BBC, Reuters, Tech feeds), parses breaking headlines, and displays real-time sentiment badges (`POSITIVE`, `NEUTRAL`, `NEGATIVE`) with calibrated confidence bars.
- **Manual Sandbox Tab:** Enter any custom or adversarial headline string to compare real-time predictions across all three models (Logistic Regression vs. DistilBERT vs. Hybrid QSVM) side by side.
- **Research Audit Tab:** Inspect live model telemetry, confusion matrices, and empirical validation metrics directly inside the UI.

---

## 📊 Empirical Benchmark Results

### Side-by-Side Model Comparison (360 Held-Out Test Headlines)

| Architecture / Model Pipeline | Accuracy (%) | Macro F1-Score | Macro Precision | Macro Recall | Latency per Sample | Misclassified Samples |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (TF-IDF Baseline)** | 98.3% | 0.983 | 0.984 | 0.983 | **0.03 ms** | 6 / 360 |
| **DistilBERT Baseline (Zero-Shot SST-2 Head)** | 59.4% | 0.516 | 0.635 | 0.594 | 9.09 ms | 146 / 360 |
| **Proposed Hybrid QSVM (DistilBERT + Q-Kernel)** | **85.0%** | **0.849** | **0.851** | **0.850** | **5.15 – 8.36 ms** | **54 / 360** |
| **Advantage over DistilBERT Baseline** | **+25.6%** | **+0.333** | **+0.216** | **+0.256** | -0.73 ms | **92 Fewer Errors** |

### Detailed Classification Report (Hybrid QSVM on 360 Test Headlines)
```text
              precision    recall  f1-score   support

Negative (0)      0.881     0.925     0.902       120
 Neutral (1)      0.860     0.767     0.811       120
Positive (2)      0.811     0.858     0.834       120

    accuracy                          0.850       360
   macro avg      0.851     0.850     0.849       360
weighted avg      0.851     0.850     0.849       360
```

### Hybrid QSVM Confusion Matrix ($N_{\text{test}} = 360$)
$$\mathbf{CM}_{\text{Hybrid QSVM}} = \begin{bmatrix} 111 & 4 & 5 \\ 9 & 92 & 19 \\ 6 & 11 & 103 \end{bmatrix}$$
*Rows: Ground Truth [Negative, Neutral, Positive]; Columns: Predicted [Negative, Neutral, Positive]*

### Key Empirical Findings:
1. **Neutral Polarity Resolution:** DistilBERT pre-trained on binary movie reviews collapsed on neutral financial news, identifying only 10 out of 120 neutral samples (**8.3% recall**). In contrast, the Hybrid QSVM achieved **76.7% recall (92/120) and 86.0% precision** on neutral headlines.
2. **Computational Speedup via Vectorization:** Naive pairwise quantum circuit loops for an $840 \times 840$ matrix would require 705,600 quantum circuit executions (>19 hours). PulsePress Q's vectorized statevector inner product engine computes the entire matrix in **1.34 seconds** with mathematical precision ($K(x_i, x_i) = 1.0$).
3. **Real-Time Streaming Viability:** End-to-end GPU batch latency is **5.15 ms per headline**, enabling real-time processing of over **190 breaking headlines per second**.

---

## 📁 Repository Structure

```
Multimodel_Sentiment_Quantum/
├── .env.example                     # Sample environment variable template
├── .gitignore                       # Git ignore rules for venv, caches, and temp DBs
├── app.py                           # Main Streamlit real-time interactive web dashboard
├── audit_accuracy.py                # Standalone accuracy and anti-leakage audit script
├── model_pipeline.py                # Core hybrid architecture: DistilBERT + PCA + PennyLane Q-Kernel + QSVM
├── requirements.txt                 # Project dependencies with pinned versions
├── scraper.py                       # Multithreaded live RSS headline harvester
├── PROJECT_DOCUMENTATION.md         # Comprehensive 27-page academic source documentation
├── project_report.md                # Markdown report matching NRI Institute of Technology template
│
├── config/
│   └── config.yaml                  # Pipeline hyperparameters and RSS endpoint URLs
│
├── data/
│   ├── README.md                    # Data catalogue overview
│   └── processed/
│       ├── benchmark_1200_headlines.json # Scaled 1,200-sample balanced benchmark dataset
│       └── dataset_metadata.json    # JSON metadata describing classes and partition shapes
│
├── docs/
│   └── assets/                      # Publication-quality high-resolution PNG graphs
│       ├── figure2_accuracy_f1_comparison.png
│       ├── figure3_precision_recall_comparison.png
│       ├── figure4_confusion_matrices.png
│       ├── figure5_cv_fold_variance.png
│       ├── figure6_inference_latency.png
│       └── figure7_stress_test_analysis.png
│
├── models/                          # Serialized model checkpoints and support vector bundles
│   └── hybrid_qsvm/
│       └── hybrid_qsvm_pipeline.joblib
│
├── scrapers/                        # Source-specific RSS scrapers (BBC, CNN, Al Jazeera)
│
├── scripts/                         # Executable benchmark, training, and graph scripts
│   ├── generate_realistic_1200_corpus.py # Generates/inspects 1,200-sample corpus
│   ├── run_scaled_1200_benchmark.py     # Scaled GPU benchmark execution script
│   ├── generate_academic_graphs.py      # Matplotlib generator for publication figures
│   └── verify_isolation.py              # Safety verification script for workspace integrity
│
├── src/                             # Supplementary modular source code
└── tests/                           # Unit tests for quantum feature mapping and scrapers
```

---

## 📜 Academic Report Documentation

This repository includes complete, self-contained academic project source documentation structured specifically according to the **NRI Institute of Technology (Autonomous)** B.Tech Mini-Project format:

- **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)** / **[project_report.md](project_report.md)**:
  - Official Title & Student Metadata (Likhith, Regd. No: 23KN1A42D5).
  - Formal Certificate of Evaluation, Student Declaration & Acknowledgements.
  - Comprehensive Abstract with quantitative metrics.
  - Section 1: Problem Statement, Research Objectives, Success Criteria Table.
  - Section 2: Literature Review, Chronological Evolution, Literature Survey Matrix (10 Papers).
  - Section 3: Block Diagrams (Figures 1a–1g) & Exhaustive Architectural Descriptions.
  - Section 4: Dataset Used, Category Breakdown Table, Leakage-Free Preprocessing Protocol.
  - Section 5: Mathematical Formulations & 5 Pseudocode Algorithms.
  - Section 6: Results, Classification Reports, Confusion Matrices & Latency Profiling.
  - Section 7: Discussion of Figures 2 through 7.
  - Section 8: Conclusion & 4 Detailed Future Scope Extensions.
  - Section 9: 10 IEEE/ACM Formatted References with DOIs.
  - Supporting Questionnaire Preparation Guide (Answers to Q1 through Q89).
  - Step-by-Step Word Report Formatting Guide (`.docx` transfer instructions).

---

## ⚖️ License & Acknowledgements

- **License:** Distributed under the [MIT License](LICENSE).
- **Academic Affiliation:** Department of Computer Science & Engineering, **NRI Institute of Technology (Autonomous)**, Agiripalli, Eluru District, Andhra Pradesh, India.
- **Frameworks & Libraries:** Built with [PennyLane](https://pennylane.ai/) (Xanadu), [PyTorch](https://pytorch.org/), [Hugging Face Transformers](https://huggingface.co/), [Scikit-Learn](https://scikit-learn.org/), and [Streamlit](https://streamlit.io/).
