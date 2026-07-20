# TrustMedAI-Chain Complete Runbook

This is the authoritative setup, operation, testing, and troubleshooting guide
for the current repository.

> Medical safety: TrustMedAI-Chain is a research and decision-support project.
> Its output is not a medical diagnosis and does not replace a licensed
> healthcare professional.

## 1. System Overview

```text
React frontend
  -> FastAPI backend
    -> trained disease model
    -> explainability, adversarial checks, and trust calculation
    -> PostgreSQL diagnosis record
    -> Ethereum audit anchor
    -> PDF report and uploaded artifacts in MinIO
```

The standard Docker stack contains:

| Service | Address | Purpose |
| --- | --- | --- |
| Frontend | http://localhost:3000 | React application |
| Backend | http://localhost:8000 | FastAPI |
| Swagger | http://localhost:8000/docs | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | Alternative API documentation |
| PostgreSQL | localhost:5432 | Persistent database |
| MinIO API | http://localhost:9000 | Object storage |
| MinIO console | http://localhost:9001 | Storage administration |
| Ganache | http://localhost:8545 | Local Ethereum network |

Hyperledger Fabric support exists in the code, but Fabric is optional and is
not started by `docker-compose.yml`. Ganache/Ethereum is the blockchain path
included in the normal local stack.

## 2. Recommended Run Method: Docker Desktop

### Prerequisites

- Docker Desktop with Docker Compose v2
- Git
- At least 8 GB free RAM and enough disk space for the Python ML image

The backend includes TensorFlow, PyTorch, SHAP, OpenCV, and other large
dependencies. The first build can take several minutes.

### Step 1: Open PowerShell in the project

```powershell
cd C:\Users\dbatu\OneDrive\Desktop\Trust_ai_chain
```

### Step 2: Create `.env`

```powershell
Copy-Item .env.example .env
```

The example contains development-only defaults. Before shared or production
use, change:

