from sqlalchemy import Engine, inspect, text


DIAGNOSIS_RECORD_COLUMNS: dict[str, str] = {
    "patient_name": "VARCHAR(255)",
    "patient_email": "VARCHAR(255)",
    "input_modality": "VARCHAR(40) DEFAULT 'tabular'",
    "input_features": "JSON",
    "ethereum_tx_hash": "VARCHAR(128)",
    "ethereum_block_number": "INTEGER",
    "ethereum_receipt_status": "VARCHAR(40)",
    "ethereum_anchor_verified": "BOOLEAN DEFAULT FALSE",
    "fabric_tx_id": "VARCHAR(128)",
    "fabric_anchor_verified": "BOOLEAN DEFAULT FALSE",
    "blockchain_status": "JSON",
    "report_object_path": "VARCHAR(512)",
    "review_status": "VARCHAR(40) DEFAULT 'pending'",
    "doctor_decision": "VARCHAR(80)",
    "final_clinical_decision": "VARCHAR(120)",
    "review_notes": "TEXT",
    "reviewed_by_id": "VARCHAR(36)",
    "reviewed_at": "TIMESTAMP",
    "priority": "VARCHAR(40) DEFAULT 'routine'",
}


USER_COLUMNS: dict[str, str] = {
    "public_patient_id": "VARCHAR(16)",
    "profile": "JSON",
    "profile_photo_object_path": "VARCHAR(512)",
    "profile_photo_content_type": "VARCHAR(120)",
    "profile_updated_at": "TIMESTAMP",
    "last_login_at": "TIMESTAMP",
}


def ensure_runtime_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "diagnosis_records" in table_names:
            existing = {column["name"] for column in inspector.get_columns("diagnosis_records")}
            for column_name, column_type in DIAGNOSIS_RECORD_COLUMNS.items():
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE diagnosis_records ADD COLUMN {column_name} {column_type}"))
        if "users" in table_names:
            existing = {column["name"] for column in inspector.get_columns("users")}
            for column_name, column_type in USER_COLUMNS.items():
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
