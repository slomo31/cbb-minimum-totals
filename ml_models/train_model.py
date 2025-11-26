#!/usr/bin/env python3
"""
ML Model Trainer
Train machine learning models for totals prediction (optional enhancement)
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import pickle

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.season_config import DATA_DIR, OUTPUT_ARCHIVE_DIR

# ML libraries - optional
try:
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    ML_AVAILABLE = True
except ImportError:
    print("scikit-learn not installed. Run: pip install scikit-learn")
    ML_AVAILABLE = False


class TotalsModelTrainer:
    """Train ML models for over/under prediction"""
    
    def __init__(self):
        self.data_dir = PROJECT_ROOT / DATA_DIR
        self.models_dir = PROJECT_ROOT / 'ml_models' / 'saved'
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.scaler = None
        self.models = {}
        self.best_model = None
        self.best_model_name = None
        
    def prepare_features(self, df):
        """Prepare features from tracking/backtest data"""
        features = []
        labels = []
        
        for _, row in df.iterrows():
            # Skip rows without results
            if row.get('result') not in ['WIN', 'LOSS'] and row.get('went_over') is None:
                continue
            
            # Build feature vector
            feature = {
                'minimum_total': row.get('minimum_total', 140),
                'expected_total': row.get('expected_total', 145),
                'buffer': row.get('buffer', 5),
                'confidence_pct': row.get('confidence_pct', row.get('confidence', 75)),
                'offensive_score': row.get('offensive_score', 15),
                'pace_score': row.get('pace_score', 12),
                'form_score': row.get('form_score', 10),
                'rest_score': row.get('rest_score', 5),
            }
            
            features.append(feature)
            
            # Label: 1 = went over (WIN), 0 = went under (LOSS)
            if row.get('result') == 'WIN' or row.get('went_over') == True:
                labels.append(1)
            else:
                labels.append(0)
        
        return pd.DataFrame(features), np.array(labels)
    
    def train(self, training_data):
        """Train multiple models and select the best"""
        if not ML_AVAILABLE:
            print("ML libraries not available")
            return None
        
        # Prepare features
        X, y = self.prepare_features(training_data)
        
        if len(X) < 50:
            print(f"Not enough training data ({len(X)} samples). Need at least 50.")
            return None
        
        print(f"Training on {len(X)} samples...")
        print(f"Class distribution: {sum(y)} wins, {len(y) - sum(y)} losses")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Define models
        model_configs = {
            'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingClassifier(n_estimators=100, random_state=42)
        }
        
        # Train and evaluate each model
        results = {}
        
        for name, model in model_configs.items():
            print(f"\nTraining {name}...")
            
            # Train
            model.fit(X_train_scaled, y_train)
            
            # Predict
            y_pred = model.predict(X_test_scaled)
            
            # Evaluate
            accuracy = accuracy_score(y_test, y_pred)
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            
            results[name] = {
                'model': model,
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
            
            print(f"  Accuracy: {accuracy:.2%}")
            print(f"  CV Mean: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")
            
            self.models[name] = model
        
        # Select best model
        best_name = max(results, key=lambda x: results[x]['cv_mean'])
        self.best_model = results[best_name]['model']
        self.best_model_name = best_name
        
        print(f"\n✅ Best model: {best_name}")
        print(f"   CV Accuracy: {results[best_name]['cv_mean']:.2%}")
        
        # Save best model
        self.save_model()
        
        return results
    
    def save_model(self):
        """Save the best model and scaler"""
        if self.best_model is None:
            return
        
        model_file = self.models_dir / 'best_model.pkl'
        scaler_file = self.models_dir / 'scaler.pkl'
        
        with open(model_file, 'wb') as f:
            pickle.dump(self.best_model, f)
        
        with open(scaler_file, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        # Save metadata
        meta = {
            'model_name': self.best_model_name,
            'trained_at': datetime.now().isoformat(),
            'features': ['minimum_total', 'expected_total', 'buffer', 'confidence_pct',
                        'offensive_score', 'pace_score', 'form_score', 'rest_score']
        }
        
        meta_file = self.models_dir / 'model_meta.pkl'
        with open(meta_file, 'wb') as f:
            pickle.dump(meta, f)
        
        print(f"Model saved to {model_file}")
    
    def load_model(self):
        """Load saved model"""
        model_file = self.models_dir / 'best_model.pkl'
        scaler_file = self.models_dir / 'scaler.pkl'
        
        if not model_file.exists():
            print("No saved model found")
            return False
        
        with open(model_file, 'rb') as f:
            self.best_model = pickle.load(f)
        
        with open(scaler_file, 'rb') as f:
            self.scaler = pickle.load(f)
        
        print("Model loaded successfully")
        return True


def main():
    """Train models using backtest or tracking data"""
    trainer = TotalsModelTrainer()
    
    print("=" * 70)
    print("ML MODEL TRAINER")
    print("=" * 70)
    
    # Try to load backtest results first
    backtest_dir = PROJECT_ROOT / OUTPUT_ARCHIVE_DIR / 'backtests'
    backtest_files = list(backtest_dir.glob('backtest_results_*.csv'))
    
    if backtest_files:
        # Use most recent backtest
        latest = sorted(backtest_files)[-1]
        print(f"Loading training data from {latest}")
        training_data = pd.read_csv(latest)
        
        # Train models
        results = trainer.train(training_data)
        
        if results:
            print("\n" + "=" * 70)
            print("TRAINING COMPLETE")
            print("=" * 70)
    else:
        print("No backtest data available for training")
        print("Run historical_backtester.py first")


if __name__ == "__main__":
    main()
