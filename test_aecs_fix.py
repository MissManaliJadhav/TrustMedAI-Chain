#!/usr/bin/env python
"""Quick test to verify AECS computation works with real data structures."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import numpy as np
from app.services.adversarial import calculate_aecs, compute_aecs_from_vectors

def test_aecs_with_real_feature_data():
    """Test AECS computation with realistic feature data."""
    
    # Simulate explanation dict
    explanation = {
        "shap": {
            "available": True,
            "method": "SHAP",
            "feature_importance": [0.15, 0.25, 0.10, 0.05],  # 4 features
        }
    }
    
    # Simulate patient_attack dict (what _tabular_patient_attack returns)
    patient_attack = {
        "modality": "tabular",
        "status": "Evaluated",
        "original_values": {
            "age": 45.0,
            "blood_pressure": 120.0,
            "cholesterol": 200.0,
            "glucose": 100.0,
        },
        "adversarial_values": {
            "age": 46.0,
            "blood_pressure": 125.0,
            "cholesterol": 205.0,
            "glucose": 105.0,
        },
    }
    
    # Calculate AECS
    aecs, reason, distance = calculate_aecs(
        confidence=0.85,
        explanation=explanation,
        patient_attack=patient_attack
    )
    
    print(f"✓ AECS calculation succeeded")
    print(f"  AECS value: {aecs}")
    print(f"  Reason: {reason}")
    print(f"  Distance: {distance}")
    
    if aecs is not None:
        assert 0.0 <= aecs <= 1.0, f"AECS {aecs} not in [0, 1]"
        print(f"✓ AECS in valid range [0, 1]")
    else:
        print(f"✗ AECS is None: {reason}")
        return False
    
    return True

def test_aecs_with_dict_importance():
    """Test with feature_importance as list of dicts."""
    
    explanation = {
        "shap": {
            "available": True,
            "method": "SHAP",
            "feature_importance": [
                {"feature": "age", "importance": 0.15},
                {"feature": "blood_pressure", "importance": 0.25},
                {"feature": "cholesterol", "importance": 0.10},
                {"feature": "glucose", "importance": 0.05},
            ],
        }
    }
    
    patient_attack = {
        "original_values": {
            "age": 45.0,
            "blood_pressure": 120.0,
            "cholesterol": 200.0,
            "glucose": 100.0,
        },
        "adversarial_values": {
            "age": 46.0,
            "blood_pressure": 125.0,
            "cholesterol": 205.0,
            "glucose": 105.0,
        },
    }
    
    aecs, reason, distance = calculate_aecs(
        confidence=0.85,
        explanation=explanation,
        patient_attack=patient_attack
    )
    
    print(f"✓ AECS with dict importance succeeded")
    print(f"  AECS value: {aecs}")
    if aecs is not None:
        assert 0.0 <= aecs <= 1.0, f"AECS {aecs} not in [0, 1]"
    else:
        print(f"✗ AECS is None: {reason}")
        return False
    
    return True

def test_aecs_unavailable():
    """Test when AECS cannot be computed."""
    
    aecs, reason, distance = calculate_aecs(
        confidence=0.85,
        patient_attack=None  # No attack data
    )
    
    print(f"✓ Handled missing attack data")
    print(f"  AECS: {aecs}")
    print(f"  Reason: {reason}")
    assert aecs is None, "Should return None when attack data missing"
    assert reason is not None, "Should provide a reason"
    
    return True

if __name__ == "__main__":
    print("\n=== Testing AECS Computation ===\n")
    
    try:
        test1 = test_aecs_with_real_feature_data()
        print()
        test2 = test_aecs_with_dict_importance()
        print()
        test3 = test_aecs_unavailable()
        
        if all([test1, test2, test3]):
            print("\n✓ All AECS tests passed!")
        else:
            print("\n✗ Some tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
