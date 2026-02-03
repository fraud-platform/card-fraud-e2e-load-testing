"""
Transaction Management task sets for load testing.

Priority: MEDIUM - Ingestion and query operations
Target: ~50 TPS local target
"""

import random
import uuid
from datetime import UTC, datetime

from locust import TaskSet, tag, task


class IngestionTaskset(TaskSet):
    """
    Transaction ingestion task set.
    Tests POST /api/v1/decision-events endpoint.
    """

    min_wait = 20  # ms
    max_wait = 100  # ms

    @task(1)
    @tag("ingestion", "single")
    def ingest_single_transaction(self):
        """Ingest a single transaction."""
        event = self._generate_decision_event()

        response = self.client.post(
            "/api/v1/decision-events",
            json=event,
            headers=self.user.headers,
            name="POST /api/v1/decision-events",
        )

        if response.status_code in [200, 201, 202]:
            self.user.metrics.increment("ingestion_success")
        else:
            self.user.metrics.increment("ingestion_error")

    @task(1)
    @tag("ingestion", "batch")
    def ingest_batch_transactions(self):
        """Simulate a second ingestion path using the same event endpoint."""
        event = self._generate_decision_event()

        response = self.client.post(
            "/api/v1/decision-events",
            json=event,
            headers=self.user.headers,
            name="POST /api/v1/decision-events (alt)",
        )

        if response.status_code in [200, 201, 202]:
            self.user.metrics.increment("ingestion_batch_success")

    def _generate_decision_event(self) -> dict:
        """Generate a single decision event."""
        txn_id = f"txn_{uuid.uuid4().hex[:16]}"
        card_last4 = str(random.randint(1000, 9999))
        decision = random.choice(["APPROVE", "DECLINE"])
        return {
            "event_version": "1.0",
            "transaction_id": txn_id,
            "evaluation_type": random.choice(["AUTH", "MONITORING"]),
            "occurred_at": datetime.now(UTC).isoformat(),
            "produced_at": datetime.now(UTC).isoformat(),
            "decision": decision,
            "decision_reason": random.choice(["RULE_MATCH", "DEFAULT_ALLOW"]),
            "transaction": {
                "card_id": f"tok_{uuid.uuid4().hex[:12]}",
                "card_last4": card_last4,
                "card_network": random.choice(["VISA", "MASTERCARD", "AMEX"]),
                "amount": round(random.uniform(100, 5000), 2),
                "currency": "USD",
                "country": random.choice(["IN", "US", "SG"]),
                "merchant_id": f"M{random.randint(10000, 99999)}",
                "mcc": random.choice(["5411", "5812", "4111", "7995", "5311"]),
            },
            "matched_rules": [],
        }


class ListQueryTaskset(TaskSet):
    """
    Transaction list/query task set.
    Tests GET /api/v1/transactions endpoint.
    """

    min_wait = 50  # ms
    max_wait = 200  # ms

    @task(2)
    @tag("query", "list")
    def list_transactions(self):
        """List transactions with filters."""
        params = {
            "page_size": random.randint(10, 100),
        }

        # Add random filters
        if random.random() > 0.5:
            params["country"] = random.choice(["IN", "US", "SG"])
        if random.random() > 0.7:
            params["currency"] = random.choice(["INR", "USD", "EUR"])

        response = self.client.get(
            "/api/v1/transactions",
            params=params,
            headers=self.user.headers,
            name="GET /api/v1/transactions",
        )

        if response.status_code == 200:
            self.user.metrics.increment("query_list_success")

    @task(1)
    @tag("query", "detail")
    def get_transaction_detail(self):
        """Get transaction by ID."""
        list_response = self.client.get(
            "/api/v1/transactions",
            params={"page_size": 1},
            headers=self.user.headers,
            name="GET /api/v1/transactions (for detail)",
        )
        if list_response.status_code != 200:
            return

        items = list_response.json().get("items", [])
        if not items:
            return
        txn_id = items[0].get("transaction_id")
        if not txn_id:
            return

        response = self.client.get(
            f"/api/v1/transactions/{txn_id}",
            headers=self.user.headers,
            name="GET /api/v1/transactions/{id}",
        )

        if response.status_code == 200:
            self.user.metrics.increment("query_detail_success")
