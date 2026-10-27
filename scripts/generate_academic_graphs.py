"""
generate_academic_graphs.py - Generates publication-quality figures for PROJECT_DOCUMENTATION.md
using verified empirical benchmark metrics.
"""

import os
import matplotlib.pyplot as plt
import numpy as np

# Set academic styling
plt.style.use("default")
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "figure.dpi": 300
})

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "assets")
os.makedirs(output_dir, exist_ok=True)

models = ["Logistic Regression\n(TF-IDF)", "DistilBERT Baseline\n(SST-2 Head)", "Hybrid QSVM\n(DistilBERT+PCA+Q-Kernel)"]
colors = ["#4A90E2", "#E74C3C", "#2ECC71"]

# -----------------------------------------------------------------------------
# FIGURE 2: Model Accuracy and Macro F1 Comparison (Seed 42, N=360)
# -----------------------------------------------------------------------------
accuracies = [98.3, 59.4, 85.0]
f1_scores = [98.3, 51.6, 84.9]

x = np.arange(len(models))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 5))
rects1 = ax.bar(x - width/2, accuracies, width, label="Accuracy (%)", color="#1f77b4", edgecolor="black", linewidth=0.8)
rects2 = ax.bar(x + width/2, f1_scores, width, label="Macro F1 (%)", color="#2ca02c", edgecolor="black", linewidth=0.8)

ax.set_ylabel("Score (%)")
ax.set_title("Figure 2: Comparative Accuracy and Macro F1 Score (Held-Out Test Set, N=360)")
ax.set_xticks(x)
ax.set_xticklabels(models)
ax.set_ylim(0, 105)
ax.legend(loc="upper left")
ax.grid(axis="y", linestyle="--", alpha=0.7)

for rect in rects1:
    h = rect.get_height()
    ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
for rect in rects2:
    h = rect.get_height()
    ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

plt.tight_layout()
fig2_path = os.path.join(output_dir, "figure2_accuracy_f1_comparison.png")
plt.savefig(fig2_path)
plt.close()
print(f"[+] Saved {fig2_path}")

# -----------------------------------------------------------------------------
# FIGURE 3: Precision & Recall Comparison (N=360)
# -----------------------------------------------------------------------------
precision = [98.4, 63.5, 85.1]
recall = [98.3, 59.4, 85.0]

fig, ax = plt.subplots(figsize=(8, 5))
rects1 = ax.bar(x - width/2, precision, width, label="Macro Precision (%)", color="#ff7f0e", edgecolor="black", linewidth=0.8)
rects2 = ax.bar(x + width/2, recall, width, label="Macro Recall (%)", color="#9467bd", edgecolor="black", linewidth=0.8)

ax.set_ylabel("Score (%)")
ax.set_title("Figure 3: Macro Precision and Recall Across Evaluated Architectures (N=360)")
ax.set_xticks(x)
ax.set_xticklabels(models)
ax.set_ylim(0, 105)
ax.legend(loc="upper left")
ax.grid(axis="y", linestyle="--", alpha=0.7)

for rect in rects1:
    h = rect.get_height()
    ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
