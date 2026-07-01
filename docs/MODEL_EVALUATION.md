# Model evaluation and data-quality report

## What changed

Tabular models are trained by `ai/training/train_csv_datasets.py`. The trainer now:

- removes exact duplicates before splitting;
- prevents severity-target leakage in the asthma dataset;
- keeps all recordings from one Parkinson patient in one split;
- treats impossible zero-valued diabetes measurements as missing;
- fits imputation, scaling, and categorical encoding on training data only;
- compares logistic regression, random forest, extra trees, and a multilayer neural network;
- chooses the model and decision threshold using validation data only;
- evaluates once on an untouched test split;
- stores the complete preprocessing pipeline, input schema, model card, and limitations with each artifact.

Run all available datasets:

```bash
python ai/training/train_csv_datasets.py
```

Run one dataset:

```bash
python ai/training/train_csv_datasets.py --model diabetes
```

## Leakage-safe held-out results

| Dataset | Selected algorithm | Accuracy | Balanced accuracy | ROC-AUC | Status |
| --- | --- | ---: | ---: | ---: | --- |
| Heart | Extra Trees | 0.819 | 0.822 | 0.921 | Research-ready |
| Diabetes | Random Forest | 0.759 | 0.775 | 0.836 | Research-ready |
| Liver | Extra Trees | 0.674 | 0.735 | 0.725 | Research-ready with caution |
| Parkinson | Logistic Regression | 0.774 | 0.860 | 0.813 | Research-ready with small-sample caution |
| Asthma | Neural network/majority behavior | 0.697 | 0.500 | 0.500 | Blocked |

Accuracy alone is unsafe for imbalanced data. Balanced accuracy, sensitivity,
specificity, F1, and ROC-AUC are stored in each `*_metrics.json` artifact and
shown by the application.

## Why asthma is blocked

The raw asthma file contains 316,800 rows, of which 311,040 are exact
duplicates. More importantly, every symptom profile is paired with severity
labels in a way that provides no generalizable signal once severity-derived
target leakage is removed. Its apparent accuracy is majority-class accuracy;
balanced accuracy and ROC-AUC are both 0.50.

No algorithm or hyperparameter can recover information that is absent from the
dataset. The dashboard therefore disables this model. Replace the source with
a representative, patient-level cohort containing an independently measured
asthma outcome before enabling it.

## Image-model limitation

The current image artifacts are compatibility baselines trained from flattened
64×64 grayscale pixels using at most 100 images per class. They are not deep
learning models and are not clinically validated. A defensible next phase
requires duplicate detection, patient-level splits, image-quality controls,
transfer learning with a CNN, calibration, and external-site validation.

## Intended use

All models in this repository are for research and educational decision support
only. They are not medical devices and must not be used as autonomous diagnoses.

The API now reports SHAP, LIME, Grad-CAM, Captum, integrated gradients,
adversarial robustness, and AECS as unavailable/unevaluated. The earlier
implementation generated these values from prediction confidence and therefore
did not execute the named methods. The federated panel is explicitly labelled
as a simulation until real Flower clients and training rounds are connected.
