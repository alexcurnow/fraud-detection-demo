"""
Fraud Detection ML Model - Training and Prediction

ML CONCEPTS EXPLAINED:

1. ISOLATION FOREST:
   - An "anomaly detection" algorithm
   - Idea: Fraudulent transactions are outliers (unusual/rare)
   - Works by "isolating" unusual data points
   - Doesn't need many fraud examples to learn (unsupervised learning)
   - Perfect for fraud where we have few labeled examples

2. HOW IT WORKS:
   - Creates random "decision trees" that split data randomly
   - Outliers (fraud) get isolated quickly (fewer splits needed)
   - Normal transactions take many splits to isolate
   - The model scores: low score = outlier = fraud

3. TRAINING:
   - Show the model many transactions (fraud + legitimate)
   - It learns the "shape" of normal behavior
   - Anything far from normal = fraud

4. PREDICTION:
   - New transaction comes in
   - Extract features
   - Model returns "anomaly score" (-1 to 1)
   - Score < 0 = anomaly = potential fraud
"""

import logging
import pickle
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

from .feature_extractor import FraudFeatureExtractor
from ..database import Database

logger = logging.getLogger(__name__)

# Model storage path
MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


class FraudDetectionModel:
    """
    ML-based fraud detection using Isolation Forest.

    Workflow:
    1. Extract features from transactions
    2. Train Isolation Forest on normal + fraud patterns
    3. Predict fraud probability for new transactions
    """

    def __init__(self):
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: list[str] = []
        self.model_version: str = ""
        self.trained_at: Optional[datetime] = None

    def train(self, contamination: float = 0.05):
        """
        Train the fraud detection model on all available transaction data.

        Args:
            contamination: Expected proportion of outliers/fraud (0.02-0.05 typical)
                          This tells the model: "expect about 5% of data to be fraud"

        TRAINING PROCESS:
        1. Extract features from all transactions
        2. Normalize features (StandardScaler) - makes all features 0-1 range
        3. Train Isolation Forest
        4. Evaluate performance on training data
        5. Save model to disk
        """
        logger.info("=" * 80)
        logger.info("TRAINING FRAUD DETECTION MODEL")
        logger.info("=" * 80)

        # Step 1: Extract features from all transactions
        logger.info("Step 1: Extracting features from transactions...")
        data = FraudFeatureExtractor.extract_features_for_all_transactions()

        if len(data) < 10:
            raise ValueError(f"Need at least 10 transactions to train, found {len(data)}")

        # Convert to numpy arrays for scikit-learn
        # X = features matrix (each row is a transaction, each column is a feature)
        # y = labels (1 = fraud, 0 = legitimate)
        feature_dicts = [d['features'] for d in data]
        self.feature_names = list(feature_dicts[0].keys())

        X = np.array([[f[name] for name in self.feature_names] for f in feature_dicts])
        y = np.array([1 if d['is_fraud'] else 0 for d in data])

        logger.info(f"Dataset: {len(X)} transactions, {X.shape[1]} features")
        logger.info(f"Fraud rate: {y.sum()}/{len(y)} ({y.sum()/len(y)*100:.1f}%)")

        # Step 2: Normalize features
        # WHY: Features have different scales ($5 vs 5000 km)
        # StandardScaler makes all features have mean=0, std=1
        logger.info("Step 2: Normalizing features (StandardScaler)...")
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Step 3: Train Isolation Forest
        logger.info(f"Step 3: Training Isolation Forest (contamination={contamination})...")

        self.model = IsolationForest(
            contamination=contamination,  # Expected fraud rate
            n_estimators=100,  # Number of decision trees (more = better, but slower)
            max_samples='auto',  # Samples per tree
            random_state=42,  # For reproducibility
            n_jobs=-1  # Use all CPU cores
        )

        self.model.fit(X_scaled)
        logger.info("✓ Model training complete")

        # Step 4: Evaluate on training data
        logger.info("Step 4: Evaluating model performance...")
        predictions = self.model.predict(X_scaled)  # -1 = outlier, 1 = normal
        anomaly_scores = self.model.score_samples(X_scaled)  # Lower = more anomalous

        # Convert predictions: -1 (outlier) → 1 (fraud), 1 (normal) → 0 (not fraud)
        y_pred = (predictions == -1).astype(int)

        # Calculate metrics
        metrics = self._calculate_metrics(y, y_pred)
        self._log_metrics(metrics, y, y_pred)

        # Step 5: Save model
        self.model_version = f"v1_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.trained_at = datetime.now(timezone.utc)
        self._save_model()
        self._save_model_metadata(metrics)

        logger.info("=" * 80)
        logger.info(f"Model training complete! Version: {self.model_version}")
        logger.info("=" * 80)

        return metrics

    def predict(self, transaction_id: str) -> Dict:
        """
        Predict fraud probability for a transaction.

        Args:
            transaction_id: ID of transaction to score

        Returns:
            Dictionary with:
            - transaction_id
            - fraud_probability (0.0 to 1.0)
            - is_fraud (boolean prediction)
            - anomaly_score (raw score from model)
            - flagged_reasons (list of suspicious features)
        """
        if not self.model or not self.scaler:
            raise ValueError("Model not trained! Call train() first or load() a saved model.")

        # Extract features
        features = FraudFeatureExtractor.extract_features(transaction_id)
        if not features:
            raise ValueError(f"Could not extract features for transaction {transaction_id}")

        # Convert to numpy array (same order as training)
        X = np.array([[features[name] for name in self.feature_names]])

        # Normalize
        X_scaled = self.scaler.transform(X)

        # Predict
        prediction = self.model.predict(X_scaled)[0]  # -1 or 1
        anomaly_score = self.model.score_samples(X_scaled)[0]  # Lower = more anomalous

        # Use prediction directly for fraud classification
        is_fraud = prediction == -1  # -1 means outlier/fraud

        # For probability: use binary classification (high confidence when flagged)
        # Isolation Forest doesn't give calibrated probabilities, so we use decision boundary
        fraud_probability = 0.95 if is_fraud else 0.05

        # Identify suspicious features
        flagged_reasons = self._identify_suspicious_features(features)

        result = {
            'transaction_id': transaction_id,
            'fraud_probability': round(fraud_probability, 4),
            'is_fraud': bool(is_fraud),
            'anomaly_score': round(float(anomaly_score), 4),
            'flagged_reasons': flagged_reasons,
            'model_version': self.model_version
        }

        logger.info(
            f"Scored {transaction_id}: "
            f"fraud_prob={result['fraud_probability']:.2%}, "
            f"is_fraud={result['is_fraud']}"
        )

        return result

    def _identify_suspicious_features(self, features: Dict[str, float]) -> list[str]:
        """
        Identify which features are suspicious.

        HEURISTICS (rules of thumb):
        - High amount deviation (>3x normal)
        - High velocity (>3 transactions/hour)
        - Fast travel (>500 km/h = airplane speed)
        - Unusual time (3-5 AM)
        - New device
        """
        reasons = []

        if features.get('amount_deviation_from_avg', 0) > 3.0:
            reasons.append('unusual_amount')

        if features.get('transactions_last_hour', 0) >= 3:
            reasons.append('velocity_anomaly')

        if features.get('travel_velocity_kmh', 0) > 500:
            reasons.append('geographic_impossibility')

        hour = features.get('hour_of_day', 12)
        if 3 <= hour <= 5:
            reasons.append('suspicious_timing')

        if features.get('is_new_device', 0) == 1.0:
            reasons.append('new_device')

        if features.get('distance_from_last_km', 0) > 1000:
            reasons.append('unusual_location')

        return reasons

    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """
        Calculate evaluation metrics.

        METRICS EXPLAINED:
        - Precision: Of predictions marked as fraud, how many were actually fraud?
                     (Avoid false alarms)
        - Recall: Of actual fraud, how many did we catch?
                  (Catch all fraud)
        - F1: Balance between precision and recall (harmonic mean)
        - Confusion Matrix:
            [[TN, FP],   TN = correctly predicted legitimate
             [FN, TP]]   TP = correctly predicted fraud
                         FP = false alarm (predicted fraud, was legitimate)
                         FN = missed fraud (predicted legitimate, was fraud)
        """
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        # Calculate accuracy
        accuracy = (y_true == y_pred).sum() / len(y_true)

        return {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1)
        }

    def _log_metrics(self, metrics: Dict, y_true: np.ndarray, y_pred: np.ndarray):
        """Log evaluation metrics."""
        logger.info("\nModel Performance:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.2%} (overall correctness)")
        logger.info(f"  Precision: {metrics['precision']:.2%} (of flagged fraud, % actually fraud)")
        logger.info(f"  Recall:    {metrics['recall']:.2%} (of actual fraud, % caught)")
        logger.info(f"  F1 Score:  {metrics['f1_score']:.2%} (balance of precision/recall)")

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        logger.info("\nConfusion Matrix:")
        logger.info("                 Predicted")
        logger.info("                 Legit  Fraud")
        logger.info(f"Actual  Legit    {cm[0][0]:4d}   {cm[0][1]:4d}")
        logger.info(f"        Fraud    {cm[1][0]:4d}   {cm[1][1]:4d}")

    def _save_model(self):
        """Save trained model to disk."""
        model_path = MODEL_DIR / f"fraud_model_{self.model_version}.pkl"

        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'model_version': self.model_version,
                'trained_at': self.trained_at
            }, f)

        logger.info(f"Model saved: {model_path}")

    def _save_model_metadata(self, metrics: Dict):
        """Save model metadata to database."""
        Database.execute(
            """
            INSERT INTO ml_models (
                model_version, algorithm, training_date,
                accuracy, precision, recall, f1_score,
                feature_list, hyperparameters, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                self.model_version,
                'IsolationForest',
                self.trained_at.isoformat(),
                metrics['accuracy'],
                metrics['precision'],
                metrics['recall'],
                metrics['f1_score'],
                json.dumps(self.feature_names),
                json.dumps({'contamination': self.model.contamination, 'n_estimators': self.model.n_estimators}),
            )
        )
        logger.info(f"Model metadata saved to database")

    def load(self, model_version: Optional[str] = None):
        """
        Load a trained model from disk.

        Args:
            model_version: Specific version to load, or None for latest
        """
        if model_version:
            model_path = MODEL_DIR / f"fraud_model_{model_version}.pkl"
        else:
            # Load latest model
            models = sorted(MODEL_DIR.glob("fraud_model_*.pkl"))
            if not models:
                raise FileNotFoundError("No trained models found")
            model_path = models[-1]

        with open(model_path, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.scaler = data['scaler']
        self.feature_names = data['feature_names']
        self.model_version = data['model_version']
        self.trained_at = data['trained_at']

        logger.info(f"Model loaded: {model_path}")
