# TrustMedAI - Docker Setup & Execution Guide

## Prerequisites
- Docker Desktop installed and running
- Docker Compose installed (usually included with Docker Desktop)
- Ensure Docker daemon is running

## Project Structure Summary
```
Trust_ai_chain/
├── backend/           # FastAPI application (Python)
├── frontend/          # React/Vite application (TypeScript)
├── ai/               # AI training scripts
│   └── training/
│       ├── train_csv_datasets.py    # Trains models on CSV data
│       └── inspect_datasets.py      # Analyzes raw datasets
├── data/
│   ├── raw/          # Raw data (CSV files and image folders)
│   │   ├── heart/, diabetes/, asthma/, etc. (datasets)
│   │   └── pneumonia/, eye/, tuberculosis/, brain_tumor/ (image folders - empty)
│   ├── train/        # Training splits
│   ├── validation/    # Validation splits
│   └── test/         # Test splits
└── backend/app/ai/artifacts/
    └── *_model.pkl, *_metrics.json  # Trained models & metrics
```

## Step-by-Step Setup

### 1. Verify Datasets are Present
```bash
cd Trust_ai_chain

# Check if CSV files exist
ls data/raw/heart/       # Should show: heart_disease_uci.csv
ls data/raw/diabetes/    # Should show: diabetes.csv
ls data/raw/asthma/      # Should show: asthma.csv
ls data/raw/liver/       # Should show: indian_liver_patient.csv
ls data/raw/parkinson/   # Should show: parkinsons.csv
```

### 2. Train Models (Optional - Already Done)
If you want to retrain models on CSV datasets:

```bash
python ai/training/train_csv_datasets.py
```

This will:
- Load CSV datasets from `data/raw/<disease_key>/`
- Split into 70% train, 15% validation, 15% test
- Train RandomForestClassifier (80 estimators)
- Save trained models to `backend/app/ai/artifacts/<disease_key>_model.pkl`
- Save metrics to `backend/app/ai/artifacts/<disease_key>_csv_metrics.json`

### 3. Build Docker Images
```bash
docker compose build --no-cache
```

Expected output:
```
[+] Building 1.2s (25/25) FINISHED
 => [postgres base] ...
 => [minio base] ...
 => [backend base] ...
 => [frontend base] ...
```

### 4. Start Docker Services
```bash
docker compose up -d
```

Services that will start:
- **PostgreSQL** (port 5432) - Database
- **MinIO** (port 9000/9001) - Object storage
- **Backend** (port 8000) - FastAPI application
- **Frontend** (port 3000) - React web application

### 5. Verify Services are Running
```bash
docker compose ps
```

Expected output (all services should show "Up"):
```
NAME          IMAGE                    STATUS
backend       project-backend:latest   Up 5 seconds
frontend      project-frontend:latest  Up 5 seconds
postgres      postgres:16-alpine       Up 10 seconds
minio         minio:latest             Up 10 seconds
```

### 6. Check Service Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f postgres
docker compose logs -f minio
```

### 7. Access the Application

#### Backend API (FastAPI)
- URL: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Frontend
- URL: http://localhost:3000

#### MinIO Console
- URL: http://localhost:9001
- Login: trustmedai / trustmedai123 (default credentials)

#### PostgreSQL
- Host: localhost
- Port: 5432
- User: postgres
- Password: 2003 (from docker-compose.yml)
- Database: trustmedai

## Testing the Prediction API

### Option 1: Using FastAPI Docs
1. Navigate to http://localhost:8000/docs
2. Click on `/api/v1/predictions` endpoint
3. Click "Try it out"
4. Enter sample data and execute

### Option 2: Using cURL

```bash
# Create a prediction
curl -X POST http://localhost:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "disease_key": "heart",
    "patient_id": "patient_001",
    "doctor_id": "doctor_001",
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
    },
    "doctor_notes": "Standard cardiac screening"
  }'
```

### Option 3: Using Python

```python
import httpx