- `JWT_SECRET_KEY`
- `SUPER_ADMIN_PASSWORD`
- `POSTGRES_PASSWORD` and the matching password in `DATABASE_URL`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`

Never commit `.env`.

### Step 3: Validate and start

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

No output from `docker compose config --quiet` means the Compose configuration
is valid. In `docker compose ps`, PostgreSQL should be healthy and the other
services should be running.

### Step 4: Verify health

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```text
status service
------ -------
ok     TrustMedAI-Chain
```

### Step 5: Login

Open http://localhost:3000.

Development administrator:

```text
Email:    admin@trustmedai.local
Password: ChangeMe123!
```

The administrator is created only when the database does not already contain
that email. Changing `SUPER_ADMIN_PASSWORD` later does not overwrite an
existing user's password.

MinIO development login:

```text
URL:      http://localhost:9001
Username: trustmedai
Password: trustmedai123
```

## 3. Pages and Roles

| Page | Route | Access |
| --- | --- | --- |
| Landing | `/` | Public |
| Login | `/login` | Public |
| Patient signup | `/signup` | Public |
| Password recovery | `/forgot-password` | Public |
| Email verification | `/verify-email` | Public |
| Dashboard | `/dashboard` | Authenticated |
| Disease catalog | `/diagnosis` | Authenticated |
| Disease workflow | `/diagnosis/:diseaseKey` | Authenticated |
| Role dashboard | `/role-dashboard` | Admin, hospital admin, doctor, patient |
| MedAI chatbot | `/chat` | Authenticated |

Only patients can self-register. Staff accounts are provisioned by an
administrator. Only `DOCTOR` and `SUPER_ADMIN` have `diagnosis:create`
permission. Disease forms are read-only for patient accounts.

## 4. Disease Pages

Open **Disease Diagnosis** in the header or visit:

```text
http://localhost:3000/diagnosis
```

### Clinical and tabular pages

| Disease | Route | Input |
| --- | --- | --- |
| Heart Disease | `/diagnosis/heart` | Disease-specific clinical fields |
| Diabetes | `/diagnosis/diabetes` | Disease-specific clinical fields |
| Asthma | `/diagnosis/asthma` | Disease-specific clinical fields |
| Liver Disease | `/diagnosis/liver` | Disease-specific clinical fields |
| Parkinson Disease | `/diagnosis/parkinson` | Voice-derived numeric measurements |

Parkinson currently accepts the trained model's numeric voice measurements. It
does not upload an audio file.

### Image pages

| Disease | Route | Input |
| --- | --- | --- |
| Pneumonia | `/diagnosis/pneumonia` | Chest image |
| Eye Disease | `/diagnosis/eye` | Ocular/retinal image |
| Tuberculosis | `/diagnosis/tuberculosis` | Chest image |
| Brain Tumor | `/diagnosis/brain_tumor` | Brain MRI image |

Image rules:

- JPEG, PNG, or WebP
- Maximum 10 MB
- Optional supporting PDF: maximum 15 MB

### Run a diagnosis

1. Login as a doctor or super administrator.
2. Open `/diagnosis` and select a disease.
3. Enter patient name and email.
4. Optionally enter the patient's existing platform user ID.
5. Fill every model field, or select the required medical image.
6. Optionally attach a supporting PDF.
7. Add clinical notes.
8. Select **Run Diagnosis**.

Successful output includes:

- prediction and confidence
- trust score
- blockchain record hash
- Ethereum transaction status when Ganache is available
- PDF report download
- blockchain verification for authorized roles

A model may show `blocked_low_quality` and disable submission. That is an
intentional model-governance result, not a frontend failure.

The first image-model request may take longer while the model is loaded. The
dedicated page allows up to 60 seconds for this cold load.

## 5. Chatbot

1. Open `/chat`.
2. Create a session.
3. Provide patient profile details.
4. Describe symptoms and duration.
5. Answer symptom and medical-history questions.
6. Complete the risk assessment.
7. Review the summary and disclaimer.
8. Export the completed assessment if a diagnosis record is needed.

An exported assessment creates a diagnosis record, hash, Ethereum anchor
attempt, and PDF report. Emergency phrases trigger escalation guidance. The
chatbot is not an emergency service.

## 6. Reports and Storage

Docker uses MinIO for generated PDFs and uploaded files. Inspect the bucket at
http://localhost:9001.

Native development can use:

```text
ARTIFACT_STORAGE_BACKEND=local
LOCAL_ARTIFACT_DIR=./.artifacts
```

Reports contain supplied patient identity, model inputs, prediction,
confidence, trust information, notes, blockchain status, and artifact hashes.

## 7. Ethereum and Blockchain Verification

Docker containers use:

```text
ETHEREUM_RPC_URL=http://ethereum:8545
```

In local/development mode, the backend automatically deploys the compiled
`TrustLedger` contract when no contract address is configured. It then submits
and verifies diagnosis hashes.

```powershell
docker compose logs -f ethereum
docker compose logs -f backend
```

Status meanings:

- `anchored`, `verified: true`: on-chain verification succeeded.
- `unavailable`: the clinical record exists, but the chain was unavailable.
- local hash match only: local integrity succeeded without a verified anchor.

Fabric requires a Fabric SDK, connection profile, peers, channel, and deployed
chaincode. It is not required for this Docker run.

## 8. Native Local Development

### Requirements

- Python 3.11
- Node.js 20
- npm
- Optional Ganache through `npx`

### Install backend

```powershell
cd C:\Users\dbatu\OneDrive\Desktop\Trust_ai_chain
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

### Run backend with SQLite and local files

```powershell
$env:DATABASE_URL = "sqlite:///./trustmedai.local.db"
$env:ARTIFACT_STORAGE_BACKEND = "local"
$env:LOCAL_ARTIFACT_DIR = "./.artifacts"
$env:ETHEREUM_RPC_URL = "http://127.0.0.1:8545"
$env:FRONTEND_ORIGIN = "http://localhost:3000"
$env:JWT_SECRET_KEY = "local-development-secret-change-me"

cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The SQLite path is relative to the `backend` directory.

### Optional local Ganache

In a separate PowerShell window from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-ganache.ps1
```

