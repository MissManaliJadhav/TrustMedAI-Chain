from pydantic import BaseModel


class DiseaseSpec(BaseModel):
    key: str
    name: str
    dataset: str
    modality: str
    task_type: str
    labels: list[str]


DISEASE_CATALOG: list[DiseaseSpec] = [
    DiseaseSpec(key="heart", name="Heart Disease", dataset="UCI Heart Disease Dataset", modality="tabular", task_type="binary", labels=["low_risk", "high_risk"]),
    DiseaseSpec(key="diabetes", name="Diabetes", dataset="Pima Indians Diabetes Dataset", modality="tabular", task_type="binary", labels=["negative", "positive"]),
    DiseaseSpec(key="asthma", name="Asthma", dataset="Asthma Prediction Dataset", modality="tabular", task_type="binary", labels=["controlled", "risk"]),
    DiseaseSpec(key="pneumonia", name="Pneumonia", dataset="Chest X-Ray Pneumonia Dataset", modality="image", task_type="binary", labels=["normal", "pneumonia"]),
    DiseaseSpec(key="eye", name="Eye Disease", dataset="Ocular Disease Recognition Dataset", modality="image", task_type="multiclass", labels=["normal", "cataract", "glaucoma", "retina"]),
    DiseaseSpec(key="tuberculosis", name="Tuberculosis", dataset="TB Chest X-Ray Dataset", modality="image", task_type="binary", labels=["normal", "tuberculosis"]),
    DiseaseSpec(key="liver", name="Liver Disease", dataset="Indian Liver Patient Dataset", modality="tabular", task_type="binary", labels=["normal", "disease"]),
    DiseaseSpec(key="parkinson", name="Parkinson Disease", dataset="UCI Parkinson Dataset", modality="voice", task_type="binary", labels=["healthy", "parkinson"]),
    DiseaseSpec(key="brain_tumor", name="Brain Tumor", dataset="Brain MRI Dataset", modality="image", task_type="multiclass", labels=["no_tumor", "glioma", "meningioma", "pituitary"]),
]


def get_disease(key: str) -> DiseaseSpec:
    for disease in DISEASE_CATALOG:
        if disease.key == key:
            return disease
    raise ValueError(f"Unsupported disease: {key}")


def dataset_manifest() -> dict:
    return {
        "splits": ["data/train", "data/validation", "data/test"],
        "diseases": [disease.model_dump() for disease in DISEASE_CATALOG],
        "note": "Dataset scripts preserve real dataset identifiers and create split folders. Licensed archives must be downloaded with the provider's terms.",
    }
