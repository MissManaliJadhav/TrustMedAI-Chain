# TrustMedAI-Chain

## Blockchain-Enabled Trustworthy Explainable AI Framework for Secure Multi-Disease Diagnosis

TrustMedAI-Chain is a production-grade healthcare AI platform that combines Artificial Intelligence, Explainable AI (XAI), Blockchain, Federated Learning, Adversarial Robustness, and Dynamic Trust Evolution to provide secure, transparent, and trustworthy multi-disease diagnosis.

The framework is inspired by the research concept:

**"Blockchain-Enabled Trustworthy Explainable Deep Learning Framework with Dynamic Trust Evolution for Secure Multi-Disease Diagnosis Under Adversarial Conditions"**

---

## Key Features

### Artificial Intelligence & Deep Learning

* Multi-disease prediction using machine learning and deep learning models
* Support for structured, tabular, and medical imaging datasets
* Real-time disease diagnosis and risk assessment

### Explainable AI (XAI)

* SHAP-based explanations
* LIME explanations
* Captum integration
* Grad-CAM visualization for medical imaging
* Transparent prediction reasoning

### Blockchain Security Layer

* Ethereum smart contract integration
* Hyperledger Fabric support
* Immutable audit trails
* Tamper-resistant medical records
* Trust score verification

### Federated Learning

* Flower-based federated learning framework
* Privacy-preserving collaborative model training
* Distributed healthcare institution support

### Security & Trust

* JWT Authentication
* Role-Based Access Control (RBAC)
* Adversarial attack detection
* Dynamic trust evolution engine
* Secure API communication

### Cloud-Native Deployment

* Docker containerization
* Docker Compose orchestration
* Kubernetes deployment manifests
* CI/CD pipeline using GitHub Actions

---

## Technology Stack

### Frontend

* React 18
* TypeScript
* Vite
* Tailwind CSS
* Material UI
* Redux Toolkit
* React Router
* Recharts
* Axios

### Backend

* FastAPI
* Python 3.11+
* SQLAlchemy
* PostgreSQL
* JWT Authentication
* Pydantic

### AI & Machine Learning

* TensorFlow
* PyTorch
* Scikit-Learn
* SHAP
* LIME
* Captum
* OpenCV

### Blockchain

* Ethereum
* Solidity Smart Contracts
* Hyperledger Fabric

### Federated Learning

* Flower Framework

### Infrastructure

* Docker
* Docker Compose
* Kubernetes
* GitHub Actions
* MinIO Object Storage

---

## Supported Diseases

| Disease           | Dataset Source                     |
| ----------------- | ---------------------------------- |
| Heart Disease     | UCI Heart Disease Dataset          |
| Diabetes          | Pima Indians Diabetes Dataset      |
| Asthma            | Asthma Prediction Dataset          |
| Pneumonia         | Chest X-Ray Pneumonia Dataset      |
| Eye Disease       | Ocular Disease Recognition Dataset |
| Tuberculosis      | TB Chest X-Ray Dataset             |
| Liver Disease     | Indian Liver Patient Dataset       |
| Parkinson Disease | UCI Parkinson Dataset              |
| Brain Tumor       | Brain MRI Dataset                  |

---

## Project Architecture

Frontend (React)
↓
FastAPI Backend
↓
AI Prediction Engine
↓
Explainable AI Module
↓
Trust Evolution Engine
↓
Blockchain Layer (Ethereum / Hyperledger)
↓
PostgreSQL + MinIO Storage

---
## Quick Start

### Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/TrustMedAI-Chain.git
cd TrustMedAI-Chain
```

### Configure Environment

Create a `.env` file from the provided template:

```bash
cp .env.example .env
```

### Start the Platform

```bash
docker compose up --build
```

### Access Services

| Service                  | URL                         |
| ------------------------ | --------------------------- |
| Frontend Dashboard       | http://localhost:3000       |
| Backend API              | http://localhost:8000       |
| Swagger API Docs         | http://localhost:8000/docs  |
| ReDoc API Docs           | http://localhost:8000/redoc |
| MinIO Object Storage API | http://localhost:9000       |
| MinIO Console            | http://localhost:9001       |
| PostgreSQL               | localhost:5432              |

### Default Credentials

#### Platform Administrator

Email:

```text
admin@trustmedai.local
```

Password:

```text
ChangeMe123!
```

#### MinIO Console

Username:

```text
trustmedai
```

Password:

```text
trustmedai123
```

Login at:

```text
http://localhost:9001
```

### Docker Services

The platform automatically starts:

* PostgreSQL Database
* MinIO Object Storage
* FastAPI Backend
* React Frontend

Verify running containers:

```bash
docker ps
```

Stop all services:

```bash
docker compose down
```

Rebuild after code changes:

```bash
docker compose up --build
```

---

## Repository Structure

```text
TrustMedAI-Chain/
│
├── backend/
├── frontend/
├── blockchain/
├── ai/
├── docs/
├── data/
├── k8s/
├── .github/
├── docker-compose.yml
├── README.md
└── .env.example
```

---

## Production Deployment Notes

For production environments:

* Use managed PostgreSQL with encrypted storage.
* Configure MinIO or AWS S3 with encryption.
* Integrate enterprise identity providers.
* Enable TLS certificates.
* Configure secure secret management.
* Deploy blockchain gateways for Ethereum and Hyperledger Fabric.
* Enable audit logging and compliance monitoring.

---

## Documentation

* API Documentation
* System Architecture
* Methodology
* UML Diagrams
* Deployment Guide
* Security Architecture

Refer to the `/docs` directory for detailed documentation.

---

## Research Contribution

TrustMedAI-Chain demonstrates the integration of:

* Explainable Artificial Intelligence
* Blockchain-Based Trust Management
* Federated Learning
* Adversarially Robust Deep Learning
* Secure Healthcare Data Sharing

to create a trustworthy next-generation healthcare diagnosis platform.

---

## License

This project is intended for academic research, educational purposes, and healthcare AI experimentation.
