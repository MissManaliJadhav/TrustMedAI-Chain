from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    key: str
    name: str
    framework: str
    modality: str
    epochs: int = 10
    batch_size: int = 32


MODEL_REGISTRY = {
    "heart": ModelConfig("heart", "Heart Model", "tensorflow", "tabular"),
    "diabetes": ModelConfig("diabetes", "Diabetes Model", "tensorflow", "tabular"),
    "asthma": ModelConfig("asthma", "Asthma Model", "tensorflow", "tabular"),
    "pneumonia": ModelConfig("pneumonia", "Pneumonia Model", "pytorch", "image"),
    "eye": ModelConfig("eye", "Eye Disease Model", "pytorch", "image"),
    "tuberculosis": ModelConfig("tuberculosis", "TB Model", "pytorch", "image"),
    "liver": ModelConfig("liver", "Liver Model", "tensorflow", "tabular"),
    "parkinson": ModelConfig("parkinson", "Parkinson Model", "tensorflow", "voice"),
    "brain_tumor": ModelConfig("brain_tumor", "Brain Tumor Model", "pytorch", "image"),
}
