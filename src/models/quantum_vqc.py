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
    - Measurement: Pauli-Z Expectation Values on all 4 wires: <Z_i>
    - Decision: Learned linear readout + Sigmoid mapping to probability in [0, 1]
    
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
        
        # Initialize trainable parameters
        np.random.seed(random_state)
        # Weights shape: (n_layers, n_qubits, 3) for Rx, Ry, Rz
        self.circuit_weights = pnp.array(
            np.random.normal(0, 0.2, (n_layers, n_qubits, 3)),
            requires_grad=True
        )
        # Readout weights (4,) and bias (1,)
        self.readout_w = pnp.array(np.random.normal(0, 0.3, (n_qubits,)), requires_grad=True)
        self.readout_b = pnp.array(0.0, requires_grad=True)
        
        self.is_trained = False
        self.training_history = []

    def _quantum_circuit(self, features, weights):
        """PennyLane QNode definition."""
        # 1. State preparation via Ry angle embedding
        qml.AngleEmbedding(features, wires=range(self.n_qubits), rotation="Y")
        
        # 2. Variational layers (parameterized rotations + entanglement)
        for layer in range(self.n_layers):
            # Parameterized single-qubit rotations
            for q in range(self.n_qubits):
                qml.RX(weights[layer, q, 0], wires=q)
                qml.RY(weights[layer, q, 1], wires=q)
                qml.RZ(weights[layer, q, 2], wires=q)
            
            # Circular CNOT entangling gates
            for q in range(self.n_qubits):
                qml.CNOT(wires=[q, (q + 1) % self.n_qubits])
        
        # 3. Measurement: Pauli-Z expectation values across all wires
        return [qml.expval(qml.PauliZ(i)) for i in range(self.n_qubits)]

    def _forward_sample(self, x, weights, w_out, b_out):
        """Compute predicted probability P(y=1|x) for a single sample."""
        # exp_vals is array of shape (4,) with values in [-1, 1]
        exp_vals = pnp.array(self._circuit(x, weights))
        # Linear readout
        logits = pnp.dot(exp_vals, w_out) + b_out
        # Sigmoid activation with numerical clipping
        logits_clipped = pnp.clip(logits, -15.0, 15.0)
        prob = 1.0 / (1.0 + pnp.exp(-logits_clipped))
        return prob

    def _loss_function(self, params, x_batch, y_batch):
        """Binary cross-entropy loss over a batch."""
        weights, w_out, b_out = params
        loss = 0.0
        eps = 1e-7
        batch_size = len(x_batch)
        
        for i in range(batch_size):
            p = self._forward_sample(x_batch[i], weights, w_out, b_out)
            # Binary cross entropy
            loss = loss - (y_batch[i] * pnp.log(p + eps) + (1.0 - y_batch[i]) * pnp.log(1.0 - p + eps))
            
        return loss / batch_size

    def fit(self, X_train, y_train, epochs=25, batch_size=32, validation_data=None):
        """
        Train the variational parameters and readout head using PennyLane's AdamOptimizer.
        """
        print(f"[*] Starting Quantum VQC Training: {epochs} epochs, batch size {batch_size}...")
        opt = qml.AdamOptimizer(stepsize=self.learning_rate)
        
        params = (self.circuit_weights, self.readout_w, self.readout_b)
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
                
                params, cost = opt.step_and_cost(
                    lambda p: self._loss_function(p, x_b, y_b),
                    params
                )
                epoch_losses.append(float(cost))
            
            avg_loss = np.mean(epoch_losses)
            record = {"epoch": epoch, "loss": round(avg_loss, 4)}
            
            if validation_data is not None:
                x_val, y_val = validation_data
                val_probs = self._predict_proba_with_params(params, x_val)
                val_preds = (val_probs >= 0.5).astype(int)
                val_acc = np.mean(val_preds == y_val) * 100.0
                record["val_accuracy"] = round(val_acc, 2)
                print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_loss:.4f} | Val Acc: {val_acc:.2f}%")
            else:
                print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_loss:.4f}")
                
            self.training_history.append(record)
            
        self.circuit_weights, self.readout_w, self.readout_b = params
        self.is_trained = True
        elapsed = time.time() - start_time
        print(f"[+] Quantum VQC Training Complete in {elapsed:.2f} seconds.")
        return self

    def _predict_proba_with_params(self, params, X):
        weights, w_out, b_out = params
        probs = [float(self._forward_sample(x, weights, w_out, b_out)) for x in X]
        return np.array(probs, dtype=np.float64)

    def predict_proba(self, X):
        """Predict probability P(y=1) for an array of 4-feature samples."""
        params = (self.circuit_weights, self.readout_w, self.readout_b)
        return self._predict_proba_with_params(params, X)

    def predict(self, X, threshold=0.5):
        """Return discrete binary labels: 1 (Positive) or 0 (Negative)."""
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def get_circuit_ascii(self):
        """Return the ASCII text representation of the 4-qubit quantum circuit."""
        dummy_x = [0.1, 0.2, 0.3, 0.4]
        return qml.draw(self._circuit)(dummy_x, self.circuit_weights)

    def save(self, filepath):
        """Serialize circuit parameters."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            "circuit_weights": np.array(self.circuit_weights),
            "readout_w": np.array(self.readout_w),
            "readout_b": float(self.readout_b),
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
        instance.circuit_weights = pnp.array(data["circuit_weights"], requires_grad=False)
        instance.readout_w = pnp.array(data["readout_w"], requires_grad=False)
        instance.readout_b = pnp.array(data["readout_b"], requires_grad=False)
        instance.training_history = data.get("training_history", [])
        instance.is_trained = data.get("is_trained", True)
        return instance
