from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("datasets.yaml")


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def create_split_folders() -> None:
    manifest = load_manifest()
    for split in ("train", "validation", "test"):
        for disease_key in manifest["diseases"]:
            path = ROOT / "data" / split / disease_key
            path.mkdir(parents=True, exist_ok=True)
            (path / ".gitkeep").touch()


def print_sources() -> None:
    manifest = load_manifest()
    for key, item in manifest["diseases"].items():
        print(f"{key}: {item['dataset']} -> {item['source']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-folders", action="store_true")
    parser.add_argument("--sources", action="store_true")
    args = parser.parse_args()
    if args.create_folders:
        create_split_folders()
    if args.sources:
        print_sources()
    if not args.create_folders and not args.sources:
        parser.print_help()


if __name__ == "__main__":
    main()
