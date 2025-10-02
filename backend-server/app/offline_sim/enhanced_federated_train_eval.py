# offline_sim/enhanced_federated_train_eval.py
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from enhanced_features import create_enhanced_features

class EnsembleAnomalyDetector:
    def __init__(self):
        self.models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100, 
                max_depth=10, 
                random_state=42,
                class_weight='balanced'
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=100, 
                max_depth=6, 
                random_state=42
            ),
            'logistic_regression': LogisticRegression(
                random_state=42, 
                class_weight='balanced',
                max_iter=1000
            ),
            'isolation_forest': IsolationForest(
                contamination=0.15, 
                random_state=42
            ),
            'one_class_svm': OneClassSVM(
                kernel='rbf', 
                nu=0.15
            )
        }
        self.scaler = StandardScaler()
        self.weights = None
        self.feature_names = None
        
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare feature matrix from dataframe"""
        feature_cols = [
            'hour_sin', 'hour_cos', 'is_weekend', 'is_night', 'is_business_hours',
            'location_encoded', 'device_encoded', 'department_encoded',
            'location_frequency', 'device_frequency',
            'location_user_pattern', 'device_user_pattern', 'hour_user_pattern', 'label_user_pattern'
        ]
        
        self.feature_names = feature_cols
        return df[feature_cols].fillna(0).values
    
    def fit(self, df: pd.DataFrame):
        """Train ensemble of models"""
        print("🤖 Training Ensemble Anomaly Detector...")
        
        # Prepare enhanced features
        df_enhanced = create_enhanced_features(df)
        X = self.prepare_features(df_enhanced)
        y = (df_enhanced['label'] == 0).astype(int)  # 1 = anomaly, 0 = normal
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train supervised models
        supervised_models = ['random_forest', 'gradient_boosting', 'logistic_regression']
        unsupervised_models = ['isolation_forest', 'one_class_svm']
        
        # Train supervised models
        for name in supervised_models:
            print(f"  Training {name}...")
            self.models[name].fit(X_scaled, y)
        
        # Train unsupervised models (use only normal data)
        normal_data = X_scaled[y == 0]  # Only normal samples
        for name in unsupervised_models:
            print(f"  Training {name}...")
            self.models[name].fit(normal_data)
        
        # Learn ensemble weights via validation
        self._learn_ensemble_weights(X_scaled, y)
        
        print("✅ Ensemble training completed!")
    
    def _learn_ensemble_weights(self, X, y):
        """Learn optimal ensemble weights"""
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # Get predictions from each model on validation set
        val_predictions = {}
        
        # Supervised models
        for name in ['random_forest', 'gradient_boosting', 'logistic_regression']:
            if name == 'random_forest':
                val_predictions[name] = self.models[name].predict_proba(X_val)[:, 1]
            elif name == 'gradient_boosting':
                val_predictions[name] = self.models[name].predict_proba(X_val)[:, 1]
            else:  # logistic_regression
                val_predictions[name] = self.models[name].predict_proba(X_val)[:, 1]
        
        # Unsupervised models (convert to anomaly scores)
        iso_scores = self.models['isolation_forest'].score_samples(X_val)
        val_predictions['isolation_forest'] = 1 - ((iso_scores - iso_scores.min()) / 
                                                  (iso_scores.max() - iso_scores.min() + 1e-8))
        
        svm_scores = self.models['one_class_svm'].score_samples(X_val)
        val_predictions['one_class_svm'] = 1 - ((svm_scores - svm_scores.min()) / 
                                                (svm_scores.max() - svm_scores.min() + 1e-8))
        
        # Find optimal weights using ROC-AUC
        best_auc = 0
        best_weights = None
        
        # Grid search over weight combinations
        weight_combinations = [
            {'random_forest': 0.3, 'gradient_boosting': 0.3, 'logistic_regression': 0.2, 
             'isolation_forest': 0.1, 'one_class_svm': 0.1},
            {'random_forest': 0.4, 'gradient_boosting': 0.3, 'logistic_regression': 0.2, 
             'isolation_forest': 0.05, 'one_class_svm': 0.05},
            {'random_forest': 0.35, 'gradient_boosting': 0.35, 'logistic_regression': 0.25, 
             'isolation_forest': 0.025, 'one_class_svm': 0.025},
        ]
        
        for weights in weight_combinations:
            ensemble_pred = np.zeros(len(y_val))
            for model_name, weight in weights.items():
                ensemble_pred += weight * val_predictions[model_name]
            
            auc = roc_auc_score(y_val, ensemble_pred)
            if auc > best_auc:
                best_auc = auc
                best_weights = weights
        
        self.weights = best_weights
        print(f"  Best ensemble AUC: {best_auc:.4f}")
        print(f"  Optimal weights: {best_weights}")
    
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Get ensemble anomaly scores"""
        df_enhanced = create_enhanced_features(df)
        X = self.prepare_features(df_enhanced)
        X_scaled = self.scaler.transform(X)
        
        # Get predictions from each model
        predictions = {}
        
        # Supervised models
        for name in ['random_forest', 'gradient_boosting', 'logistic_regression']:
            predictions[name] = self.models[name].predict_proba(X_scaled)[:, 1]
        
        # Unsupervised models
        iso_scores = self.models['isolation_forest'].score_samples(X_scaled)
        predictions['isolation_forest'] = 1 - ((iso_scores - iso_scores.min()) / 
                                              (iso_scores.max() - iso_scores.min() + 1e-8))
        
        svm_scores = self.models['one_class_svm'].score_samples(X_scaled)
        predictions['one_class_svm'] = 1 - ((svm_scores - svm_scores.min()) / 
                                           (svm_scores.max() - svm_scores.min() + 1e-8))
        
        # Ensemble prediction
        ensemble_pred = np.zeros(X_scaled.shape[0])
        for model_name, weight in self.weights.items():
            ensemble_pred += weight * predictions[model_name]
        
        return ensemble_pred

