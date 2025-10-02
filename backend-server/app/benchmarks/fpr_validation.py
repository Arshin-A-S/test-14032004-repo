# benchmarks/fpr_validation.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.fl_component import FLComponent

def validate_fpr():
    """Calculate actual false positive rate"""
    fl_comp = FLComponent()
    
    # Create test data with known labels
    test_data = [
        # Normal cases (label=0)
        ({"location": "chennai", "device_id": "laptop1"}, 0),
        ({"location": "mumbai", "device_id": "legion"}, 0),
        ({"location": "chennai", "device_id": "phone1"}, 0),
        # Repeat normal patterns
        *[({"location": "chennai", "device_id": "laptop1"}, 0) for _ in range(100)],
        
        # Anomalous cases (label=1) 
        ({"location": "unknown_city", "device_id": "suspicious"}, 1),
        ({"location": "foreign", "device_id": "hacker"}, 1),
        *[({"location": "unknown", "device_id": "unknown"}, 1) for _ in range(20)]
    ]
    
    # Score all test cases
    predictions = []
    true_labels = []
    threshold = 0.65  # From your fl_model.json
    
    for context, true_label in test_data:
        score = fl_comp.score_access(context)
        predicted_anomaly = 1 if score >= threshold else 0
        
        predictions.append(predicted_anomaly)
        true_labels.append(true_label)
    
    # Calculate FPR
    false_positives = sum((true_labels[i] == 0) and (predictions[i] == 1) 
                         for i in range(len(true_labels)))
    true_negatives = sum(label == 0 for label in true_labels)
    
    fpr = false_positives / max(1, true_negatives)
    
    return {
        "false_positive_rate": fpr,
        "threshold_used": threshold,
        "total_samples": len(true_labels),
        "false_positives": false_positives,
        "true_negatives": true_negatives
    }

if __name__ == "__main__":
    print("🔍 Validating False Positive Rate...")
    
    fpr_results = validate_fpr()
    
    print(f"📊 False Positive Rate: {fpr_results['false_positive_rate']:.1%}")
    print(f"📊 Threshold Used: {fpr_results['threshold_used']}")
    print(f"📊 Test Samples: {fpr_results['total_samples']}")
