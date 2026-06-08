#!/usr/bin/env python3
"""
Test script to validate TrustMedAI setup and Docker services.
Run after: docker compose up -d
"""

import json
import time
import sys
from pathlib import Path

import requests

# Configuration
PROJECT_ROOT = Path(__file__).parent
BACKEND_URL = "http://localhost:8000"
POSTGRES_HOST = "localhost"
MINIO_HOST = "localhost"
HEALTH_CHECK_RETRIES = 5
HEALTH_CHECK_DELAY = 3

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BLUE = "\033[94m"


def print_header(title: str) -> None:
    """Print section header."""
    print(f"\n{BLUE}{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}{RESET}\n")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{RED}✗ {message}{RESET}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}⚠ {message}{RESET}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"  {BLUE}ℹ {message}{RESET}")


def check_local_files() -> bool:
    """Check if required files exist locally."""
    print_header("1. Checking Local Files")
    
    required_files = {
        "CSV Data": [
            "data/raw/heart/heart_disease_uci.csv",
            "data/raw/diabetes/diabetes.csv",
            "data/raw/asthma/asthma.csv",
            "data/raw/liver/indian_liver_patient.csv",
            "data/raw/parkinson/parkinsons.csv",
        ],
        "Trained Models": [
            "backend/app/ai/artifacts/heart_model.pkl",
            "backend/app/ai/artifacts/diabetes_model.pkl",
            "backend/app/ai/artifacts/asthma_model.pkl",
            "backend/app/ai/artifacts/liver_model.pkl",
            "backend/app/ai/artifacts/parkinson_model.pkl",
        ],
        "Model Metrics": [
            "backend/app/ai/artifacts/heart_csv_metrics.json",
            "backend/app/ai/artifacts/diabetes_csv_metrics.json",
        ],
        "Docker": [
            "docker-compose.yml",
            "backend/Dockerfile",
            "frontend/Dockerfile",
        ],
    }
    
    all_exist = True
    for category, files in required_files.items():
        print(f"{category}:")
        for file_path in files:
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                print_success(f"{file_path}")
            else:
                print_error(f"{file_path} - NOT FOUND")
                all_exist = False
    
    return all_exist


def check_backend_api() -> bool:
    """Check if backend API is responding."""
    print_header("2. Checking Backend API")
    
    for attempt in range(HEALTH_CHECK_RETRIES):
        try:
            print_info(f"Attempt {attempt + 1}/{HEALTH_CHECK_RETRIES}")
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            
            if response.status_code == 200:
                print_success(f"Backend API is responding")
                print_info(f"URL: {BACKEND_URL}")
                print_info(f"Status Code: {response.status_code}")
                
                try:
                    data = response.json()
                    print_info(f"Response: {json.dumps(data, indent=2)}")
                except:
                    print_info(f"Response: {response.text}")
                
                return True
            else:
                print_warning(f"Unexpected status code: {response.status_code}")
        
        except requests.exceptions.ConnectionError as e:
            print_warning(f"Connection failed: {str(e)[:60]}")
        except requests.exceptions.Timeout:
            print_warning("Request timed out")
        except Exception as e:
            print_warning(f"Error: {str(e)[:60]}")
        
        if attempt < HEALTH_CHECK_RETRIES - 1:
            print_info(f"Waiting {HEALTH_CHECK_DELAY}s before retry...")
            time.sleep(HEALTH_CHECK_DELAY)
    
    print_error("Backend API not responding after retries")
    print_info("Make sure to run: docker compose up -d")
    return False


def check_api_endpoints() -> bool:
    """Check critical API endpoints."""
    print_header("3. Checking API Endpoints")
    
    endpoints = {
        "Health": "/health",
        "API Docs": "/docs",
        "Prediction Schema": "/api/v1/predictions",
    }
    
    all_ok = True
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            if response.status_code in [200, 422]:  # 422 for missing auth on POST
                print_success(f"{name} endpoint available: {endpoint}")
            else:
                print_warning(f"{name} returned status {response.status_code}")
                all_ok = False
        except Exception as e:
            print_error(f"{name} error: {str(e)[:50]}")
            all_ok = False
    
    return all_ok


