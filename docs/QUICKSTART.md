# Quick Start Guide

## 1. Verify Data (2 minutes)
```bash
cd Trust_ai_chain

# Check if CSV files are in place
ls data/raw/heart/         # Should show: heart_disease_uci.csv
ls data/raw/diabetes/      # Should show: diabetes.csv
ls data/raw/asthma/        # Should show: asthma.csv
ls data/raw/liver/         # Should show: indian_liver_patient.csv
ls data/raw/parkinson/     # Should show: parkinsons.csv
```

## 2. Retrain Models (Optional, ~2 minutes)
```bash
# Train on CSV datasets and save models
python ai/training/train_csv_datasets.py

# Verify models created
ls backend/app/ai/artifacts/*.pkl   # Should show 5 .pkl files
```

## 3. Start Docker (30 seconds)
```bash
# Start all services
docker compose up -d

# Wait 10-30 seconds for initialization

# Verify services running
docker compose ps
```

## 4. Access Application (Instant)
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **MinIO**: http://localhost:9001

## 5. Test & Validate (5 minutes)
```bash
# Run comprehensive validation
python test_setup.py

# Expected: All checks should show ✓ PASS
```

## 6. Run a Prediction

### Option A: Via FastAPI Docs
1. Go to http://localhost:8000/docs
2. Find `/api/v1/predictions` endpoint
3. Click "Try it out"
4. Paste test data below and execute

### Option B: Via cURL
```bash
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "disease_key": "heart",
    "patient_id": "test_patient",
    "doctor_id": "test_doctor",
    "features": {
      "age": 45,
      "sex": 1,
      "cp": 1,
      "trestbps": 130,
      "chol": 250,
      "fbs": 0,
      "restecg": 1,
      "thalach": 150,
      "exang": 0,
      "oldpeak": 2.5,
      "slope": 1,
      "ca": 0,
      "thal": 3
    }
  }'
```

## 7. View Logs (Debugging)
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f postgres
docker compose logs -f minio
```

## 8. Stop Services (Cleanup)
```bash
# Stop all services
docker compose stop

# Stop and remove containers
docker compose down

# Stop, remove containers AND volumes (full reset)
docker compose down -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API not responding | Wait 15-30 seconds, services initializing |
| Models not found | Run `python ai/training/train_csv_datasets.py` |
| Docker not found | Install Docker Desktop |
| Permission denied | Run with `sudo` or add user to docker group |
| Port already in use | Change ports in docker-compose.yml |

## What's Included

✅ **5 Trained ML Models** - Heart, Diabetes, Asthma, Liver, Parkinson
✅ **Model Persistence** - Models saved as pickle files for quick loading
✅ **Backend API** - FastAPI with endpoints for predictions
✅ **Frontend** - React/Vite dashboard for testing
✅ **Database** - PostgreSQL for storing predictions
✅ **Object Storage** - MinIO for medical images
✅ **Validation** - Comprehensive test script included
✅ **Documentation** - Complete setup and deployment guides

## Model Performance

| Disease | Accuracy | AUC |
|---------|----------|-----|
| Heart | 91% | 0.912 |
| Parkinson | 92% | 0.915 |
| Diabetes | 82% | 0.812 |
| Asthma | 81% | 0.807 |
| Liver | 70% | 0.698 |

## Next Steps

1. ✅ Data verified
2. ✅ Models trained
3. ✅ Docker running
4. ✅ API accessible
5. → Make predictions!

---

**Need help?** Check `DOCKER_RUN_GUIDE.md` for detailed instructions.
