#!/usr/bin/env python3
"""
ML Model Predictor
Use trained ML model for enhanced predictions
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import pickle

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class MLPredictor:
    """Use ML model to enhance predictions"""
    
    def __init__(self):
        self.models_dir = PROJECT_ROOT / 'ml_models' / 'saved'
        self.model = None
        self.scaler = None
        self.meta = None
        self.is_loaded = False
        
        # Try to load model
        self._load_model()
    
    def _load_model(self):
        """Load saved model and scaler"""
        model_file = self.models_dir / 'best_model.pkl'
        scaler_file = self.models_dir / 'scaler.pkl'
        meta_file = self.models_dir / 'model_meta.pkl'
        
        if not model_file.exists():
            return False
        
        try:
            with open(model_file, 'rb') as f:
                self.model = pickle.load(f)
            
            with open(scaler_file, 'rb') as f:
                self.scaler = pickle.load(f)
            
            if meta_file.exists():
                with open(meta_file, 'rb') as f:
                    self.meta = pickle.load(f)
            
            self.is_loaded = True
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict(self, game_data):
        """
        Predict probability of going over
        
        Args:
            game_data: dict with prediction features
        
        Returns:
            dict with ML prediction results
        """
        if not self.is_loaded:
            return {
                'ml_available': False,
                'ml_probability': None,
                'ml_prediction': None
            }
        
        # Prepare features
        features = pd.DataFrame([{
            'minimum_total': game_data.get('minimum_total', 140),
            'expected_total': game_data.get('expected_total', 145),
            'buffer': game_data.get('buffer', 5),
            'confidence_pct': game_data.get('confidence_pct', 75),
            'offensive_score': game_data.get('offensive_score', 15),
            'pace_score': game_data.get('pace_score', 12),
            'form_score': game_data.get('form_score', 10),
            'rest_score': game_data.get('rest_score', 5),
        }])
        
        # Scale
        features_scaled = self.scaler.transform(features)
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        
        # Get probability if available
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(features_scaled)[0]
            over_probability = probabilities[1]  # Probability of class 1 (over)
        else:
            over_probability = float(prediction)
        
        return {
            'ml_available': True,
            'ml_probability': round(over_probability * 100, 1),
            'ml_prediction': 'OVER' if prediction == 1 else 'UNDER',
            'ml_model': self.meta.get('model_name', 'unknown') if self.meta else 'unknown'
        }
    
    def enhance_predictions(self, predictions_df):
        """Add ML predictions to existing predictions DataFrame"""
        if not self.is_loaded:
            print("ML model not available - skipping enhancement")
            return predictions_df
        
        print("Enhancing predictions with ML model...")
        
        ml_probs = []
        ml_preds = []
        
        for _, row in predictions_df.iterrows():
            result = self.predict(row.to_dict())
            ml_probs.append(result['ml_probability'])
            ml_preds.append(result['ml_prediction'])
        
        predictions_df['ml_probability'] = ml_probs
        predictions_df['ml_prediction'] = ml_preds
        
        # Create combined confidence (average of rule-based and ML)
        predictions_df['combined_confidence'] = (
            predictions_df['confidence_pct'] + predictions_df['ml_probability']
        ) / 2
        
        return predictions_df


def main():
    """Test the ML predictor"""
    predictor = MLPredictor()
    
    print("=" * 70)
    print("ML PREDICTOR TEST")
    print("=" * 70)
    
    if not predictor.is_loaded:
        print("\nNo trained model available")
        print("Run train_model.py first")
        return
    
    print(f"\nModel loaded: {predictor.meta.get('model_name', 'unknown')}")
    print(f"Trained at: {predictor.meta.get('trained_at', 'unknown')}")
    
    # Test prediction
    test_game = {
        'minimum_total': 140.5,
        'expected_total': 155.0,
        'buffer': 14.5,
        'confidence_pct': 82.5,
        'offensive_score': 25,
        'pace_score': 20,
        'form_score': 16,
        'rest_score': 7
    }
    
    result = predictor.predict(test_game)
    
    print("\nTest Prediction:")
    print(f"  ML Probability: {result['ml_probability']}%")
    print(f"  ML Prediction: {result['ml_prediction']}")


if __name__ == "__main__":
    main()
