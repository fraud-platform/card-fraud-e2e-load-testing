"""
Ops Analyst Agent — Investigation tasksets.

Endpoints exercised:
  POST /api/v1/ops-agent/investigations/run
  GET  /api/v1/ops-agent/investigations/{run_id}
  GET  /api/v1/ops-agent/transactions/{transaction_id}/insights

Priority: MEDIUM-LOW — advisory engine, P99 <= 2s deterministic
"""

# Pre-seeded transaction IDs inserted by scripts/load_test_data.py.
# The list is populated at runtime from OPS_ANALYST_TRANSACTION_IDS env var
# (comma-separated) so no IDs are hardcoded here.
import os
import random
import uuid

from locust import TaskSet, tag, task

_RAW = os.getenv("OPS_ANALYST_TRANSACTION_IDS", "")
SEEDED_TRANSACTION_IDS: list[str] = [t.strip() for t in _RAW.split(",") if t.strip()]

# Fallback: generate deterministic-looking UUIDs so tests don't crash when env
# var is absent.  These will 404 on the DB but that is acceptable for smoke runs.
if not SEEDED_TRANSACTION_IDS:
    SEEDED_TRANSACTION_IDS = [str(uuid.UUID(int=i)) for i in range(1, 6)]


class InvestigationTaskset(TaskSet):
    """
    Exercise the investigation pipeline end-to-end.

    Flow: POST run → GET result by run_id
    """

    min_wait = 500  # ms — investigation is heavier than a simple query
    max_wait = 2000

    @task(3)
    @tag("investigations", "run")
    def run_investigation(self):
        """Trigger a quick investigation for a random seeded transaction."""
        txn_id = random.choice(SEEDED_TRANSACTION_IDS)

        response = self.client.post(
            "/api/v1/ops-agent/investigations/run",
            json={"transaction_id": txn_id, "mode": "quick"},
            headers=self.user.headers,
            name="POST /api/v1/ops-agent/investigations/run",
        )

        if response.status_code in (200, 201):
            self.user.metrics.increment("investigations_run_success")
            # Follow-up: fetch the result
            data = response.json()
            run_id = data.get("run_id")
            if run_id:
                self.client.get(
                    f"/api/v1/ops-agent/investigations/{run_id}",
                    headers=self.user.headers,
                    name="GET /api/v1/ops-agent/investigations/{run_id}",
                )
                self.user.metrics.increment("investigations_get_success")
        else:
            self.user.metrics.increment("investigations_run_error")

    @task(1)
    @tag("investigations", "insights")
    def get_transaction_insights(self):
        """Fetch insights for a transaction that already has a run."""
        txn_id = random.choice(SEEDED_TRANSACTION_IDS)

        response = self.client.get(
            f"/api/v1/ops-agent/transactions/{txn_id}/insights",
            headers=self.user.headers,
            name="GET /api/v1/ops-agent/transactions/{id}/insights",
        )

        if response.status_code == 200:
            self.user.metrics.increment("insights_get_success")

