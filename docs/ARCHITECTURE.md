# Architecture

TrustMedAI-Chain is organized as a deployable monorepo:

- `frontend/` - React 18 app for landing, authentication, role dashboards, visualization, reports, blockchain explorer, and federated dashboards
- `backend/` - FastAPI app with RBAC, diagnosis, XAI, trust, ledger, federated, report, and dataset APIs
- `ai/` - dataset preparation, training, XAI, adversarial, trust, and Flower code
- `blockchain/` - Ethereum smart contract and Hyperledger Fabric chaincode
- `k8s/` - Kubernetes-ready manifests

The runtime flow:

1. A doctor submits patient features or scan metadata.
2. The prediction service loads disease configuration and model metrics.
3. XAI services generate SHAP, LIME, Grad-CAM, Captum, integrated-gradient, saliency, and counterfactual structures.
4. Adversarial services evaluate FGSM, PGD, DeepFool, and Carlini-Wagner robustness proxies.
5. AECS is calculated using Dice similarity.
6. DTEI combines predictive fidelity, interpretability, robustness, blockchain integrity, and compliance.
7. The ledger service stores hashes only and records an audit event.
8. The frontend visualizes trust evolution, blockchain reliability, federated trust, and report output.
