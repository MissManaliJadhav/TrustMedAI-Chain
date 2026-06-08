from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
OUTPUT_JSON = PROJECT_ROOT / "data" / "raw_dataset_summary.json"
OUTPUT_TXT = PROJECT_ROOT / "data" / "raw_dataset_summary.txt"

DISEASE_KEYS = [
    "heart",
    "diabetes",
    "asthma",
    "pneumonia",
    "eye",
    "tuberculosis",
    "liver",
    "parkinson",
    "brain_tumor",
]
TARGET_CANDIDATES = [
    "target",
    "label",
    "Outcome",
    "outcome",
    "diagnosis",
    "Diagnosis",
    "result",
    "Result",
    "class",
    "Class",
    "y",
    "Y",
    "heart_disease",
    "HeartDisease",
    "disease_present",
    "num",
    "Dataset",
    "dataset",
    "status",
]
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tif", "tiff", "jfif"}


def find_csv_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("**/*.csv") if p.is_file())


def detect_target_column(header: list[str], rows: list[list[str]]) -> str | None:
    for candidate in TARGET_CANDIDATES:
        for name in header:
            if name.strip().lower() == candidate.strip().lower():
                return name
    # fallback: if last column looks like a binary or small categorical target
    if rows:
        last_col = header[-1]
        values = [row[-1].strip() for row in rows if row]
        if values:
            unique = set(values)
            if unique <= {"0", "1", "2"} or len(unique) <= 4:
                return last_col
    return None


def inspect_csv(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "exists": path.exists(),
        "columns": [],
        "row_count": 0,
        "sample_rows": [],
        "missing_per_column": {},
        "target_column": None,
        "target_distribution": {},
    }
    if not path.exists():
        return summary

    with path.open("r", encoding="utf-8", errors="replace") as csvfile:
        reader = csv.reader(csvfile)
        try:
            header = next(reader)
        except StopIteration:
            return summary
        summary["columns"] = header
        rows = []
        missing_counter = Counter()
        distribution: Counter[str] = Counter()
        samples = []
        for i, row in enumerate(reader, start=1):
            if len(row) != len(header):
                row = row + [""] * (len(header) - len(row))
            if i <= 10:
                rows.append(row)
            if i <= 5:
                samples.append(row)
        target_col = detect_target_column(header, rows)
        summary["target_column"] = target_col
        csvfile.seek(0)
        reader = csv.reader(csvfile)
        next(reader, None)
        for i, row in enumerate(reader, start=1):
            if len(row) != len(header):
                row = row + [""] * (len(header) - len(row))
            for name, value in zip(header, row):
                if value is None or value.strip() == "":
                    missing_counter[name] += 1
            if target_col is not None:
                idx = header.index(target_col)
                value = row[idx].strip() if idx < len(row) else ""
                if value == "":
                    distribution["(missing)"] += 1
                else:
                    distribution[value] += 1
            summary["row_count"] = i
        summary["sample_rows"] = samples
        summary["missing_per_column"] = dict(missing_counter)
        if target_col is not None:
            summary["target_distribution"] = dict(distribution)
        for i, row in enumerate(reader, start=1):
            if len(row) != len(header):
                row = row + [""] * (len(header) - len(row))
            if i <= 5:
                samples.append(row)
            for name, value in zip(header, row):
                if value is None or value.strip() == "":
                    missing_counter[name] += 1
            if target_col is not None:
                idx = header.index(target_col)
                value = row[idx].strip() if idx < len(row) else ""
                if value == "":
                    distribution["(missing)"] += 1
                else:
                    distribution[value] += 1
            summary["row_count"] = i
        summary["sample_rows"] = samples
        summary["missing_per_column"] = dict(missing_counter)
        if target_col is not None:
            summary["target_distribution"] = dict(distribution)
    return summary


def inspect_image_folder(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "folder": str(path.relative_to(PROJECT_ROOT)),
        "exists": path.exists(),
        "image_files": 0,
        "subfolder_counts": {},
        "examples": [],
    }
    if not path.exists():
        return summary
    file_count = 0
    subfolder_counts: Counter[str] = Counter()
    examples = []
    for item in sorted(path.rglob("*")):
        if item.is_file() and item.suffix.lower().lstrip(".") in IMAGE_EXTENSIONS:
            file_count += 1
            rel = item.relative_to(path)
            if rel.parent == Path(""):
                subfolder_counts["."] += 1
            else:
                subfolder_counts[str(rel.parent)] += 1
            if len(examples) < 10:
                examples.append(str(rel))
    summary["image_files"] = file_count
    summary["subfolder_counts"] = dict(subfolder_counts)
    summary["examples"] = examples
    return summary


def inspect_datasets() -> dict[str, Any]:
    result: dict[str, Any] = {"datasets": {}, "raw_root": str(RAW_ROOT.relative_to(PROJECT_ROOT))}
    for key in DISEASE_KEYS:
        dataset_summary: dict[str, Any] = {"csv_files": [], "image_folder": None}
        raw_dir = RAW_ROOT / key
        if raw_dir.exists():
            csv_files = find_csv_files(raw_dir)
            for csv_path in csv_files:
                dataset_summary["csv_files"].append(inspect_csv(csv_path))
            if key in {"pneumonia", "eye", "tuberculosis", "brain_tumor"}:
                dataset_summary["image_folder"] = inspect_image_folder(raw_dir)
        else:
            dataset_summary["error"] = "missing raw folder"
        result["datasets"][key] = dataset_summary
    return result


def write_output(summary: dict[str, Any]) -> None:
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = []
    lines.append("Raw dataset summary")
    lines.append("===================\n")
    for key, data in summary["datasets"].items():
        lines.append(f"Dataset: {key}")
        if "error" in data:
            lines.append(f"  {data['error']}")
            lines.append("")
            continue
        for csv_info in data["csv_files"]:
            lines.append(f"  CSV file: {csv_info['file']}")
            lines.append(f"    exists: {csv_info['exists']}")
            lines.append(f"    row_count: {csv_info['row_count']}")
            lines.append(f"    columns: {len(csv_info['columns'])}")
            lines.append(f"    column_names: {csv_info['columns']}")
            lines.append(f"    target_column: {csv_info['target_column']}")
            if csv_info["target_distribution"]:
                lines.append(f"    target_distribution: {csv_info['target_distribution']}")
            if csv_info["missing_per_column"]:
                lines.append(f"    missing_per_column: {csv_info['missing_per_column']}")
            lines.append("    sample_rows:")
            for row in csv_info["sample_rows"]:
                lines.append(f"      {row}")
            lines.append("")
        if data["image_folder"] is not None:
            img = data["image_folder"]
            lines.append(f"  image_folder: {img['folder']}")
            lines.append(f"    exists: {img['exists']}")
            lines.append(f"    image_files: {img['image_files']}")
            lines.append(f"    subfolder_counts: {img['subfolder_counts']}")
            lines.append(f"    examples: {img['examples']}")
            lines.append("")
    OUTPUT_TXT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    summary = inspect_datasets()
    write_output(summary)
    print(f"Wrote summary to {OUTPUT_JSON} and {OUTPUT_TXT}")
