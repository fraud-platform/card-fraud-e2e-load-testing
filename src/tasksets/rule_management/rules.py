"""
Rule Management task sets for load testing.

Priority: LOW - Governance API, infrequent writes
Target: ~50 TPS local target
"""

import random

from locust import TaskSet, tag, task


class ListRulesTaskset(TaskSet):
    """
    List rules task set.
    Tests GET /api/v1/rules endpoint.
    """

    min_wait = 100  # ms
    max_wait = 500  # ms

    @task(1)
    @tag("rules", "list")
    def list_rules(self):
        """List all rules."""
        response = self.client.get(
            "/api/v1/rules",
            headers=self.user.headers,
            name="GET /api/v1/rules",
        )

        if response.status_code == 200:
            self.user.metrics.increment("rules_list_success")

    @task(1)
    @tag("rules", "list-filtered")
    def list_rules_filtered(self):
        """List rules with filters."""
        params = {
            "rule_type": random.choice(["AUTH", "MONITORING"]),
            "status": random.choice(["DRAFT", "APPROVED", "ACTIVE"]),
        }

        response = self.client.get(
            "/api/v1/rules",
            params=params,
            headers=self.user.headers,
            name="GET /api/v1/rules (filtered)",
        )

        if response.status_code == 200:
            self.user.metrics.increment("rules_list_filtered_success")


class GetRuleTaskset(TaskSet):
    """
    Get single rule task set.
    Tests GET /api/v1/rules/{id} endpoint.
    """

    min_wait = 50  # ms
    max_wait = 200  # ms

    @task(1)
    @tag("rules", "get")
    def get_rule(self):
        """Get a single rule by ID."""
        list_response = self.client.get(
            "/api/v1/rules",
            params={"limit": 1},
            headers=self.user.headers,
            name="GET /api/v1/rules (for get)",
        )
        if list_response.status_code != 200:
            return

        items = list_response.json().get("items", [])
        if not items:
            return
        rule_id = items[0].get("rule_id")
        if not rule_id:
            return

        response = self.client.get(
            f"/api/v1/rules/{rule_id}",
            headers=self.user.headers,
            name="GET /api/v1/rules/{id}",
        )

        if response.status_code == 200:
            self.user.metrics.increment("rules_get_success")


class CreateRuleTaskset(TaskSet):
    """
    Create rule task set.
    Tests POST /api/v1/rules endpoint.
    """

    min_wait = 200  # ms
    max_wait = 1000  # ms

    @task(1)
    @tag("rules", "create")
    def create_rule(self):
        """Create a new rule."""
        rule = self._generate_rule()

        response = self.client.post(
            "/api/v1/rules",
            json=rule,
            headers=self.user.headers,
            name="POST /api/v1/rules",
        )

        if response.status_code in [200, 201]:
            self.user.metrics.increment("rules_create_success")

    def _generate_rule(self) -> dict:
        """Generate a test rule."""
        return {
            "rule_name": f"Load Test Rule {random.randint(1000, 9999)}",
            "description": "Generated rule for load testing",
            "rule_type": random.choice(["AUTH", "MONITORING"]),
            "priority": random.randint(1, 100),
            "condition_tree": {
                "field": "amount",
                "operator": ">",
                "value": random.randint(1000, 50000),
            },
        }


class RulesetTaskset(TaskSet):
    """
    Ruleset management task set.
    Tests ruleset publishing and activation.
    """

    min_wait = 500  # ms
    max_wait = 2000  # ms

    @task(1)
    @tag("rulesets", "list")
    def list_rulesets(self):
        """List all rulesets."""
        response = self.client.get(
            "/api/v1/rulesets",
            headers=self.user.headers,
            name="GET /api/v1/rulesets",
        )

        if response.status_code == 200:
            self.user.metrics.increment("rulesets_list_success")

    @task(1)
    @tag("rulesets", "publish")
    def publish_ruleset(self):
        """Publish a ruleset."""
        ruleset = self._generate_ruleset()

        response = self.client.post(
            "/api/v1/rulesets",
            json=ruleset,
            headers=self.user.headers,
            name="POST /api/v1/rulesets (publish)",
        )

        if response.status_code in [200, 201]:
            self.user.metrics.increment("rulesets_publish_success")

    def _generate_ruleset(self) -> dict:
        """Generate a test ruleset."""
        return {
            "name": f"Load Test Ruleset {random.randint(1000, 9999)}",
            "description": "Generated ruleset for load testing",
            "environment": "local",
            "region": "IN",
            "country": "IN",
            "rule_type": random.choice(["AUTH", "MONITORING"]),
        }
