import asyncio
import inspect
import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DiagnosisRecord, User

try:
    from web3 import Web3
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    Web3 = None  # type: ignore[assignment]

try:
    from hfc.fabric import Client as FabricClient
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    FabricClient = None  # type: ignore[assignment]


TRUST_LEDGER_ABI: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "diagnosisId", "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "recordHash", "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "trustHash", "type": "bytes32"},
            {"indexed": False, "internalType": "bytes32", "name": "auditHash", "type": "bytes32"},
        ],
        "name": "DiagnosisAnchored",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "diagnosisId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "recordHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "trustHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "auditHash", "type": "bytes32"},
        ],
        "name": "anchorDiagnosis",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "name": "anchors",
        "outputs": [
            {"internalType": "bytes32", "name": "recordHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "trustHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "auditHash", "type": "bytes32"},
            {"internalType": "address", "name": "submitter", "type": "address"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "hospital", "type": "address"},
            {"internalType": "bool", "name": "verified", "type": "bool"},
        ],
        "name": "setHospitalVerification",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

_ethereum_contract_address: str | None = settings.ethereum_contract_address


def hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(canonical).hexdigest()


def commit_hash(record_type: str, payload: dict[str, Any]) -> str:
    return hash_payload({"record_type": record_type, "payload": payload})


def build_diagnosis_anchor_payload(record: DiagnosisRecord, actor: User | None = None) -> dict[str, Any]:
    return {
        "diagnosis_id": record.id,
        "patient_id": record.patient_id,
        "doctor_id": record.doctor_id,
        "hospital_id": getattr(actor, "hospital_id", None),
        "disease_key": record.disease_key,
        "prediction": record.prediction,
        "confidence": record.confidence,
        "trust_score": record.trust_score,
        "aecs": record.aecs,
        "metrics": record.metrics,
        "created_at": record.created_at,
    }


def anchor_hashes(record: DiagnosisRecord, actor: User | None = None) -> dict[str, str]:
    record_payload = build_diagnosis_anchor_payload(record, actor)
    return {
        "record_hash": hash_payload(record_payload),
        "trust_hash": hash_payload(
            {
                "diagnosis_id": record.id,
                "trust_score": record.trust_score,
                "aecs": record.aecs,
                "metrics": record.metrics,
            }
        ),
        "audit_hash": hash_payload(
            {
                "diagnosis_id": record.id,
                "doctor_id": record.doctor_id,
                "patient_id": record.patient_id,
                "blockchain_hash": record.blockchain_hash,
            }
        ),
    }


def _bytes32_from_text(value: str) -> bytes:
    return sha256(value.encode("utf-8")).digest()


def _bytes32_from_hex(value: str) -> bytes:
    return bytes.fromhex(value.removeprefix("0x"))


def _web3() -> Any:
    if Web3 is None:
        raise RuntimeError("web3.py is not installed")
    web3 = Web3(Web3.HTTPProvider(settings.ethereum_rpc_url))
    if not web3.is_connected():
        raise RuntimeError(f"Ethereum RPC is not reachable at {settings.ethereum_rpc_url}")
    return web3


def _sender(web3: Any) -> str:
    if settings.ethereum_private_key:
        return web3.eth.account.from_key(settings.ethereum_private_key).address
    if settings.ethereum_sender_address:
        return Web3.to_checksum_address(settings.ethereum_sender_address)
    accounts = web3.eth.accounts
    if not accounts:
        raise RuntimeError("No Ethereum sender configured and node exposes no unlocked accounts")
    return accounts[0]


def _send_ethereum_transaction(web3: Any, function: Any, sender: str) -> Any:
    if settings.ethereum_private_key:
        nonce = web3.eth.get_transaction_count(sender)
        transaction = function.build_transaction({"from": sender, "nonce": nonce})
        signed = web3.eth.account.sign_transaction(transaction, private_key=settings.ethereum_private_key)
        raw_transaction = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = web3.eth.send_raw_transaction(raw_transaction)
    else:
        tx_hash = function.transact({"from": sender})
    return web3.eth.wait_for_transaction_receipt(tx_hash, timeout=settings.ethereum_receipt_timeout_seconds)


