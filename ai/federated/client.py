from __future__ import annotations

import flwr as fl


class TrustMedClient(fl.client.NumPyClient):
    def get_parameters(self, config):
        return []

    def fit(self, parameters, config):
        return [], 128, {"trust_score": 0.88}

    def evaluate(self, parameters, config):
        return 0.12, 128, {"accuracy": 0.91, "trust_score": 0.89}


def main() -> None:
    fl.client.start_numpy_client(server_address="127.0.0.1:8080", client=TrustMedClient())


if __name__ == "__main__":
    main()
