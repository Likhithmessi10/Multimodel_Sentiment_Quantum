import os
import time
import joblib
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

class VariationalQuantumClassifier:
    """
    A genuine 4-Qubit Variational Quantum Classifier (VQC) implemented in PennyLane.
    
    Circuit Design:
    - Qubits: 4 wires (0, 1, 2, 3)
    - Quantum Simulator: 'default.qubit' (CPU statevector simulation)
    - State Preparation: Ry Angle Embedding of 4 classical features
    - Variational Layers: Parameterized Single-Qubit Rotations (Rx, Ry, Rz) + Circular CNOT Entanglement
    - Measurement: Pauli-Z Expectation Value on Wire 0: <Z_0> in [-1, 1]
    - Probability Mapping: P(y=1) = (<Z_0> + 1) / 2
    
    FAIRNESS & INTEGRITY:
    - Real quantum circuit execution on statevector simulator (not mocked).
    - Features must be 4 continuous numerical values (e.g. from QuantumFeaturePipeline).
    """
    def __init__(self, n_qubits=4, n_layers=2, learning_rate=0.08, random_state=42):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.learning_rate = learning_rate
        self.random_state = random_state
        
        # Initialize quantum device
        self.dev = qml.device("default.qubit", wires=n_qubits)
        
        # Setup QNode
        self._circuit = qml.QNode(self._quantum_circuit, self.dev, interface="autograd")
        
        # Initialize trainable parameters: shape (n_layers, n_qubits, 3)
        np.random.seed(random_state)
        self.weights = pnp.array(
            np.random.normal(0, 0.2, (n_layers, n_qubits, 3)),
            requires_grad=True
        )
        
        self.is_trained = False
        self.training_history = []

    def _quantum_circuit(self, features, weights):
        """PennyLane QNode definition."""
        # 1. State preparation via Ry angle embedding
        qml.AngleEmbedding(features, wires=range(self.n_qubits), rotation="Y")
        
        # 2. Variational layers (parameterized rotations + circular CNOT entanglement)
        for layer in range(self.n_layers):
            for q in range(self.n_qubits):
                qml.RX(weights[layer, q, 0], wires=q)
                qml.RY(weights[layer, q, 1], wires=q)
                qml.RZ(weights[layer, q, 2], wires=q)
            
            for q in range(self.n_qubits):
                qml.CNOT(wires=[q, (q + 1) % self.n_qubits])
        
        # 3. Measurement: Pauli-Z expectation value on readout qubit 0
        return qml.expval(qml.PauliZ(0))

    def _loss_function(self, weights, x_batch, y_batch):
        """Mean squared error loss between circuit expectation and target polarity {-1, +1}."""
        loss = 0.0
        batch_size = len(x_batch)
        for x, y in zip(x_batch, y_batch):
            pred_z = self._circuit(x, weights)
            target_z = 2.0 * y - 1.0  # y=1 -> +1.0, y=0 -> -1.0
            loss = loss + (pred_z - target_z) ** 2
        return loss / batch_size

    def fit(self, X_train, y_train, epochs=15, batch_size=25, validation_data=None):
        """
        Train the variational parameters using PennyLane's AdamOptimizer.
        """
        print(f"[*] Starting Quantum VQC Training: {epochs} epochs, batch size {batch_size}...")
        opt = qml.AdamOptimizer(stepsize=self.learning_rate)
        
        w = pnp.array(self.weights, requires_grad=True)
        n_samples = len(X_train)
        indices = np.arange(n_samples)
        
        self.training_history = []
        start_time = time.time()
        
        for epoch in range(1, epochs + 1):
            np.random.shuffle(indices)
            epoch_losses = []
            
            for start_idx in range(0, n_samples, batch_size):
                end_idx = min(start_idx + batch_size, n_samples)
                batch_idx = indices[start_idx:end_idx]
                
                x_b = pnp.array(X_train[batch_idx])
                y_b = pnp.array(y_train[batch_idx])
                
                w, cost = opt.step_and_cost(
                    lambda weights: self._loss_function(weights, x_b, y_b),
                    w
                )
                epoch_losses.append(float(cost))
            
            avg_loss = np.mean(epoch_losses)
            record = {"epoch": epoch, "loss": round(avg_loss, 4)}
            
            if validation_data is not None:
                x_val, y_val = validation_data
                val_probs = self._predict_proba_with_weights(w, x_val)
                val_preds = (val_probs >= 0.5).astype(int)
                val_acc = np.mean(val_preds == y_val) * 100.0
                record["val_accuracy"] = round(val_acc, 2)
                print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_loss:.4f} | Val Acc: {val_acc:.2f}%")
            else:
                print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_loss:.4f}")
                
            self.training_history.append(record)
            
        self.weights = w
        self.is_trained = True
        elapsed = time.time() - start_time
        print(f"[+] Quantum VQC Training Complete in {elapsed:.2f} seconds.")
        return self

    def _predict_proba_with_weights(self, weights, X):
        probs = []
        for x in X:
            exp_z = float(self._circuit(x, weights))
            # Map [-1, 1] to [0, 1]
            p = (exp_z + 1.0) / 2.0
            probs.append(p)
        return np.array(probs, dtype=np.float64)

    def predict_proba(self, X):
        """Predict probability P(y=1) for an array of 4-feature samples."""
        return self._predict_proba_with_weights(self.weights, X)

    def predict(self, X, threshold=0.5):
        """Return discrete binary labels: 1 (Positive) or 0 (Negative)."""
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def get_circuit_ascii(self):
        """Return the ASCII text representation of the 4-qubit quantum circuit."""
        dummy_x = [0.1, 0.2, 0.3, 0.4]
        return qml.draw(self._circuit)(dummy_x, self.weights)

    def save(self, filepath):
        """Serialize circuit parameters."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            "weights": np.array(self.weights),
            "n_qubits": self.n_qubits,
            "n_layers": self.n_layers,
            "training_history": self.training_history,
            "is_trained": self.is_trained
        }, filepath)
        print(f"[+] Saved VQC weights to {filepath}")

    @classmethod
    def load(cls, filepath):
        """Load trained VQC from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"VQC artifact not found at {filepath}")
        data = joblib.load(filepath)
        instance = cls(n_qubits=data["n_qubits"], n_layers=data["n_layers"])
        instance.weights = pnp.array(data["weights"], requires_grad=False)
        instance.training_history = data.get("training_history", [])
        instance.is_trained = data.get("is_trained", True)
        return instance
