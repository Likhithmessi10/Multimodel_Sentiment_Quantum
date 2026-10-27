import os
import joblib
from sklearn.linear_model import LogisticRegression

class LogisticRegressionClassifier:
    """
    Fast Classical Baseline Model for Sentiment Classification.
    Uses L2 regularized log-loss on TF-IDF features.
    """
    def __init__(self, C=1.0, max_iter=200, random_state=42):
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state
        self.model = LogisticRegression(C=C, max_iter=max_iter, random_state=random_state)
        self.is_fitted = False

    def fit(self, X, y):
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X):
        return self.model.predict(X)

    def predict_proba(self, X):
        return self.model.predict_proba(X)[:, 1]

    def save(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.model, filepath)
        print(f"[+] Saved Logistic Regression to {filepath}")

    @classmethod
    def load(cls, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model artifact not found at {filepath}")
        instance = cls()
        instance.model = joblib.load(filepath)
        instance.is_fitted = True
        return instance
