import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'app'))
from app.services.prediction import load_model
print('PYTHON', sys.version)
print('MODEL DIR', (Path(__file__).resolve().parent / 'app' / 'ai' / 'artifacts').resolve())
print('EYE_MODEL_PATH_EXISTS', (Path(__file__).resolve().parent / 'app' / 'ai' / 'artifacts' / 'eye_model.pkl').exists())
model = load_model('eye')
print('EYE MODEL', type(model), model is not None)
