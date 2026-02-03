"""
Query operations for Transaction Management.

Additional query-focused task sets.
"""

import random

from locust import TaskSet, tag, task


class QueryTaskset(TaskSet):
    """
    Transaction query task set.
    Tests various query endpoints.
    """

    min_wait = 50  # ms
    max_wait = 200  # ms

    @task(2)
    @tag("query", "by-card")
    def query_by_card(self):
        """Query transactions by card ID."""
        card_id = f"{random.choice(['4111', '5411', '3700'])}{'*' * 8}{random.randint(1000, 9999)}"

        response = self.client.get(
            "/api/v1/transactions",
            params={"card_id": card_id, "page_size": 50},
            headers=self.user.headers,
            name="GET /api/v1/transactions (by card)",
        )

        if response.status_code == 200:
            self.user.metrics.increment("query_by_card_success")

    @task(1)
    @tag("query", "by-merchant")
    def query_by_merchant(self):
        """Query transactions by merchant."""
        merchant_id = f"M{random.randint(10000, 99999)}"

        response = self.client.get(
            "/api/v1/transactions",
            params={"merchant_id": merchant_id, "page_size": 100},
            headers=self.user.headers,
            name="GET /api/v1/transactions (by merchant)",
        )

        if response.status_code == 200:
            self.user.metrics.increment("query_by_merchant_success")

    @task(1)
    @tag("query", "analytics")
    def query_analytics(self):
        """Query transaction analytics."""
        response = self.client.get(
            "/api/v1/metrics",
            params={"time_range": random.choice(["1h", "24h", "7d"])},
            headers=self.user.headers,
            name="GET /api/v1/metrics",
        )

        if response.status_code == 200:
            self.user.metrics.increment("query_analytics_success")
