from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "TrustMedAI-Chain"
    environment: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    database_url: str = "sqlite:///./trustmedai.local.db"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "trustmedai"
    minio_secret_key: str = "trustmedai123"
    minio_secure: bool = False
    minio_bucket: str = "trustmedai-artifacts"
    artifact_storage_backend: str = "auto"
    local_artifact_dir: str = "./.artifacts"

    jwt_secret_key: str = "replace-with-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    super_admin_email: str = "admin@trustmedai.local"
    super_admin_password: str = "ChangeMe123!"

    ethereum_rpc_url: str = "http://ethereum:8545"
    ethereum_contract_address: str | None = None
    ethereum_contract_bytecode: str | None = None
    ethereum_contract_artifact: str = "app/blockchain/TrustLedger.compiled.json"
    ethereum_private_key: str | None = None
    ethereum_sender_address: str | None = None
    ethereum_receipt_timeout_seconds: int = 120

    fabric_gateway_endpoint: str = "fabric-peer:7051"
    fabric_connection_profile: str | None = None
    fabric_org_name: str = "Org1"
    fabric_user_name: str = "Admin"
    fabric_channel_name: str = "trustmedai-diagnosis"
    fabric_chaincode_name: str = "trustledger"
    fabric_peer_names: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
