"""Keep tests isolated from Docker/PostgreSQL settings in the developer .env file."""

import os


os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ARTIFACT_STORAGE_BACKEND"] = "local"
os.environ["ENVIRONMENT"] = "test"
