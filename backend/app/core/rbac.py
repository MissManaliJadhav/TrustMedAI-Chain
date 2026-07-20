from enum import Enum


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    HOSPITAL_ADMIN = "HOSPITAL_ADMIN"
    DOCTOR = "DOCTOR"
    PATIENT = "PATIENT"
    RESEARCHER = "RESEARCHER"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.SUPER_ADMIN: {
        "platform:manage",
        "blockchain:manage",
        "hospitals:manage",
        "users:manage",
        "audit:view",
        "trust:view",
        "federated:manage",
        "datasets:upload",
        "research:view",
    },
    Role.HOSPITAL_ADMIN: {
        "doctors:manage",
        "patients:manage",
        "datasets:upload",
        "audit:view",
        "trust:view",
        "federated:manage",
    },
    Role.DOCTOR: {"diagnosis:create", "scans:upload", "xai:view", "trust:view", "reports:view", "reports:download", "audit:view"},
    Role.PATIENT: {"diagnosis:create", "reports:upload", "results:view", "reports:download", "trust:view"},
    Role.RESEARCHER: {"datasets:anonymized:view", "metrics:view", "experiments:run", "trust:view"},
}


def role_has_permission(role: Role, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