async def test_prediction():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/predictions",
            json={
                "disease_key": "heart",
                "patient_id": "patient_001",
                "doctor_id": "doctor_001",
                "features": {"age": 45, "sex": 1, ...},
                "doctor_notes": "Test"
            },
            headers={"Authorization": "Bearer YOUR_TOKEN"}
        )
        print(response.json())
```

## Model Information

### Trained Models
Models are loaded automatically from `backend/app/ai/artifacts/`:

| Disease | Model File | Status | Accuracy |
|---------|-----------|--------|----------|
| heart | heart_model.pkl | ✓ Trained | See metrics |
| diabetes | diabetes_model.pkl | ✓ Trained | See metrics |
| asthma | asthma_model.pkl | ✓ Trained | See metrics |
| parkinson | parkinson_model.pkl | ✓ Trained | See metrics |
| liver | liver_model.pkl | ✓ Trained | See metrics |
| pneumonia | - | Not trained | Uses mock scoring |
| eye | - | Not trained | Uses mock scoring |
| tuberculosis | - | Not trained | Uses mock scoring |
| brain_tumor | - | Not trained | Uses mock scoring |

### Viewing Model Metrics
Metrics are available in JSON files:
```bash
cat backend/app/ai/artifacts/heart_csv_metrics.json
```

Shows: accuracy, precision, recall, f1_score, auc, num_classes, train_rows, validation_rows, test_rows

## Troubleshooting

### Docker Services Won't Start
```bash
# Check Docker status
docker info

# Check logs
docker compose logs

# Restart services
docker compose restart

# Full reset
docker compose down -v
docker compose up -d
```

### Backend Connection Issues
```bash
# Check if backend is running
docker ps | grep backend

# Check backend logs
docker compose logs backend

# Test connectivity
curl http://localhost:8000/api/v1/health  # Or your health check endpoint
```

### Database Connection Error
```bash
# PostgreSQL health check
docker compose exec postgres psql -U postgres -d trustmedai -c "SELECT 1"

# Reset database
docker compose down -v
docker compose up -d
```

### Model Loading Issues
```bash
# Verify model files exist
docker compose exec backend ls -la app/ai/artifacts/

# Check if models are accessible
docker compose exec backend python -c "import pickle; pickle.load(open('app/ai/artifacts/heart_model.pkl', 'rb'))"
```

## Stopping Services

```bash
# Stop all services (containers still exist)
docker compose stop

# Stop and remove containers
docker compose down

# Stop, remove containers and volumes (full reset)
docker compose down -v
```

## Adding New Image Datasets

To train on medical images:

1. **Place images in appropriate folders:**
   ```
   data/raw/pneumonia/
   ├── normal/
   │   ├── image1.jpg
   │   ├── image2.jpg
   │   └── ...
   └── pneumonia/
       ├── image1.jpg
       ├── image2.jpg
       └── ...
   ```

2. **Run training (will auto-detect image folders):**
   ```bash
   python ai/training/train_csv_datasets.py
   ```

3. **Models will be saved as:**
   ```
   backend/app/ai/artifacts/pneumonia_model.pkl
   backend/app/ai/artifacts/pneumonia_images_metrics.json
   ```

## Performance Notes

- **Model Training**: ~1-2 minutes for all 5 CSV datasets
- **Docker Build**: ~3-5 minutes (first time, less on rebuilds)
- **Services Startup**: ~10-30 seconds for all 4 services to be healthy
- **API Response**: <500ms for predictions with loaded models

## Environment Variables

Override defaults in `docker-compose.yml` or create `.env` file:

```env
POSTGRES_DB=trustmedai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=2003
MINIO_ACCESS_KEY=trustmedai
MINIO_SECRET_KEY=trustmedai123
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Next Steps

1. Run `docker compose up -d` to start all services
2. Visit http://localhost:3000 to access the web application
3. Check http://localhost:8000/docs for API documentation
4. Create user account and start making predictions
5. Monitor logs with `docker compose logs -f`
