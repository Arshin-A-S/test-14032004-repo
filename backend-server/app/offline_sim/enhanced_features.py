# offline_sim/enhanced_features.py

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from datetime import datetime

def create_enhanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create enhanced features for better anomaly detection"""
    # Time-based features
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['is_weekend'] = df['ts'].apply(lambda x: datetime.fromtimestamp(x).weekday() >= 5)
    df['is_night'] = (df['hour'] <= 6) | (df['hour'] >= 22)
    df['is_business_hours'] = (df['hour'] >= 9) & (df['hour'] <= 17)

    # Behavioral features
    df['location_device_combo'] = df['location'] + '_' + df['device']
    df['location_dept_combo'] = df['location'] + '_' + df['department']

    # ✅ FIXED: User behavioral patterns (handle single-row case)
    if len(df) == 1:
        # For single-event inference, use defaults
        df['location_user_pattern'] = 1  # Single unique location
        df['device_user_pattern'] = 1    # Single unique device
        df['hour_user_pattern'] = 0      # No standard deviation for single value
        df['label_user_pattern'] = 1     # Assume normal for single event
    else:
        # For training data with multiple rows per user
        user_stats = df.groupby('client_id').agg({
            'location': lambda x: len(x.unique()),
            'device': lambda x: len(x.unique()),
            'hour': 'std',
            'label': 'mean'
        }).add_suffix('_user_pattern')
        df = df.merge(user_stats, left_on='client_id', right_index=True, how='left')
        
        # Fill any remaining NaNs
        df['location_user_pattern'] = df['location_user_pattern'].fillna(1)
        df['device_user_pattern'] = df['device_user_pattern'].fillna(1)
        df['hour_user_pattern'] = df['hour_user_pattern'].fillna(0)
        df['label_user_pattern'] = df['label_user_pattern'].fillna(1)

    # Location frequency (rare locations are more suspicious)
    loc_freq = df['location'].value_counts(normalize=True)
    df['location_frequency'] = df['location'].map(loc_freq).fillna(0.1)  # Default for unknown

    # Device frequency
    dev_freq = df['device'].value_counts(normalize=True)
    df['device_frequency'] = df['device'].map(dev_freq).fillna(0.1)  # Default for unknown

    # Encode categorical variables
    le_loc = LabelEncoder()
    le_dev = LabelEncoder()
    le_dept = LabelEncoder()
    
    df['location_encoded'] = le_loc.fit_transform(df['location'].astype(str))
    df['device_encoded'] = le_dev.fit_transform(df['device'].astype(str))
    df['department_encoded'] = le_dept.fit_transform(df['department'].astype(str))

    return df

