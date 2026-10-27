import time
import numpy as np

class DistilBertSentimentClassifier:
    """
    Contextual Transformer Baseline utilizing DistilBERT 
    (distilbert-base-uncased-finetuned-sst-2-english).
    
    Provides high contextual bidirectional self-attention representation.
    """
    def __init__(self, model_name="distilbert-base-uncased-finetuned-sst-2-english", device=-1):
        self.model_name = model_name
        self.device = device
        self.pipeline = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import pipeline
            print(f"[*] Initializing DistilBERT from {self.model_name}...")
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=self.model_name,
                device=self.device,
                truncation=True,
                max_length=512
            )
            print("[+] DistilBERT pipeline loaded successfully.")
        except Exception as e:
            print(f"[!] Warning: DistilBERT could not be initialized directly: {e}")
            self.pipeline = None

    def predict_single(self, text):
        """Predict sentiment for a single text string."""
        if self.pipeline is None:
            # Fallback / initialization retry
            self._load_model()
            if self.pipeline is None:
                raise RuntimeError("DistilBERT model pipeline is not available.")
                
        start = time.time()
        # Truncate text to avoid excessive latency on extreme length
        res = self.pipeline(text[:2000])[0]
        latency = (time.time() - start) * 1000.0
        
        raw_label = res["label"].upper()
        raw_score = float(res["score"])
        
        # SST-2 returns POSITIVE or NEGATIVE
        if raw_label == "POSITIVE":
            pos_prob = raw_score
            pred_label = 1
        else:
            pos_prob = 1.0 - raw_score
            pred_label = 0
            
        return {
            "label": "Positive" if pred_label == 1 else "Negative",
            "class_id": pred_label,
            "confidence": round(raw_score * 100.0, 2),
            "positive_probability": round(pos_prob, 4),
            "latency_ms": round(latency, 2)
        }

    def predict_batch(self, texts):
        """Predict for a list of texts."""
        return [self.predict_single(t) for t in texts]
