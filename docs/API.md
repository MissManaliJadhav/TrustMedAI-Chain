# API Overview

Base URL: `/api/v1`

## Authentication

- `POST /auth/signup` - register patient, doctor, hospital admin, or researcher
- `POST /auth/login` - issue JWT access and refresh tokens
- `POST /auth/refresh` - rotate token pair
- `POST /auth/forgot-password` - queue reset workflow
- `POST /auth/verify-email` - verify email token

## Diagnosis

- `GET /datasets/diseases` - list supported disease models and datasets
- `GET /datasets/manifest` - list split folders and source metadata
- `POST /predictions` - run multi-disease diagnosis with XAI, adversarial evaluation, AECS, DTEI, and ledger anchoring

## Trust And Explainability

- `GET /trust/history` - trust evolution graph data
- `GET /trust/weights` - DTEI coefficients

## Blockchain

- `GET /blockchain/explorer` - hash-only audit explorer
- `GET /blockchain/nodes` - configured Fabric and Ethereum nodes

## Federated Learning

- `GET /federated/dashboard` - hospital node, CIFTS, reputation, and consensus status
- `POST /federated/synchronize` - synchronize trust scores and model-weight round metadata

## Reports

- `GET /reports/{diagnosis_id}.pdf` - downloadable diagnosis report with prediction, confidence, trust score, AECS, blockchain hash, and doctor notes