Without Ganache, diagnosis records can still be saved, but Ethereum status is
unavailable.

### Run frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

`frontend/.env` must contain:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Vite variables are embedded during build. Rebuild after changing them.

## 9. Tests and Build Verification

Backend:

```powershell
cd backend
python -m pytest -q
```

Current expected result:

```text
14 passed
```

Frontend:

```powershell
cd frontend
npm install
npm run build
```

Expected final line:

```text
✓ built
```

Compile the Solidity contract from the repository root:

```powershell
python scripts\compile-contract.py
```

Expected artifacts:

```text
blockchain/ethereum/TrustLedger.compiled.json
backend/app/blockchain/TrustLedger.compiled.json
```

Smoke checks:

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-WebRequest http://localhost:3000 -UseBasicParsing
```

## 10. Logs and Shutdown

```powershell
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f ethereum
docker compose restart backend
docker compose down
```

Full reset:

```powershell
docker compose down -v
```

> Warning: `docker compose down -v` permanently deletes Compose PostgreSQL and
> MinIO volumes, including users, records, and stored artifacts.

## 11. Troubleshooting

### Docker is unavailable

Start Docker Desktop, then run:

```powershell
docker info
```

### Port conflict

```powershell
Get-NetTCPConnection -LocalPort 3000,8000,8545,9000,9001,5432
```

Stop the conflicting program or change the host port in `docker-compose.yml`.

### Backend does not start

```powershell
docker compose ps
docker compose logs backend
docker compose logs postgres
```

Allow time for ML imports and runtime schema initialization.

### Container hostname cannot resolve

`postgres`, `minio`, and `ethereum` work only between containers. Native
development must use `127.0.0.1` and the exposed port.

### Invalid administrator password

- Confirm `.env`.
- Bootstrap does not overwrite an existing administrator.
- Reset only disposable data with `docker compose down -v`.
- For disposable local SQLite, stop the backend and remove only
  `backend/trustmedai.local.db`.

Never delete a database containing needed data.

### Frontend cannot call API

- Check http://localhost:8000/health.
- Ensure `VITE_API_BASE_URL` ends with `/api/v1`.
- Ensure backend CORS allows the frontend origin.
- Rebuild after changing Vite configuration.

### Image page fails on first load

- Wait for model loading.
- Check backend logs.
- Confirm the relevant `*_model.pkl` exists.
- The page uses a 60-second cold-load timeout.

### Diagnosis button is disabled

Valid causes include:

- role is not doctor or super administrator
- required fields are missing
- no image is selected
- model artifact is missing
- model is marked `blocked_low_quality`

### PDF fails

```powershell
docker compose logs backend
docker compose logs minio
```

Verify storage credentials and bucket configuration.

### Ethereum is unavailable

```powershell
docker compose ps ethereum
docker compose logs ethereum
docker compose logs backend
```

Docker must use `http://ethereum:8545`; native development must use
`http://127.0.0.1:8545`.

### Deep route gives Nginx 404

The supplied Nginx config includes SPA fallback. Rebuild the frontend:

```powershell
docker compose build frontend
docker compose up -d frontend
```

## 12. Production Checklist

Before production:

- set `ENVIRONMENT=production`
- replace every development password and secret
- enable TLS everywhere
- use managed or backed-up database and object storage
- configure a reviewed contract address instead of automatic deployment
- implement real staff identity provisioning and email delivery
- add monitoring, backups, audit retention, and incident response
- complete security, privacy, clinical, and regulatory review

## 13. Quick Commands

```powershell
cd C:\Users\dbatu\OneDrive\Desktop\Trust_ai_chain
Copy-Item .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Start-Process http://localhost:3000
```

Stop:

```powershell
docker compose down
```
