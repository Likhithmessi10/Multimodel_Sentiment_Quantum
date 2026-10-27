"""
app.py - Multi-Model Sentiment Analysis Demonstration UI
Displays predictions from all three models (Logistic Regression, Multinomial Naive Bayes, Bidirectional LSTM)
side-by-side with complete decision logic and token-level feature attribution.
"""

import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.predict import SentimentPredictor

# Page Configuration - Wide layout for clear side-by-side model comparison
st.set_page_config(
    page_title="Multimodel Sentiment Analysis of Text in DL",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for polished, modern academic demonstration
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    h1 {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        color: #1a2639;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #555;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    /* Model Card Styling */
    .model-card {
        border-radius: 10px;
        padding: 1.2rem;
        background: #ffffff;
        border: 1px solid #e1e4e8;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
        text-align: center;
    }
    .model-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a2639;
        margin-bottom: 0.5rem;
    }
    .model-sub {
        font-size: 0.8rem;
        color: #666;
        margin-bottom: 0.8rem;
    }
    .badge-pos {
        background-color: #e6f4ea;
        color: #137333;
        border: 1px solid #ceead6;
        padding: 0.5rem 0.8rem;
        border-radius: 6px;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .badge-neg {
        background-color: #fce8e6;
        color: #c5221f;
        border: 1px solid #fad2cf;
        padding: 0.5rem 0.8rem;
        border-radius: 6px;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .consensus-box {
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin: 1.2rem 0;
        text-align: center;
        font-size: 1.1rem;
        font-weight: 600;
    }
    .consensus-agree {
        background-color: #e8f0fe;
        color: #1a73e8;
        border: 1px solid #d2e3fc;
    }
    .consensus-split {
        background-color: #fef7e0;
        color: #b06000;
        border: 1px solid #fce8b2;
    }
    .logic-box {
        background-color: #f8f9fa;
        border-left: 4px solid #1a73e8;
        padding: 0.8rem 1rem;
        border-radius: 0 6px 6px 0;
        margin-bottom: 1rem;
        font-size: 0.92rem;
        line-height: 1.45;
    }
    .footer-note {
        font-size: 0.85rem;
        color: #777;
        text-align: center;
        margin-top: 2rem;
        border-top: 1px solid #eee;
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown("<h1>Multimodel Sentiment Analysis of Text in DL</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Comparative sentiment prediction and decision logic inspection across Linear, Probabilistic, and Deep Learning models.</div>", unsafe_allow_html=True)

# Initialize Predictor
@st.cache_resource
def get_predictor():
    return SentimentPredictor()

try:
    predictor = get_predictor()
except Exception as e:
    st.error(f"Failed to load trained models: {e}")
    st.stop()

# Predefined Demonstration Examples
EXAMPLES = {
    "-- Custom Review / Input --": "",
    "Strongly Positive Review": "This movie was an extraordinary visual masterpiece with brilliant acting, a gripping narrative, and an unforgettable emotional climax.",
    "Strongly Negative Review": "The movie was utterly dreadful, boring, terribly written, and an unbearable waste of two hours.",
    "Subtle Mixed / Positive": "While the first half dragged somewhat, the director salvaged the ending with impressive cinematography and solid character development.",
    "Subtle Mixed / Negative": "Despite high expectations and famous lead actors, the pacing fell apart and the dialogue was completely contrived.",
    "Negation Nuance": "It was not a bad film, but definitely not a great one either."
}

# Example Selector
selected_example = st.selectbox(
    "Select a pre-configured sample review or write custom text below:",
    options=list(EXAMPLES.keys()),
    index=0
)

# Text Area Input
default_text = EXAMPLES[selected_example]
user_text = st.text_area(
    "Enter sentence, movie review, or feedback to analyze:",
    value=default_text,
    height=110,
    placeholder="Type or paste any English sentence or review here..."
)

# Action Button
analyze_btn = st.button("🚀 Analyze Sentiment Across All 3 Models", type="primary", use_container_width=True)

def render_attribution_bar(explanation: dict, title: str):
    """Render interactive Plotly horizontal bar chart for token attribution."""
    top_pos = explanation.get("top_positive", [])
    top_neg = explanation.get("top_negative", [])

    chart_tokens = []
    for item in top_pos[:5]:
        chart_tokens.append({"word": item["word"], "score": item["score"], "direction": "Positive Influence"})
    for item in top_neg[:5]:
        chart_tokens.append({"word": item["word"], "score": item["score"], "direction": "Negative Influence"})

    if not chart_tokens:
        st.info("No salient vocabulary tokens or out-of-vocabulary terms detected.")
        return

    df_tokens = pd.DataFrame(chart_tokens).sort_values(by="score", ascending=True)
    colors = ["#c5221f" if s < 0 else "#137333" for s in df_tokens["score"]]

    fig = go.Figure(go.Bar(
        x=df_tokens["score"],
        y=df_tokens["word"],
        orientation="h",
        marker_color=colors,
        text=[f"{s:+.3f}" for s in df_tokens["score"]],
        textposition="auto"
    ))
    fig.update_layout(
        title=f"Influential Words ({title})",
        xaxis_title="Polarity Contribution / Attribution Score",
        yaxis_title="Token",
        height=280,
        margin=dict(l=10, r=10, t=35, b=25),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)


if analyze_btn:
    if not user_text.strip():
        st.warning("⚠️ Please provide text to analyze before clicking the button.")
    else:
        with st.spinner("Executing inference and calculating token attribution across all 3 models..."):
            try:
                res_lr = predictor.predict(user_text, model_name="Logistic Regression")
                res_nb = predictor.predict(user_text, model_name="Multinomial Naive Bayes")
                res_lstm = predictor.predict(user_text, model_name="Bidirectional LSTM")
            except Exception as ex:
                st.error(f"Inference error: {ex}")
                st.stop()

        results = [res_lr, res_nb, res_lstm]
        pos_count = sum(1 for r in results if r["sentiment"] == "Positive")
        neg_count = sum(1 for r in results if r["sentiment"] == "Negative")

        st.markdown("---")

        # Consensus Banner
        if pos_count == 3:
            st.markdown(
                "<div class='consensus-box consensus-agree'>🎯 <strong>Unanimous Consensus:</strong> All 3 models predict <strong>POSITIVE</strong> sentiment.</div>",
                unsafe_allow_html=True
            )
        elif neg_count == 3:
            st.markdown(
                "<div class='consensus-box consensus-agree'>🎯 <strong>Unanimous Consensus:</strong> All 3 models predict <strong>NEGATIVE</strong> sentiment.</div>",
                unsafe_allow_html=True
            )
        else:
            majority = "Positive" if pos_count > neg_count else "Negative"
            st.markdown(
                f"<div class='consensus-box consensus-split'>⚖️ <strong>Split Decision:</strong> {pos_count} models predict Positive, {neg_count} predict Negative. (Majority: <strong>{majority}</strong>)</div>",
                unsafe_allow_html=True
            )

        # -----------------------------------------------------------------
        # SECTION 1: SIDE-BY-SIDE MODEL OUTPUT CARDS
        # -----------------------------------------------------------------
        st.markdown("### 📊 Side-by-Side Model Predictions")
        c1, c2, c3 = st.columns(3)

        # Model 1: Logistic Regression
        with c1:
            st.markdown("<div class='model-card'>", unsafe_allow_html=True)
            st.markdown("<div class='model-title'>Model 1: Logistic Regression</div>", unsafe_allow_html=True)
            st.markdown("<div class='model-sub'>Convex Linear Model | TF-IDF (1,2) N-Grams</div>", unsafe_allow_html=True)
            if res_lr["sentiment"] == "Positive":
                st.markdown(f"<div class='badge-pos'>🟢 POSITIVE ({res_lr['confidence']*100:.1f}%)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='badge-neg'>🔴 NEGATIVE ({res_lr['confidence']*100:.1f}%)</div>", unsafe_allow_html=True)

            st.write(f"**Pos Prob:** {res_lr['prob_positive']*100:.1f}% | **Neg Prob:** {res_lr['prob_negative']*100:.1f}%")
            st.write(f"⏱️ **Latency:** `{res_lr['inference_time_ms']:.1f} ms` | 🏆 **Test Acc:** `90.64%`")
            st.progress(res_lr["prob_positive"])
            st.markdown("</div>", unsafe_allow_html=True)

        # Model 2: Multinomial Naive Bayes
        with c2:
            st.markdown("<div class='model-card'>", unsafe_allow_html=True)
            st.markdown("<div class='model-title'>Model 2: Naive Bayes</div>", unsafe_allow_html=True)
            st.markdown("<div class='model-sub'>Generative Probabilistic | Laplace α=1.0</div>", unsafe_allow_html=True)
            if res_nb["sentiment"] == "Positive":
                st.markdown(f"<div class='badge-pos'>🟢 POSITIVE ({res_nb['confidence']*100:.1f}%)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='badge-neg'>🔴 NEGATIVE ({res_nb['confidence']*100:.1f}%)</div>", unsafe_allow_html=True)

            st.write(f"**Pos Prob:** {res_nb['prob_positive']*100:.1f}% | **Neg Prob:** {res_nb['prob_negative']*100:.1f}%")
            st.write(f"⏱️ **Latency:** `{res_nb['inference_time_ms']:.1f} ms` | 🏆 **Test Acc:** `87.91%`")
            st.progress(res_nb["prob_positive"])
            st.markdown("</div>", unsafe_allow_html=True)

        # Model 3: Bidirectional LSTM
        with c3:
            st.markdown("<div class='model-card'>", unsafe_allow_html=True)
            st.markdown("<div class='model-title'>Model 3: Bidirectional LSTM</div>", unsafe_allow_html=True)
            st.markdown("<div class='model-sub'>Deep Recurrent Network | PyTorch Sequence Model</div>", unsafe_allow_html=True)
            if res_lstm["sentiment"] == "Positive":
                st.markdown(f"<div class='badge-pos'>🟢 POSITIVE ({res_lstm['confidence']*100:.1f}%)</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='badge-neg'>🔴 NEGATIVE ({res_lstm['confidence']*100:.1f}%)</div>", unsafe_allow_html=True)

            st.write(f"**Pos Prob:** {res_lstm['prob_positive']*100:.1f}% | **Neg Prob:** {res_lstm['prob_negative']*100:.1f}%")
            st.write(f"⏱️ **Latency:** `{res_lstm['inference_time_ms']:.1f} ms` | 🏆 **Test Acc:** `72.44%`")
            st.progress(res_lstm["prob_positive"])
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # -----------------------------------------------------------------
        # SECTION 2: SHOWCASE THE LOGIC (DEEP DIVE INTO HOW EACH DECIDED)
        # -----------------------------------------------------------------
        st.markdown("### 🔍 Showcase the Decision Logic & Word Influences")
        st.caption("Inspect the exact mathematical mechanism and token-level attribution that explains how each model formed its decision.")

        tab_lr, tab_nb, tab_lstm, tab_comp = st.tabs([
            "📐 1. Logistic Regression Logic",
            "🎲 2. Naive Bayes Logic",
            "🧠 3. Bidirectional LSTM Logic",
            "📋 4. Comparative Matrix"
        ])

        # TAB 1: Logistic Regression Logic
        with tab_lr:
            st.markdown("""
            <div class='logic-box'>
                <strong>How the Logic Works:</strong><br>
                1. Text is mapped into a 10,000-dimensional sublinear TF-IDF space spanning unigrams and bigrams.<br>
                2. Computes the dot product with learned weight coefficients: <code>z = Σ (w_i · x_i) + b</code>.<br>
                3. Passes <code>z</code> through the logistic sigmoid function: <code>P(Positive) = 1 / (1 + e^-z)</code>.<br>
                4. Words with high positive coefficients push the score upward; words with negative coefficients push downward.
            </div>
            """, unsafe_allow_html=True)

            col_l1, col_l2 = st.columns([1.2, 1.0])
            with col_l1:
                render_attribution_bar(res_lr["explanation"], "Logistic Regression")
            with col_l2:
                st.markdown("**Active Token Breakdown:**")
                tab_data = []
                for t in res_lr["explanation"].get("active_tokens", []):
                    tab_data.append({
                        "Token": t["word"],
                        "Weight (x·β)": round(t["score"], 4),
                        "Learned Coef (β)": round(t.get("coefficient", 0.0), 4),
                        "Push": "🟢 Positive" if t["score"] > 0 else "🔴 Negative"
                    })
                if tab_data:
                    st.dataframe(pd.DataFrame(tab_data), use_container_width=True, hide_index=True)
                else:
                    st.info("No active tokens found.")

        # TAB 2: Naive Bayes Logic
        with tab_nb:
            st.markdown("""
            <div class='logic-box'>
                <strong>How the Logic Works:</strong><br>
                1. Applies Bayes' Rule under the conditional word independence assumption.<br>
                2. Incorporates Laplace smoothing (α = 1.0): <code>P(w|c) = (count + 1) / (total + |V|)</code>.<br>
                3. Evaluates the Log-Likelihood Ratio for each word: <code>LogOdds(w) = log P(w|Positive) - log P(w|Negative)</code>.<br>
                4. Positive log-odds push the posterior probability toward Positive; negative log-odds push toward Negative.
            </div>
            """, unsafe_allow_html=True)

            col_n1, col_n2 = st.columns([1.2, 1.0])
            with col_n1:
                render_attribution_bar(res_nb["explanation"], "Naive Bayes")
            with col_n2:
                st.markdown("**Active Token Breakdown:**")
                tab_data = []
                for t in res_nb["explanation"].get("active_tokens", []):
                    tab_data.append({
                        "Token": t["word"],
                        "Log-Odds Ratio": round(t["score"], 4),
                        "Push": "🟢 Positive" if t["score"] > 0 else "🔴 Negative"
                    })
                if tab_data:
                    st.dataframe(pd.DataFrame(tab_data), use_container_width=True, hide_index=True)
                else:
                    st.info("No active tokens found.")

        # TAB 3: Bidirectional LSTM Logic
        with tab_lstm:
            st.markdown("""
            <div class='logic-box'>
                <strong>How the Logic Works:</strong><br>
                1. Maps words into continuous 64-dimensional learned embeddings.<br>
                2. Recurrent BiLSTM cells process sequences forward (past-to-future) and backward (future-to-past).<br>
                3. The concatenated final states are passed through Dense(64) + ReLU + Dropout(0.3) + Sigmoid.<br>
                4. <strong>Word Occlusion Attribution Logic:</strong> For every word <code>w_i</code>, the model measures the marginal change in output probability: <code>ΔP = P(Full) - P(Text \ {w_i})</code>. Removing positive words causes positive confidence to drop (ΔP > 0); removing negative words causes positive confidence to rise (ΔP < 0).
            </div>
            """, unsafe_allow_html=True)

            col_m1, col_m2 = st.columns([1.2, 1.0])
            with col_m1:
                render_attribution_bar(res_lstm["explanation"], "Bidirectional LSTM")
            with col_m2:
                st.markdown("**Word Occlusion Attribution (ΔP):**")
                tab_data = []
                for t in res_lstm["explanation"].get("active_tokens", []):
                    tab_data.append({
                        "Token": t["word"],
                        "Marginal Shift (ΔP)": round(t["score"], 4),
                        "Decision Contribution": "🟢 Positive Driver" if t["score"] > 0.001 else "🔴 Negative Driver" if t["score"] < -0.001 else "⚪ Neutral"
                    })
                if tab_data:
                    st.dataframe(pd.DataFrame(tab_data), use_container_width=True, hide_index=True)
                else:
                    st.info("No active tokens found.")

        # TAB 4: Comparative Matrix
        with tab_comp:
            st.markdown("#### Multi-Model Comparison on Given Input Text")
            comp_rows = [
                {
                    "Model": res_lr["model_name"],
                    "Predicted Sentiment": res_lr["sentiment"],
                    "Confidence": f"{res_lr['confidence']*100:.1f}%",
                    "Pos Probability": f"{res_lr['prob_positive']*100:.1f}%",
                    "Neg Probability": f"{res_lr['prob_negative']*100:.1f}%",
                    "Latency (ms)": f"{res_lr['inference_time_ms']:.1f}",
                    "Representation Type": "TF-IDF (1,2) N-Grams",
                    "Benchmark Test Accuracy": "90.64%"
                },
                {
                    "Model": res_nb["model_name"],
                    "Predicted Sentiment": res_nb["sentiment"],
                    "Confidence": f"{res_nb['confidence']*100:.1f}%",
                    "Pos Probability": f"{res_nb['prob_positive']*100:.1f}%",
                    "Neg Probability": f"{res_nb['prob_negative']*100:.1f}%",
                    "Latency (ms)": f"{res_nb['inference_time_ms']:.1f}",
                    "Representation Type": "TF-IDF Term Counts",
                    "Benchmark Test Accuracy": "87.91%"
                },
                {
                    "Model": res_lstm["model_name"],
                    "Predicted Sentiment": res_lstm["sentiment"],
                    "Confidence": f"{res_lstm['confidence']*100:.1f}%",
                    "Pos Probability": f"{res_lstm['prob_positive']*100:.1f}%",
                    "Neg Probability": f"{res_lstm['prob_negative']*100:.1f}%",
                    "Latency (ms)": f"{res_lstm['inference_time_ms']:.1f}",
                    "Representation Type": "Learned Dense Embeddings",
                    "Benchmark Test Accuracy": "72.44%"
                }
            ]
            st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

        st.markdown(
            "<div class='footer-note'>Multimodel Sentiment Analysis System | Built for B.Tech Final Year Mini-Project Evaluation | Genuinely Trained on IMDb 50,000 Dataset</div>",
            unsafe_allow_html=True
        )