def check_models_loaded() -> bool:
    """Check if trained models can be loaded."""
    print_header("4. Checking Model Files")
    
    import pickle
    
    models_dir = PROJECT_ROOT / "backend/app/ai/artifacts"
    all_loaded = True
    
    for model_file in sorted(models_dir.glob("*_model.pkl")):
        try:
            with open(model_file, "rb") as f:
                model = pickle.load(f)
            disease_key = model_file.stem.replace("_model", "")
            print_success(f"Loaded {disease_key} model - {model.__class__.__name__}")
        except Exception as e:
            print_error(f"Failed to load {model_file.name}: {str(e)[:50]}")
            all_loaded = False
    
    return all_loaded


def check_metrics() -> bool:
    """Check if metrics files are valid."""
    print_header("5. Checking Model Metrics")
    
    metrics_dir = PROJECT_ROOT / "backend/app/ai/artifacts"
    all_valid = True
    
    for metrics_file in sorted(metrics_dir.glob("*_metrics.json")):
        try:
            with open(metrics_file) as f:
                metrics = json.load(f)
            disease_key = metrics_file.stem.replace("_csv_metrics", "").replace("_images_metrics", "")
            
            if isinstance(metrics, dict):
                keys = ", ".join(metrics.keys())
                print_success(f"{disease_key} metrics: {keys}")
                
                # Show key metrics if available
                if "accuracy" in metrics and "auc" in metrics:
                    accuracy = metrics["accuracy"]
                    auc = metrics.get("auc", "N/A")
                    print_info(f"  Accuracy: {accuracy:.4f}, AUC: {auc}")
            else:
                print_warning(f"{disease_key} metrics format unexpected")
                all_valid = False
        
        except Exception as e:
            print_error(f"Failed to read {metrics_file.name}: {str(e)[:50]}")
            all_valid = False
    
    return all_valid


def check_database_connection() -> bool:
    """Check if PostgreSQL is accessible."""
    print_header("6. Checking Database Connection")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=5432,
            user="postgres",
            password="2003",
            database="trustmedai"
        )
        print_success("PostgreSQL connection successful")
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print_success("Database query successful")
        
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        print_warning(f"PostgreSQL check skipped: {str(e)[:60]}")
        print_info("(psycopg2 not installed or database not running)")
        return False


def check_minio_connection() -> bool:
    """Check if MinIO is accessible."""
    print_header("7. Checking MinIO Connection")
    
    try:
        response = requests.get(f"http://{MINIO_HOST}:9000", timeout=5)
        # MinIO may return 403 or other status, just checking connectivity
        print_success("MinIO is accessible")
        return True
    
    except Exception as e:
        print_warning(f"MinIO not accessible: {str(e)[:60]}")
        return False


def print_summary(results: dict[str, bool]) -> None:
    """Print test summary."""
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check_name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {check_name}: {status}")
    
    print(f"\n{BLUE}Result: {passed}/{total} checks passed{RESET}")
    
    if passed == total:
        print_success("All checks passed! System is ready.")
    elif passed >= total * 0.8:
        print_warning("Most checks passed. Some optional services may not be running.")
    else:
        print_error("Multiple checks failed. See errors above.")
    
    return passed == total


def main() -> int:
    """Run all checks."""
    print(f"\n{BLUE}TrustMedAI System Validation{RESET}")
    print(f"Project Root: {PROJECT_ROOT}\n")
    
    results = {}
    
    # Run checks
    results["Local Files"] = check_local_files()
    results["Backend API"] = check_backend_api()
    
    if results["Backend API"]:
        results["API Endpoints"] = check_api_endpoints()
    else:
        print_info("Skipping endpoint checks (API not responding)")
    
    results["Model Files"] = check_models_loaded()
    results["Model Metrics"] = check_metrics()
    results["Database"] = check_database_connection()
    results["MinIO"] = check_minio_connection()
    
    # Summary
    all_passed = print_summary(results)
    
    # Next steps
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    if not results["Backend API"]:
        print("1. Start Docker services:")
        print("   docker compose up -d")
        print("2. Wait 10-30 seconds for services to initialize")
        print("3. Run this script again to verify")
    else:
        print("✓ Access the application:")
        print("  - Frontend: http://localhost:3000")
        print("  - API Docs: http://localhost:8000/docs")
        print("  - MinIO: http://localhost:9001")
    
    print("\nFor issues, check logs with:")
    print("  docker compose logs -f [service_name]")
    print("  Available services: backend, frontend, postgres, minio\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
