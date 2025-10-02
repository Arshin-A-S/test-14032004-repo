#!/usr/bin/env python3
import os
import sys

# Generate enhanced data
os.system("python offline_sim/synthetic_data_gen.py --events 15000")

# Train ensemble model  
os.system("python offline_sim/enhanced_federated_train_eval.py")


