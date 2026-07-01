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
}


def ensure_runtime_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "diagnosis_records" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("diagnosis_records")}
    with engine.begin() as connection:
        for column_name, column_type in DIAGNOSIS_RECORD_COLUMNS.items():
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE diagnosis_records ADD COLUMN {column_name} {column_type}"))
