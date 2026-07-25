"""Load tests for the Arc DevKit REST API.

Exercises only read-only, side-effect-free endpoints (health, fee quotes,
gas estimates, network info) — no payment/bridge/job endpoints, since those
sign and broadcast real transactions and must never run under load testing.

Run against a locally running API:
    uvicorn arc_devkit.api.main:app --reload
    locust -f locustfile.py --host http://localhost:8000

Or headless:
    locust -f locustfile.py --host http://localhost:8000 \\
        --headless -u 20 -r 5 -t 1m
"""

from locust import HttpUser, between, task

_ADDRESS = "0x000000000000000000000000000000000000dEaD"


class ArcDevKitApiUser(HttpUser):
    """Simulates a client polling read-only Arc DevKit API endpoints."""

    wait_time = between(0.5, 2.0)

    @task(3)
    def health(self) -> None:
        self.client.get("/health", name="/health")

    @task(2)
    def fee_quote_native(self) -> None:
        self.client.get(
            "/fees/quote",
            params={"to": _ADDRESS, "amount": 1.0, "token": "native"},
            name="/fees/quote (native)",
        )

    @task(1)
    def fee_quote_usdc(self) -> None:
        self.client.get(
            "/fees/quote",
            params={"to": _ADDRESS, "amount": 1.0, "token": "usdc"},
            name="/fees/quote (usdc)",
        )

    @task(2)
    def gas_estimate(self) -> None:
        self.client.get(
            "/debug/estimate",
            params={"to": _ADDRESS, "amount": 1.0},
            name="/debug/estimate",
        )

    @task(1)
    def balance(self) -> None:
        self.client.get(f"/agents/balance/{_ADDRESS}", name="/agents/balance/{address}")
