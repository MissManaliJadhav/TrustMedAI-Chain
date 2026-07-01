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
        "diagnosis:create",
        "datasets:upload",
        "research:view",
        "reports:download",
    },
    Role.HOSPITAL_ADMIN: {"doctors:manage", "patients:manage", "reports:view", "reports:download", "datasets:upload", "audit:view"},
    Role.DOCTOR: {"diagnosis:create", "scans:upload", "xai:view", "trust:view", "reports:view", "reports:download", "audit:view"},
    Role.PATIENT: {"reports:upload", "results:view", "reports:download"},
    Role.RESEARCHER: {"datasets:anonymized:view", "metrics:view", "experiments:run", "trust:view"},
}


def role_has_permission(role: Role, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