def enhanced_federated_training(events_path: str, output_model_path: str):
    """Enhanced federated training with ensemble methods"""
    
    # Load and enhance data
    df = pd.read_csv(events_path)
    
    # Train ensemble detector
    detector = EnsembleAnomalyDetector()
    detector.fit(df)
    
    # Evaluate on test set
    train_df, test_df = train_test_split(df, test_size=0.3, random_state=42)
    
    test_scores = detector.predict_proba(test_df)
    test_labels = (test_df['label'] == 0).astype(int)
    
    # Calculate metrics
    auc_score = roc_auc_score(test_labels, test_scores)
    
    print(f"\nENSEMBLE PERFORMANCE:")
    print(f"ROC-AUC: {auc_score:.4f}")
    print(f"Improvement: {((auc_score - 0.557) / 0.557 * 100):.1f}% over baseline")
    
    # Save enhanced model
    enhanced_model = {
        "version": 3,
        "schema": "ensemble-anomaly-model",
        "ensemble_weights": detector.weights,
        "feature_names": detector.feature_names,
        "performance": {
            "roc_auc": float(auc_score),
            "test_samples": len(test_df)
        }
    }
    
    with open(output_model_path, 'w') as f:
        json.dump(enhanced_model, f, indent=2)
    
    # Save the trained detector
    joblib.dump(detector, 'trained_ensemble_detector.pkl')
    return detector, auc_score

if __name__ == "__main__":
    # Generate enhanced synthetic data
    print("📊 Generating enhanced synthetic data...")
    # Run your enhanced_synthetic_data_gen.py first
    
    # Train ensemble model
    detector, auc = enhanced_federated_training(
        "offline_sim/data/synthetic_events.csv",
        "enhanced_fl_model.json"
    )
    
    print(f"\n✅ Enhanced model saved with {auc:.4f} ROC-AUC!")
