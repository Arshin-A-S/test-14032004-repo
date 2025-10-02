import sys
sys.path.append('offline_sim')

# ✅ Import the class BEFORE loading joblib model
from app.offline_sim.enhanced_federated_train_eval import EnsembleAnomalyDetector
from app.components.fl_component import EnhancedFLComponent

print('🚀 Testing Enhanced FL Component...')

# Initialize the enhanced FL component
fl = EnhancedFLComponent()

# Test normal access patterns
print('\n📊 Testing Normal Access Patterns:')

normal_contexts = [
    {'location': 'chennai', 'device_id': 'laptop1', 'department': 'cs', 'hour': 10},
    {'location': 'mumbai', 'device_id': 'legion', 'department': 'cs', 'hour': 14},
    {'location': 'chennai', 'device_id': 'phone1', 'department': 'cs', 'hour': 9}
]

for i, context in enumerate(normal_contexts, 1):
    score = fl.score_access_enhanced(context)
    print(f'  Normal #{i}: {score:.4f} (Location: {context["location"]}, Device: {context["device_id"]})')

# Test suspicious access patterns
print('\n🚨 Testing Suspicious Access Patterns:')

suspicious_contexts = [
    {'location': 'unknown_country', 'device_id': 'suspicious_browser', 'department': 'external', 'hour': 3},
    {'location': 'blacklisted_region', 'device_id': 'tor_exit_node', 'department': 'unknown', 'hour': 2},
    {'location': 'suspicious_location', 'device_id': 'unknown_device', 'department': 'external', 'hour': 23}
]

for i, context in enumerate(suspicious_contexts, 1):
    score = fl.score_access_enhanced(context)
    print(f'  Suspicious #{i}: {score:.4f} (Location: {context["location"]}, Device: {context["device_id"]})')

# Get the current threshold
threshold = fl.model.get('decision', {}).get('threshold', 0.6)
print(f'\n🎯 Current threshold: {threshold:.4f}')

# Check if ensemble is loaded
if hasattr(fl, 'ensemble_detector') and fl.ensemble_detector:
    print('✅ Using Enhanced Ensemble Model!')
else:
    print('⚠️ Using Basic Fallback Model')