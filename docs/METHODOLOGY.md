# Methodology

## Multi-Disease AI

Each disease has an independent pipeline with train, validation, and test phases. Tabular and voice datasets use classical baselines as runnable defaults and can be replaced with TensorFlow models. Image datasets target PyTorch CNNs and Grad-CAM.

Metrics saved per model:

- accuracy
- precision
- recall
- f1-score
- auc

## XAI

The platform exposes a unified explanation bundle:

- SHAP feature importance
- LIME local rules
- Grad-CAM heatmaps
- Captum saliency and occlusion sensitivity
- Integrated gradients
- Counterfactual explanations

## Adversarial Robustness

The adversarial module includes FGSM, PGD, DeepFool, and Carlini-Wagner proxy implementations. Production deployments can replace proxy functions with framework-specific attack libraries while preserving API response contracts.

## AECS

Adversarial Explanation Consistency Score:

```text
AECS = Dice(original explanation, adversarial explanation)
```

## DTEI

Dynamic Trust Evolution Index:

```text
DTEI = alpha F + beta I + gamma R + delta B + lambda C
```

Where:

- `F` = Predictive Fidelity
- `I` = Interpretability
- `R` = Robustness
- `B` = Blockchain Integrity
- `C` = Compliance

Default coefficients:

- alpha = 0.30
- beta = 0.20
- gamma = 0.20
- delta = 0.15
- lambda = 0.15

## CIFTS

Cross Institutional Federated Trust Synchronization shares:

- trust scores
- trust evolution
- hospital reputation
- consensus reliability
