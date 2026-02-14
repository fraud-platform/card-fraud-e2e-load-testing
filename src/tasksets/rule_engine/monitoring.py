"""
Rule Engine MONITORING Task Set for load testing.

Priority: MEDIUM - Post-authorization monitoring
Target: 30% of traffic, <100ms p99 latency
"""

from datetime import UTC

from faker import Faker
from locust import TaskSet, tag, task

fake = Faker()


class MonitoringTaskset(TaskSet):
    """
    MONITORING evaluation task set.

    Tests POST /v1/evaluate/monitoring endpoint.
    MONITORING is less latency-critical than AUTH.
    """

    min_wait = 10  # ms
    max_wait = 50  # ms

    @task(1)
    @tag("monitoring", "medium-priority")
    def evaluate_monitoring(self):
        """MONITORING evaluation for post-authorization analysis."""
        transaction = self._generate_transaction()

        response = self.client.post(
            f"{self.user.rule_engine_monitoring_url}/v1/evaluate/monitoring",
            json=transaction,
            headers=self.user.headers,
            name="POST /v1/evaluate/monitoring",
        )

        if response.status_code == 200:
            data = response.json()
            assert "decision" in data
            self.user.metrics.increment("monitoring_success")

    def _generate_transaction(self) -> dict:
        """Generate a test transaction with varied amounts."""
        import random
        import uuid
        from datetime import datetime

        # Varied amounts: 80% normal (100-5000), 20% high (500-50000)
        if random.random() < 0.80:
            amount = round(random.uniform(100, 5000), 2)
        else:
            amount = round(random.uniform(500, 50000), 2)

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

