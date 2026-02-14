"""
Ops Analyst Agent — Worklist (recommendations) tasksets.

Endpoints exercised:
  GET  /api/v1/ops-agent/worklist/recommendations
  POST /api/v1/ops-agent/worklist/recommendations/{id}/acknowledge

Priority: MEDIUM-LOW — analyst review queue, low RPS
"""

import random

from locust import TaskSet, tag, task

SEVERITIES = ["HIGH", "MEDIUM", "LOW", None]


class WorklistTaskset(TaskSet):
    """
    Exercise the analyst worklist — list recommendations and acknowledge them.

    The acknowledge step uses action=acknowledge (not reject) to keep test data
    cycling through valid states without permanently closing recommendations.
    """

    min_wait = 200
    max_wait = 1000

    @task(4)
    @tag("worklist", "list")
    def list_recommendations(self):
        """List open recommendations with optional severity filter."""
        params: dict = {"limit": random.choice([10, 25, 50])}

        severity = random.choice(SEVERITIES)
        if severity:
            params["severity"] = severity

        response = self.client.get(
            "/api/v1/ops-agent/worklist/recommendations",
            params=params,
            headers=self.user.headers,
            name="GET /api/v1/ops-agent/worklist/recommendations",
        )

        if response.status_code == 200:
            self.user.metrics.increment("worklist_list_success")
            data = response.json()
            items = data.get("recommendations", [])

            # Opportunistically acknowledge the first OPEN recommendation found
            for rec in items:
                if rec.get("status") == "OPEN":
                    rec_id = rec.get("recommendation_id")
                    if rec_id:
                        self._acknowledge(rec_id)
                    break

    @task(1)
    @tag("worklist", "list-paginated")
    def list_recommendations_paginated(self):
        """Paginate through recommendations using cursor."""
        response = self.client.get(
            "/api/v1/ops-agent/worklist/recommendations",
            params={"limit": 10},
            headers=self.user.headers,
            name="GET /api/v1/ops-agent/worklist/recommendations (page 1)",
        )

        if response.status_code != 200:
            return

        data = response.json()
        next_cursor = data.get("next_cursor")
        if not next_cursor:
            return

        self.client.get(
            "/api/v1/ops-agent/worklist/recommendations",
            params={"limit": 10, "cursor": next_cursor},
            headers=self.user.headers,
            name="GET /api/v1/ops-agent/worklist/recommendations (page 2)",
        )
        self.user.metrics.increment("worklist_paginated_success")

    def _acknowledge(self, recommendation_id: str) -> None:
        """Acknowledge a recommendation (non-destructive test action)."""
        response = self.client.post(
            f"/api/v1/ops-agent/worklist/recommendations/{recommendation_id}/acknowledge",
            json={"action": "acknowledge", "comment": "Load test acknowledgement"},
            headers=self.user.headers,
            name="POST /api/v1/ops-agent/worklist/recommendations/{id}/acknowledge",
        )

        if response.status_code == 200:
            self.user.metrics.increment("worklist_acknowledge_success")
        elif response.status_code == 409:
            # Already acknowledged/rejected — expected during concurrent load test
            self.user.metrics.increment("worklist_acknowledge_conflict")