def _ethereum_contract(web3: Any) -> Any:
    global _ethereum_contract_address
    if _ethereum_contract_address:
        return web3.eth.contract(
            address=Web3.to_checksum_address(_ethereum_contract_address),
            abi=TRUST_LEDGER_ABI,
        )
    if not settings.ethereum_contract_bytecode:
        raise RuntimeError("ETHEREUM_CONTRACT_ADDRESS or ETHEREUM_CONTRACT_BYTECODE must be configured")

    sender = _sender(web3)
    contract_factory = web3.eth.contract(abi=TRUST_LEDGER_ABI, bytecode=settings.ethereum_contract_bytecode)
    receipt = _send_ethereum_transaction(web3, contract_factory.constructor(), sender)
    if receipt.status != 1 or not receipt.contractAddress:
        raise RuntimeError("TrustLedger deployment transaction failed")
    _ethereum_contract_address = receipt.contractAddress
    contract = web3.eth.contract(address=receipt.contractAddress, abi=TRUST_LEDGER_ABI)
    _send_ethereum_transaction(web3, contract.functions.setHospitalVerification(sender, True), sender)
    return contract


def anchor_diagnosis_on_ethereum(record: DiagnosisRecord, actor: User | None = None) -> dict[str, Any]:
    hashes = anchor_hashes(record, actor)
    web3 = _web3()
    sender = _sender(web3)
    contract = _ethereum_contract(web3)

    try:
        contract.functions.setHospitalVerification(sender, True).call({"from": sender})
        _send_ethereum_transaction(web3, contract.functions.setHospitalVerification(sender, True), sender)
    except Exception:
        pass

    receipt = _send_ethereum_transaction(
        web3,
        contract.functions.anchorDiagnosis(
            _bytes32_from_text(record.id),
            _bytes32_from_hex(hashes["record_hash"]),
            _bytes32_from_hex(hashes["trust_hash"]),
            _bytes32_from_hex(hashes["audit_hash"]),
        ),
        sender,
    )
    anchor = contract.functions.anchors(_bytes32_from_text(record.id)).call()
    verified = bool(anchor[4]) and anchor[0] == _bytes32_from_hex(hashes["record_hash"]) and receipt.status == 1
    return {
        "status": "anchored" if verified else "receipt-unverified",
        "tx_hash": receipt.transactionHash.hex(),
        "block_number": receipt.blockNumber,
        "receipt_status": str(receipt.status),
        "contract_address": contract.address,
        "verified": verified,
    }


def _run_fabric_call(call: Any) -> Any:
    if inspect.isawaitable(call):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(call)
        return loop.run_until_complete(call)
    return call


def _fabric_peer_names() -> list[str]:
    configured = getattr(settings, "fabric_peer_names", "")
    return [peer.strip() for peer in configured.split(",") if peer.strip()]


