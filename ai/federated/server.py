from __future__ import annotations

import flwr as fl


def weighted_average(metrics):
    total = sum(num_examples for num_examples, _ in metrics)
    accuracy = sum(num_examples * item.get("accuracy", 0) for num_examples, item in metrics) / max(total, 1)
    trust_score = sum(num_examples * item.get("trust_score", 0) for num_examples, item in metrics) / max(total, 1)
    return {"accuracy": accuracy, "trust_score": trust_score}


def main() -> None:
    strategy = fl.server.strategy.FedAvg(evaluate_metrics_aggregation_fn=weighted_average)
    fl.server.start_server(server_address="0.0.0.0:8080", config=fl.server.ServerConfig(num_rounds=5), strategy=strategy)


if __name__ == "__main__":
    main()