for rect in rects2:
    h = rect.get_height()
    ax.annotate(f"{h:.1f}%", xy=(rect.get_x() + rect.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

plt.tight_layout()
fig3_path = os.path.join(output_dir, "figure3_precision_recall_comparison.png")
plt.savefig(fig3_path)
plt.close()
print(f"[+] Saved {fig3_path}")

# -----------------------------------------------------------------------------
# FIGURE 4: Confusion Matrices (Logistic Regression, DistilBERT, Hybrid QSVM) (N=360)
# -----------------------------------------------------------------------------
cm_lr = np.array([[119, 0, 1], [0, 119, 1], [4, 0, 116]])
cm_bert = np.array([[118, 0, 2], [102, 10, 8], [5, 29, 86]])
cm_qsvm = np.array([[111, 4, 5], [9, 92, 19], [6, 11, 103]])

class_labels = ["Negative", "Neutral", "Positive"]

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

for ax, cm, title, cmap_name in zip(
    axes,
    [cm_lr, cm_bert, cm_qsvm],
    ["(a) Logistic Regression (TF-IDF)", "(b) DistilBERT Baseline", "(c) Hybrid QSVM (Ours)"],
    ["Blues", "Reds", "Greens"]
):
    cmap = plt.get_cmap(cmap_name)
    im = ax.imshow(cm, interpolation='nearest', cmap=cmap)
    ax.set_title(title, fontweight="bold", pad=10)
    ax.set_xticks(np.arange(len(class_labels)))
    ax.set_yticks(np.arange(len(class_labels)))
    ax.set_xticklabels(class_labels)
    ax.set_yticklabels(class_labels)
    ax.set_xlabel("Predicted Class")
    ax.set_ylabel("Actual Ground Truth")
    
    # Text annotations inside cells
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            val = cm[i, j]
            color = "white" if val > thresh else "black"
            ax.text(j, i, format(val, 'd'),
                    ha="center", va="center",
                    color=color, fontsize=12, fontweight="bold")

plt.suptitle("Figure 4: Confusion Matrices on 360-Sample Held-Out Test Set (120 samples/class)", fontsize=13, y=1.02)
plt.tight_layout()
fig4_path = os.path.join(output_dir, "figure4_confusion_matrices.png")
plt.savefig(fig4_path, bbox_inches="tight")
plt.close()
print(f"[+] Saved {fig4_path}")

# -----------------------------------------------------------------------------
# FIGURE 5: 5-Fold Stratified Cross-Validation Accuracy
# -----------------------------------------------------------------------------
folds = ["Fold 1", "Fold 2", "Fold 3", "Fold 4", "Fold 5"]
fold_accs = [85.4, 91.7, 93.8, 97.9, 91.7]
mean_acc = 92.08
std_acc = 4.04

fig, ax = plt.subplots(figsize=(8, 4.8))
bars = ax.bar(folds, fold_accs, color="#3498DB", edgecolor="black", linewidth=0.9, width=0.55)
ax.axhline(mean_acc, color="#E74C3C", linestyle="--", linewidth=1.5, label=f"Mean Accuracy ({mean_acc:.2f}% ± {std_acc:.2f}%)")
ax.axhspan(mean_acc - std_acc, mean_acc + std_acc, color="#E74C3C", alpha=0.15, label="Standard Deviation Band (±1σ)")

ax.set_ylabel("Validation Accuracy (%)")
ax.set_title("Figure 5: Stratified 5-Fold Cross-Validation Accuracy (All 240 Headlines)")
ax.set_ylim(70, 105)
ax.legend(loc="lower right")
ax.grid(axis="y", linestyle="--", alpha=0.7)

for bar in bars:
    h = bar.get_height()
    ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

plt.tight_layout()
fig5_path = os.path.join(output_dir, "figure5_cv_fold_variance.png")
plt.savefig(fig5_path)
plt.close()
print(f"[+] Saved {fig5_path}")

# -----------------------------------------------------------------------------
# FIGURE 6: Inference Latency Comparison (Log Scale, GPU Accelerated)
# -----------------------------------------------------------------------------
latencies = [0.02, 5.41, 5.15]  # ms per sample

fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(models, latencies, color=["#34495E", "#E67E22", "#16A085"], edgecolor="black", linewidth=0.9, width=0.5)

ax.set_ylabel("Latency per Sample (ms) [Logarithmic Scale]")
ax.set_title("Figure 6: Per-Sample Inference Latency (CUDA RTX 3050 Accelerated)")
ax.set_yscale("log")
ax.set_ylim(0.005, 30)
ax.grid(axis="y", linestyle="--", alpha=0.7)

for bar in bars:
    h = bar.get_height()
    ax.annotate(f"{h:.2f} ms", xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 5), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

plt.tight_layout()
fig6_path = os.path.join(output_dir, "figure6_inference_latency.png")
plt.savefig(fig6_path)
plt.close()
print(f"[+] Saved {fig6_path}")

# -----------------------------------------------------------------------------
# FIGURE 7: Stress-Test Validation Breakdown (10 Tricky Headlines)
# -----------------------------------------------------------------------------
stress_cats = [
    "Contrastive Clause",
    "Mixed Valence",
    "Constructive Action",
    "Double Negation",
    "Keyword Subversion",
    "Crisis Relief",
    "Sarcasm / Irony",
    "Expectation Drop",
    "Status Quo Policy",
    "Trial Failure"
]
qsvm_correct = [0, 0, 1, 1, 1, 0, 1, 0, 1, 1]  # 6 / 10 passed
bert_correct = [0, 0, 1, 0, 1, 0, 1, 0, 0, 1]  # 4 / 10 passed

fig, ax = plt.subplots(figsize=(10, 5.2))
y_pos = np.arange(len(stress_cats))
bar_h = 0.35

rects1 = ax.barh(y_pos - bar_h/2, qsvm_correct, bar_h, label="Hybrid QSVM (6/10 Passed)", color="#27AE60", edgecolor="black")
rects2 = ax.barh(y_pos + bar_h/2, bert_correct, bar_h, label="DistilBERT Baseline (4/10 Passed)", color="#E74C3C", edgecolor="black")

ax.set_xlabel("Test Result (1 = Passed / 0 = Failed)")
ax.set_title("Figure 7: Ambiguous Linguistic Stress-Test Suite Breakdown (10 Edge Cases)")
ax.set_yticks(y_pos)
ax.set_yticklabels(stress_cats)
ax.set_xlim(-0.1, 1.3)
ax.set_xticks([0, 1])
ax.set_xticklabels(["Failed (0)", "Passed (1)"])
ax.legend(loc="lower right")
ax.grid(axis="x", linestyle="--", alpha=0.7)

plt.tight_layout()
fig7_path = os.path.join(output_dir, "figure7_stress_test_analysis.png")
plt.savefig(fig7_path)
plt.close()
print(f"[+] Saved {fig7_path}")
print("[+] All 6 academic figures successfully generated.")
