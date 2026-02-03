"""
Rule Engine POSTAUTH Task Set for load testing.

Priority: MEDIUM - Post-authorization analytics
Target: 30% of traffic, <100ms p99 latency
"""

from datetime import UTC

from faker import Faker
from locust import TaskSet, tag, task

fake = Faker()


class PostauthTaskset(TaskSet):
    """
    POSTAUTH evaluation task set.

    Tests POST /v1/evaluate/monitoring endpoint.
    POSTAUTH is less latency-critical than PREAUTH.
    """

    min_wait = 10  # ms
    max_wait = 50  # ms

    @task(3)
    @tag("postauth", "normal")
    def evaluate_postauth_normal(self):
        """Normal POSTAUTH evaluation."""
        transaction = self._generate_transaction("normal")

        response = self.client.post(
            "/v1/evaluate/monitoring",
            json=transaction,
            headers=self.user.headers,
            name="POST /v1/evaluate/monitoring",
        )

        if response.status_code == 200:
            data = response.json()
            assert "decision" in data

    @task(1)
    @tag("postauth", "chargeback")
    def evaluate_postauth_chargeback(self):
        """POSTAUTH for chargeback scenarios."""
        transaction = self._generate_transaction("chargeback")

        response = self.client.post(
            "/v1/evaluate/monitoring",
            json=transaction,
            headers=self.user.headers,
            name="POST /v1/evaluate/monitoring (chargeback)",
        )

        if response.status_code == 200:
            self.user.metrics.increment("postauth_chargeback")

    def _generate_transaction(self, risk_level: str = "normal") -> dict:
        """Generate a test transaction."""
        import random
        import uuid
        from datetime import datetime

        amount_ranges = {
            "normal": (100, 5000),
            "chargeback": (500, 50000),
        }

        amount = round(random.uniform(*amount_ranges[risk_level]), 2)

        return {
            "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
            "card_hash": f"card_{uuid.uuid4().hex[:12]}",
            "card_network": random.choice(["VISA", "MASTERCARD", "AMEX"]),
            "merchant_id": f"M{random.randint(10000, 99999)}",
            "ip_address": fake.ipv4(),
            "amount": amount,
            "currency": "USD",
            "country_code": random.choice(["IN", "US", "SG"]),
            "transaction_type": "PURCHASE",
            "decision": random.choice(["APPROVE", "DECLINE"]),
            "timestamp": datetime.now(UTC).isoformat(),
        }
