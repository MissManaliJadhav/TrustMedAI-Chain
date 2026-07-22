#!/usr/bin/env python
import sys
sys.path.insert(0, r"c:\Users\dbatu\OneDrive\Desktop\Trust_ai_chain")

try:
    from ai.training.production_disease_pipeline import compute_aecs_from_vectors
    print("✓ Import successful")
    
    import numpy as np
    result = compute_aecs_from_vectors(np.array([1.0, 0.0]), np.array([1.0, 0.0]))
    print(f"✓ Function call successful: {result}")
    print(f"✓ Return type: {type(result)}, length: {len(result) if isinstance(result, tuple) else 'N/A'}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
