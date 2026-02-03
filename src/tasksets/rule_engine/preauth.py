"""
Rule Engine PREAUTH Task Set for load testing.

Priority: HIGH - Core decisioning engine
Target: 10,000+ RPS, P50 < 5ms, P95 < 15ms, P99 < 30ms
"""

from datetime import UTC

from faker import Faker
from locust import TaskSet, tag, task

fake = Faker()


class PreauthTaskset(TaskSet):
    """
    PREAUTH evaluation task set.

    Tests POST /v1/evaluate/auth endpoint.
    Expected: P50 < 5ms, P95 < 15ms, P99 < 30ms
    """

    min_wait = 1  # ms
    max_wait = 10  # ms

    @task(1)
    @tag("preauth", "high-priority")
    def evaluate_preauth_normal(self):
        """Normal PREAUTH evaluation."""
        transaction = self._generate_transaction("normal")

        with self.user.metrics.timer("preauth_normal"):
            response = self.client.post(
                "/v1/evaluate/auth",
                json=transaction,
                headers=self.user.headers,
                name="POST /v1/evaluate/auth",
            )

            if response.status_code == 200:
                self.user.metrics.increment("preauth_success")
                data = response.json()
                assert "decision" in data
                assert data["transaction_id"] == transaction["transaction_id"]
            else:
                self.user.metrics.increment("preauth_error")

    @task(1)
    @tag("preauth", "high-value")
    def evaluate_preauth_high_value(self):
        """High-value PREAUTH (potential decline)."""
        transaction = self._generate_transaction("high")

        response = self.client.post(
            "/v1/evaluate/auth",
            json=transaction,
            headers=self.user.headers,
            name="POST /v1/evaluate/auth (high-value)",
        )

        if response.status_code == 200:
            self.user.metrics.increment("preauth_high_value")

    @task(1)
    @tag("preauth", "suspicious")
    def evaluate_preauth_suspicious(self):
        """Suspicious PREAUTH (review/decline likely)."""
        transaction = self._generate_transaction("suspicious")

        response = self.client.post(
            "/v1/evaluate/auth",
            json=transaction,
            headers=self.user.headers,
            name="POST /v1/evaluate/auth (suspicious)",
        )

        if response.status_code == 200:
            self.user.metrics.increment("preauth_suspicious")

    def _generate_transaction(self, risk_level: str = "normal") -> dict:
        """Generate a test transaction."""
        import random
        import uuid
        from datetime import datetime

        amount_ranges = {
            "normal": (100, 5000),
            "high": (5000, 50000),
            "suspicious": (50000, 500000),
        }

        amount = round(random.uniform(*amount_ranges[risk_level]), 2)

        return {
            "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
            "card_hash": f"card_{uuid.uuid4().hex[:12]}",
            "card_network": random.choice(["VISA", "MASTERCARD", "AMEX"]),
            "merchant_id": f"M{random.randint(10000, 99999)}",
            "ip_address": fake.ipv4() if risk_level != "suspicious" else "192.168.1.1",
            "amount": amount,
            "currency": "USD",
            "country_code": random.choice(["IN", "US", "SG"]),
            "transaction_type": "PURCHASE",
            "timestamp": datetime.now(UTC).isoformat(),
        }
