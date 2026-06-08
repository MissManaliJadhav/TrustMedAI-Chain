from datetime import datetime, timezone

HOSPITAL_NODES = [
    {"id": "hospital-a", "name": "Hospital Node A", "trust": 0.91, "reputation": 0.88},
    {"id": "hospital-b", "name": "Hospital Node B", "trust": 0.87, "reputation": 0.84},
    {"id": "hospital-c", "name": "Hospital Node C", "trust": 0.89, "reputation": 0.86},
    {"id": "hospital-d", "name": "Hospital Node D", "trust": 0.85, "reputation": 0.82},
]


def federated_dashboard() -> dict:
    consensus = round(sum(node["trust"] for node in HOSPITAL_NODES) / len(HOSPITAL_NODES), 3)
    return {
        "nodes": HOSPITAL_NODES,
        "model_weight_round": 12,
        "consensus_reliability": consensus,
        "cifts": {
            "trust_synchronization": consensus,
            "hospital_reputation": round(sum(node["reputation"] for node in HOSPITAL_NODES) / len(HOSPITAL_NODES), 3),
            "trust_evolution": [0.79, 0.82, 0.84, 0.87, consensus],
        },
    }


def synchronize_trust() -> dict:
    for node in HOSPITAL_NODES:
        node["trust"] = round(min(0.99, node["trust"] + 0.006), 3)
    return {"status": "synchronized", "timestamp": datetime.now(timezone.utc).isoformat(), "dashboard": federated_dashboard()}
