import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import MinMaxScaler

class QuantumFeaturePipeline:
    """
    Classical text preprocessing and dimensionality reduction pipeline designed to 
    encode text into a 4-dimensional continuous vector suitable for angle embedding 
    into a 4-qubit quantum circuit.
    
    CRITICAL FAIRNESS RULE:
    Fitted strictly on training data only. Never fitted on validation or test sets.
    """
    def __init__(self, n_components=4, max_features=5000, random_state=42):
        self.n_components = n_components
        self.max_features = max_features
        self.random_state = random_state
        
        self.tfidf = TfidfVectorizer(
            max_features=max_features,
            sublinear_tf=True,
            ngram_range=(1, 2),
            stop_words='english'
        )
        self.svd = TruncatedSVD(n_components=n_components, random_state=random_state)
        # Scale to [-0.9 * pi, 0.9 * pi] for rotation gates (Ry)
        self.scaler = MinMaxScaler(feature_range=(-np.pi * 0.9, np.pi * 0.9))
        self.is_fitted = False

    def fit(self, texts):
        """Fit TF-IDF, TruncatedSVD, and Scaler exclusively on training texts."""
        print(f"[*] Fitting QuantumFeaturePipeline on {len(texts)} training samples...")
        tfidf_mat = self.tfidf.fit_transform(texts)
        svd_mat = self.svd.fit_transform(tfidf_mat)
        self.scaler.fit(svd_mat)
        self.is_fitted = True
        explained_var = np.sum(self.svd.explained_variance_ratio_) * 100
        print(f"[+] QuantumFeaturePipeline fitted. 4 SVD components retain {explained_var:.2f}% of TF-IDF variance.")
        return self

    def transform(self, texts):
        """Transform texts into (N, 4) numerical angle representations."""
        if not self.is_fitted:
            raise RuntimeError("QuantumFeaturePipeline must be fitted before calling transform().")
        tfidf_mat = self.tfidf.transform(texts)
        svd_mat = self.svd.transform(tfidf_mat)
        angles = self.scaler.transform(svd_mat)
        return np.asarray(angles, dtype=np.float64)

    def fit_transform(self, texts):
        return self.fit(texts).transform(texts)

    def save(self, filepath):
        """Serialize pipeline components."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            'tfidf': self.tfidf,
            'svd': self.svd,
            'scaler': self.scaler,
            'n_components': self.n_components,
            'is_fitted': self.is_fitted
        }, filepath)
        print(f"[+] Saved QuantumFeaturePipeline to {filepath}")

    @classmethod
    def load(cls, filepath):
        """Load serialized pipeline."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Pipeline artifact not found at {filepath}")
        data = joblib.load(filepath)
        instance = cls(n_components=data['n_components'])
        instance.tfidf = data['tfidf']
        instance.svd = data['svd']
        instance.scaler = data['scaler']
        instance.is_fitted = data['is_fitted']
        return instance
