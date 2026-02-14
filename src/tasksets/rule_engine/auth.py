"""
Rule Engine AUTH Task Set for load testing.

Priority: HIGH - Core decisioning engine
Target: 10,000+ RPS, P50 < 5ms, P95 < 15ms, P99 < 30ms
"""

from datetime import UTC

from faker import Faker
from locust import TaskSet, tag, task

fake = Faker()


class AuthTaskset(TaskSet):
    """
    AUTH evaluation task set.

    Tests POST /v1/evaluate/auth endpoint.
    Expected: P50 < 5ms, P95 < 15ms, P99 < 30ms
    """

    min_wait = 1  # ms
    max_wait = 10  # ms

    @task(1)
    @tag("auth", "high-priority")
    def evaluate_auth(self):
        """AUTH evaluation with varied transaction amounts."""
        transaction = self._generate_transaction()

        with self.user.metrics.timer("auth"):
            response = self.client.post(
                f"{self.user.rule_engine_auth_url}/v1/evaluate/auth",
                json=transaction,
                headers=self.user.headers,
                name="POST /v1/evaluate/auth",
            )

            if response.status_code == 200:
                self.user.metrics.increment("auth_success")
                data = response.json()
                assert "decision" in data
                assert data["transaction_id"] == transaction["transaction_id"]
            else:
                self.user.metrics.increment("auth_error")

    def _generate_transaction(self) -> dict:
        """Generate a test transaction with varied amounts."""
        import random
        import uuid
        from datetime import datetime

        # Varied amounts: 80% normal (100-5000), 15% high (5000-50000), 5% very high (50000-500000)
        rand = random.random()
        if rand < 0.80:
            amount = round(random.uniform(100, 5000), 2)
        elif rand < 0.95:
            amount = round(random.uniform(5000, 50000), 2)
        else:
            amount = round(random.uniform(50000, 500000), 2)

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
            "timestamp": datetime.now(UTC).isoformat(),
        }
