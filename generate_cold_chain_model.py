"""
generate_cold_chain_model.py
Script to generate synthetic cold chain sensor data and train a Random Forest 
classifier to predict shipment integrity status.

Status Mapping for VeriDrip contract:
- Status 1: Normal/Intact (no breach detected)
- Status 2: Warning (minor deviations detected)
- Status 3: Breach (significant violation requiring insurance claim)

The model analyzes temperature variance, humidity, vibration, shipment duration,
door openings, and GPS deviations to assess cold chain integrity.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import joblib
import random

# ------------------------------
# Step 1: Generate Synthetic Dataset
# ------------------------------
def generate_cold_chain_dataset(n_samples=10000):
    np.random.seed(42)
    random.seed(42)
    
    data = []
    
    for _ in range(n_samples):
        # Feature 1: Temperature Variance (标准差)
        # Normal shipments have low variance (< 1.5°C), breached shipments have high variance
        integrity_status = random.choices([1, 2, 3], weights=[0.7, 0.15, 0.15])[0]
        
        if integrity_status == 1:  # Normal
            temp_variance = np.random.uniform(0.2, 1.5)
            avg_humidity = np.random.uniform(45, 65)
            max_vibration = np.random.uniform(0.01, 0.08)
            duration_hours = np.random.uniform(12, 48)
            door_open_count = np.random.randint(0, 5)
            gps_deviation_km = np.random.uniform(0, 5)
        elif integrity_status == 2:  # Warning
            temp_variance = np.random.uniform(1.5, 3.0)
            avg_humidity = np.random.uniform(40, 80)
            max_vibration = np.random.uniform(0.08, 0.2)
            duration_hours = np.random.uniform(24, 72)
            door_open_count = np.random.randint(2, 10)
            gps_deviation_km = np.random.uniform(5, 20)
        else:  # Breach
            temp_variance = np.random.uniform(3.0, 8.0)
            avg_humidity = np.random.uniform(30, 90)
            max_vibration = np.random.uniform(0.2, 0.6)
            duration_hours = np.random.uniform(36, 120)
            door_open_count = np.random.randint(5, 30)
            gps_deviation_km = np.random.uniform(20, 100)
        
        # Add realistic noise to features
        temp_variance += np.random.normal(0, 0.1)
        avg_humidity += np.random.normal(0, 2)
        max_vibration += np.random.normal(0, 0.02)
        
        data.append([
            temp_variance, avg_humidity, max_vibration, 
            duration_hours, door_open_count, gps_deviation_km,
            integrity_status
        ])
    
    columns = [
        'temperature_variance', 'avg_humidity', 'max_vibration',
        'duration_hours', 'door_open_count', 'gps_deviation_km',
        'integrity_status'
    ]
    
    df = pd.DataFrame(data, columns=columns)
    return df

# ------------------------------
# Step 2: Prepare Features and Target
# ------------------------------
def prepare_features_target(df):
    feature_columns = [
        'temperature_variance', 'avg_humidity', 'max_vibration',
        'duration_hours', 'door_open_count', 'gps_deviation_km'
    ]
    X = df[feature_columns]
    y = df['integrity_status']
    return X, y

# ------------------------------
# Step 3: Train the Model
# ------------------------------
def train_model(X_train, y_train):
    # Scale features for better performance
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Random Forest Classifier (provides good performance and probability estimates)
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    
    model.fit(X_train_scaled, y_train)
    return model, scaler

# ------------------------------
# Step 4: Evaluate Model
# ------------------------------
def evaluate_model(model, scaler, X_test, y_test):
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)
    
    print("\n=== Model Performance ===")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Warning', 'Breach']))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Calculate confidence scores (maximum probability)
    confidence_scores = y_pred_proba.max(axis=1)
    print(f"\nConfidence Score Range: {confidence_scores.min():.4f} - {confidence_scores.max():.4f}")
    print(f"Mean Confidence: {confidence_scores.mean():.4f}")
    
    return y_pred, confidence_scores

# ------------------------------
# Step 5: Save the Model (pkl file)
# ------------------------------
def save_model(model, scaler, filename="cold_chain_model.pkl"):
    # Save both the model and the scaler together (scaler needed for prediction)
    full_model = {
        'classifier': model,
        'scaler': scaler,
        'feature_columns': [
            'temperature_variance', 'avg_humidity', 'max_vibration',
            'duration_hours', 'door_open_count', 'gps_deviation_km'
        ],
        'status_map': {0: 1, 1: 2, 2: 3}  # Model output to contract status
    }
    joblib.dump(full_model, filename)
    print(f"\n✅ Model saved to {filename}")

# ------------------------------
# Main Execution
# ------------------------------
if __name__ == "__main__":
    # 1. Generate dataset
    print("Generating synthetic cold chain dataset...")
    df = generate_cold_chain_dataset(n_samples=10000)
    print(f"Dataset shape: {df.shape}")
    print(df.head())
    
    # 2. Prepare features and target
    X, y = prepare_features_target(df)
    
    # 3. Split into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTraining samples: {X_train.shape[0]}")
    print(f"Testing samples: {X_test.shape[0]}")
    
    # 4. Train model
    print("\nTraining Random Forest classifier...")
    model, scaler = train_model(X_train, y_train)
    
    # 5. Evaluate model
    evaluate_model(model, scaler, X_test, y_test)
    
    # 6. Save model with scaler
    save_model(model, scaler)
    
    print("\n🎉 Model generation complete! You can now use it with your oracle.py")
    print("To use with oracle.py:")
    print("  1. Place 'cold_chain_model.pkl' in the project root directory")
    print("  2. Ensure 'AI_MODEL_PATH=./cold_chain_model.pkl' is in .env")
    print("  3. Run python3 oracle.py (it will automatically use the real model)")