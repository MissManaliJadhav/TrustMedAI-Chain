# Dataset Splits

The training pipeline expects this structure:

```text
data/
  train/<disease_key>/
  validation/<disease_key>/
  test/<disease_key>/
```

Run:

```bash
python ai/data/prepare_datasets.py --create-folders
```

Several medical datasets require Kaggle, UCI, or institutional license acceptance. The preparation script records canonical dataset names and creates deterministic split folders; put downloaded archives into `data/raw/<disease_key>/` before extraction.
