# Production Disease Training Pipeline

This project now has a real-data training pipeline at:

```powershell
python ai\training\production_disease_pipeline.py --print-plan
```

It supports the requested modules:

- Machine learning and deep learning model training
- Federated-learning compatible artifact metadata
- Explainable AI reports
- Adversarial robustness evaluation
- Dynamic Trust Evolution Index
- Blockchain-style audit hashes for model and metric integrity
- AECS explanation consistency scoring

## Datasets

Dataset sources are defined in `ai/data/kaggle_datasets.yaml`.

The pipeline uses local data from `data/raw/<disease>` first. If data is missing, configure Kaggle credentials and add `--download-kaggle`:

```powershell
$env:KAGGLE_USERNAME="your_username"
$env:KAGGLE_KEY="your_api_key"
python ai\training\production_disease_pipeline.py --disease diabetes --download-kaggle
```

## Train One Disease

```powershell
python ai\training\production_disease_pipeline.py --disease diabetes
python ai\training\production_disease_pipeline.py --disease heart
python ai\training\production_disease_pipeline.py --disease pneumonia --epochs 12 --batch-size 16
```

For a quick local validation pass:

```powershell
python ai\training\production_disease_pipeline.py --disease diabetes --smoke
python ai\training\production_disease_pipeline.py --disease pneumonia --smoke --epochs 1
```

## Train All

```powershell
python ai\training\production_disease_pipeline.py --all --epochs 12 --batch-size 16
```

Image training should be run on a GPU machine for proper results. The script will still work on CPU, but CNN/ResNet/DenseNet/EfficientNet/ViT training can take a long time.

## Outputs

The trainer writes deployable artifacts to `backend/app/ai/artifacts`:

- `<disease>_model.pkl` for tabular models
- `<disease>_model.keras` for image deep-learning models
- `<disease>_model_metadata.json`
- `<disease>_csv_metrics.json` or `<disease>_images_metrics.json`
- `reports/<disease>/curves.json`
- `reports/<disease>/explanations.json`
- `reports/<disease>/blockchain_audit.json`

The API now loads `.keras` image models when available, and falls back to the existing `.pkl` baseline artifacts when no deep-learning artifact has been trained yet.

## Accuracy Policy

The pipeline does not generate fake accuracy. Metrics are calculated from a held-out 15% test split after a 70% train and 15% validation split. If a dataset is missing, malformed, duplicated, or too weak, the metadata records a failed or blocked status instead of presenting the result as production-ready.
