# backend/components/fl_component.py
"""
Simple federated-learning-like anomaly detector simulation.

Phase 1: we'll implement a lightweight local anomaly scorer:
- Each client computes an 'access vector' statistics (counts by hour, location, device)
- We simulate federated aggregation by averaging model parameters (here simple thresholds).
- For your project: FL will produce an anomaly score for an access event (0..1).
"""

import datetime
import random
import json
import os
from collections import defaultdict
import time
import joblib
import numpy as np
from offline_sim.enhanced_features import create_enhanced_features

class FLComponent:
    def __init__(self, model_path="fl_model.json"):
        self.model_path = model_path
        # model is just a small dict of normal means for attributes (toy)
        if os.path.exists(model_path):
            with open(model_path, "r") as f:
                self.model = json.load(f)
        else:
            self.model = {"location_scores": {}, "device_scores": {}, "global_threshold": 0.6}
            self._persist()

    def _persist(self):
        with open(self.model_path, "w") as f:
            json.dump(self.model, f)

    def client_train_and_report(self, local_stats):
        """
        Simulate client-side local training and send updates.
        local_stats: dict of counters, e.g. {"location": {"india": 10, "us":2}, "device": {"d1":11}}
        We'll convert into normalized scores and send to server aggregator (here we just update model)
        """
        # compute normalized location distribution
        loc = local_stats.get("location", {})
        total = sum(loc.values()) or 1
        for k,v in loc.items():
            self.model["location_scores"][k] = (self.model["location_scores"].get(k, 0) + v/total)/2

        dev = local_stats.get("device", {})
        totald = sum(dev.values()) or 1
        for k,v in dev.items():
            self.model["device_scores"][k] = (self.model["device_scores"].get(k, 0) + v/totald)/2

        # store
        self._persist()
        return True

    def score_access(self, context):
        """
        Score using the trained federated model with proper weighting and time buckets.
        """
        # Check if we have the new v2 model format
        if "learned" not in self.model:
            # Fallback to old scoring method for backward compatibility
            return self._score_access_old(context)
        
        # Extract context features
        loc = context.get("location")
        dev = context.get("device_id") or context.get("device")
        
        # Convert current hour to time bucket
        import datetime
        current_hour = datetime.datetime.now().hour
        time_bucket = self._hour_to_bucket(current_hour)
        
        # Get weights from trained model
        weights = self.model["decision"]["weights"]
        eps = self.model["decision"].get("eps", 1e-6)
        
        # Get learned success rates
        learned = self.model["learned"]
        global_rate = learned["global_success_rate"]
        
        loc_rate = learned["location_success_rate"].get(loc, global_rate)
        dev_rate = learned["device_success_rate"].get(dev, global_rate)
        time_rate = learned["time_success_rate"].get(time_bucket, global_rate)
        
        # Calculate risk scores (1 - success_rate)
        loc_risk = 1.0 - float(loc_rate)
        dev_risk = 1.0 - float(dev_rate)
        time_risk = 1.0 - float(time_rate)
        
        # Weighted combination
        score = (weights["location"] * loc_risk + 
                weights["device"] * dev_risk + 
                weights["time"] * time_risk)
        
        # Add small epsilon and clamp
        return max(0.0, min(1.0, float(score + eps)))

    def _hour_to_bucket(self, hour):
        """Convert hour to time bucket."""
        if 0 <= hour < 6:
            return "bucket_0_6"
        elif 6 <= hour < 12:
            return "bucket_6_12" 
        elif 12 <= hour < 18:
            return "bucket_12_18"
        else:
            return "bucket_18_24"
        
    def _score_access_old(self, context):
        """Fallback to old scoring method for backward compatibility."""
        # Use main score_access method if model has v2 format
        if "learned" in self.model:
            return self.score_access(context)
        
        # Handle old format only if it exists
        if "location_scores" not in self.model:
            return 0.5  # Default neutral score
            
        loc = context.get("location")
        dev = context.get("device_id")
        
        loc_score = 1.0 - self.model["location_scores"].get(loc, 0.0)
        dev_score = 1.0 - self.model["device_scores"].get(dev, 0.0)
        
        score = (loc_score + dev_score) / 2.0
        return max(0.0, min(1.0, score))



class EnhancedFLComponent(FLComponent):
    def __init__(self, model_path="enhanced_fl_model.json"):
        super().__init__(model_path)
        self.ensemble_detector = None
        self.load_ensemble_model()
    
    def load_ensemble_model(self):
        """Load the trained ensemble model"""
        try:
            self.ensemble_detector = joblib.load('trained_ensemble_detector.pkl')
            print("✅ Enhanced ensemble model loaded successfully")
        except Exception as e:
            print(f"Warning: Enhanced ensemble model not found ({e}), falling back to basic model")
    
    def score_access_enhanced(self, context):
        """Enhanced scoring using ensemble methods"""
        if self.ensemble_detector is None:
            return self._score_access_old(context)

        # Convert context to dataframe for feature engineering
        import pandas as pd
        current_hour = context.get('hour', datetime.datetime.now().hour)
        context_df = pd.DataFrame([{
            'hour': current_hour,
            'location': context.get('location', 'unknown'),
            'device': context.get('device_id', 'unknown'),
            'department': context.get('department', 'cs'),
            'client_id': context.get('user_id', 'unknown'),
            'ts': time.time(),
            'label': 1  # Assume normal for feature engineering
        }])

        # ✅ FIX: Apply enhanced feature engineering
        try:
            if create_enhanced_features is not None:
                context_df = create_enhanced_features(context_df)
                
                # ✅ CRITICAL FIX: Ensure user pattern columns exist before prediction
                required_pattern_cols = [
                    'location_user_pattern', 'device_user_pattern', 
                    'hour_user_pattern', 'label_user_pattern'
                ]
                for col in required_pattern_cols:
                    if col not in context_df.columns:
                        context_df[col] = 0  # Default for single-event inference
                
                print(f"Enhanced features created: {list(context_df.columns)}")
            else:
                print("Warning: Using basic features only")

            # Get ensemble prediction
            score = self.ensemble_detector.predict_proba(context_df)[0]
            return float(np.clip(score, 0.0, 1.0))

        except Exception as e:
            print(f"Ensemble scoring failed: {e}, falling back to basic scoring")
            return self.score_access(context)  # ✅ FIX: Use score_access instead of _score_access_old