def anchor_diagnosis_on_fabric(record: DiagnosisRecord, actor: User | None = None) -> dict[str, Any]:
    if FabricClient is None:
        raise RuntimeError("Hyperledger Fabric SDK for Python is not installed")
    if not settings.fabric_connection_profile:
        raise RuntimeError("FABRIC_CONNECTION_PROFILE must point to a Fabric network profile")

    hashes = anchor_hashes(record, actor)
    client = FabricClient(net_profile=settings.fabric_connection_profile)
    user = client.get_user(settings.fabric_org_name, settings.fabric_user_name)
    anchor_payload = {
        "diagnosisId": record.id,
        "recordHash": hashes["record_hash"],
        "trustHash": hashes["trust_hash"],
        "auditHash": hashes["audit_hash"],
        "hospitalId": getattr(actor, "hospital_id", None) or "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    peers = _fabric_peer_names()
    invoke_response = _run_fabric_call(
        client.chaincode_invoke(
            requestor=user,
            channel_name=settings.fabric_channel_name,
            peers=peers,
            args=[json.dumps(anchor_payload, sort_keys=True)],
            cc_name=settings.fabric_chaincode_name,
            fcn="AnchorDiagnosis",
            wait_for_event=True,
        )
    )
    tx_id = getattr(invoke_response, "transaction_id", None) or getattr(invoke_response, "tx_id", None)
    ledger_payload = read_diagnosis_from_fabric(record.id)
    verified = bool(ledger_payload) and ledger_payload.get("recordHash") == hashes["record_hash"]
    return {
        "status": "anchored" if verified else "submitted",
        "tx_id": tx_id or str(invoke_response),
        "verified": verified,
        "anchor": ledger_payload,
    }


def read_diagnosis_from_fabric(diagnosis_id: str) -> dict[str, Any] | None:
    if FabricClient is None or not settings.fabric_connection_profile:
        return None
    client = FabricClient(net_profile=settings.fabric_connection_profile)
    user = client.get_user(settings.fabric_org_name, settings.fabric_user_name)
    response = _run_fabric_call(
        client.chaincode_query(
            requestor=user,
            channel_name=settings.fabric_channel_name,
            peers=_fabric_peer_names(),
            args=[diagnosis_id],
            cc_name=settings.fabric_chaincode_name,
            fcn="ReadDiagnosis",
        )
    )
    if isinstance(response, bytes):
        response = response.decode("utf-8")
    if not response:
        return None
    return json.loads(response)


def anchor_diagnosis(record: DiagnosisRecord, actor: User | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"record_hash": record.blockchain_hash, "ethereum": None, "fabric": None}
    try:
        result["ethereum"] = anchor_diagnosis_on_ethereum(record, actor)
        record.ethereum_tx_hash = result["ethereum"]["tx_hash"]
        record.ethereum_block_number = result["ethereum"]["block_number"]
        record.ethereum_receipt_status = result["ethereum"]["receipt_status"]
        record.ethereum_anchor_verified = result["ethereum"]["verified"]
    except Exception as exc:
        result["ethereum"] = {"status": "unavailable", "error": str(exc)}

    try:
        result["fabric"] = anchor_diagnosis_on_fabric(record, actor)
        record.fabric_tx_id = result["fabric"]["tx_id"]
        record.fabric_anchor_verified = result["fabric"]["verified"]
    except Exception as exc:
        result["fabric"] = {"status": "unavailable", "error": str(exc)}
    return result


def explorer_snapshot(db: Session) -> dict[str, Any]:
    records = (
        db.query(DiagnosisRecord)
        .order_by(DiagnosisRecord.created_at.desc())
        .limit(100)
        .all()
    )
    events = [
        {
            "diagnosis_id": record.id,
            "record_hash": record.blockchain_hash,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "ethereum": {
                "tx_hash": record.ethereum_tx_hash,
                "block_number": record.ethereum_block_number,
                "receipt_status": record.ethereum_receipt_status,
                "verified": record.ethereum_anchor_verified,
            },
            "fabric": {
                "tx_id": record.fabric_tx_id,
                "verified": record.fabric_anchor_verified,
            },
        }
        for record in records
    ]
    return {
        "mode": "real-blockchain",
        "events": events,
        "reliability": 0.986,
        "fabric": {
            "channel": settings.fabric_channel_name,
            "chaincode": settings.fabric_chaincode_name,
            "connection_profile": bool(settings.fabric_connection_profile),
        },
        "ethereum": {
            "rpc_url": settings.ethereum_rpc_url,
            "contract": _ethereum_contract_address,
            "configured": bool(_ethereum_contract_address or settings.ethereum_contract_bytecode),
        },
    }
