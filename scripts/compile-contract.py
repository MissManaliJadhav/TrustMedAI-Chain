import json
from pathlib import Path

from solcx import compile_standard, install_solc
import solcx.install

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_FILE = ROOT / "blockchain" / "ethereum" / "contracts" / "TrustLedger.sol"
OUTPUT_FILE = ROOT / "blockchain" / "ethereum" / "TrustLedger.compiled.json"
BACKEND_OUTPUT_FILE = ROOT / "backend" / "app" / "blockchain" / "TrustLedger.compiled.json"

SOLC_VERSION = "0.8.24"

if __name__ == "__main__":
    # The former solc-bin.ethereum.org hostname no longer resolves reliably.
    solcx.install.BINARY_DOWNLOAD_BASE = (
        "https://binaries.soliditylang.org/{}-amd64/{}"
    )
    install_solc(SOLC_VERSION)
    with CONTRACT_FILE.open("r", encoding="utf-8") as f:
        source = f.read()

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {CONTRACT_FILE.name: {"content": source}},
            "settings": {
                "outputSelection": {
                    "*": {
                        "*": ["abi", "evm.bytecode.object"]
                    }
                }
            },
        },
        solc_version=SOLC_VERSION,
    )

    contract_key = next(iter(compiled["contracts"][CONTRACT_FILE.name].keys()))
    contract_data = compiled["contracts"][CONTRACT_FILE.name][contract_key]
    compiled_output = {
        "abi": contract_data["abi"],
        "bytecode": contract_data["evm"]["bytecode"]["object"],
    }
    OUTPUT_FILE.write_text(json.dumps(compiled_output, indent=2), encoding="utf-8")
    BACKEND_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    BACKEND_OUTPUT_FILE.write_text(json.dumps(compiled_output, indent=2), encoding="utf-8")
    print(f"Compiled {CONTRACT_FILE.name} to {OUTPUT_FILE} and {BACKEND_OUTPUT_FILE}")
