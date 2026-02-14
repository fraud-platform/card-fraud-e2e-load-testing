"""
Card Fraud E2E & Load Testing - Main Locust Entry Point

Usage:
    uv run lt-run --users=1000 --spawn-rate=100 --run-time=5m
    uv run lt-rule-engine --users=1000
    uv run lt-trans-mgmt --users=200
    uv run lt-rule-mgmt --users=50
    uv run lt-web
"""

import os
import sys
from pathlib import Path

from locust import between, events
from locust.contrib.fasthttp import FastHttpUser
from locust.runners import MasterRunner

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.defaults import get_service_config  # noqa: E402
from utilities.metrics import metrics_collector  # noqa: E402
from utilities.reporting import report_generator  # noqa: E402

# =============================================================================
# Environment Configuration
# =============================================================================

RULE_ENGINE_URL = os.getenv("RULE_ENGINE_URL", "http://localhost:8081")
RULE_ENGINE_AUTH_URL = os.getenv("RULE_ENGINE_AUTH_URL", RULE_ENGINE_URL)
RULE_ENGINE_MONITORING_URL = os.getenv("RULE_ENGINE_MONITORING_URL", RULE_ENGINE_AUTH_URL)
RULE_MGMT_URL = os.getenv("RULE_MGMT_URL", "http://localhost:8000")
TRANSACTION_MGMT_URL = os.getenv("TRANSACTION_MGMT_URL", "http://localhost:8002")
OPS_ANALYST_URL = os.getenv("OPS_ANALYST_URL", "http://localhost:8003")

# Load service configurations
SERVICE_CONFIGS = {
    "rule-engine": get_service_config("rule-engine"),
    "rule-management": get_service_config("rule-management"),
    "transaction-management": get_service_config("transaction-management"),
    "ops-analyst-agent": get_service_config("ops-analyst-agent"),
}


# =============================================================================
# Custom Events
# =============================================================================


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics and reporting."""
    metrics_collector.init(environment)

    # Restrict enabled user classes based on TEST_* env vars.
    # This prevents Locust from spawning "disabled" user classes that would otherwise do no work.
    enabled = get_enabled_user_classes()
    if enabled and hasattr(environment, "user_classes"):
        environment.user_classes = enabled

    if isinstance(environment.runner, MasterRunner):
        worker_count = getattr(environment.runner, "worker_count", None)
        if worker_count is None:
            clients = getattr(environment.runner, "clients", None)
            if isinstance(clients, dict):
                worker_count = len(clients)

        if worker_count is None:
            print("Running in distributed mode (master)")
        else:
            print(f"Running in distributed mode with {worker_count} workers")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate final report when test stops."""
    report_generator.generate_final_report(environment)


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Handle test completion."""
    if environment.stats.total.fail_ratio > 0.01:
        environment.process_exit_code = 1


# =============================================================================
# User Classes - One per Service
# =============================================================================


class RuleEngineUser(FastHttpUser):
    """
    Load test user for the Card Fraud Rule Engine.

    Priority: HIGH - Core decisioning engine
    Target: 10,000+ RPS, P50 < 5ms, P95 < 15ms, P99 < 30ms
    Traffic Mix: 70% PREAUTH, 30% POSTAUTH
    """

    config = SERVICE_CONFIGS["rule-engine"]
    host = RULE_ENGINE_AUTH_URL

    def on_start(self):
        self.metrics = metrics_collector

        self.rule_engine_auth_url = RULE_ENGINE_AUTH_URL
        self.rule_engine_monitoring_url = RULE_ENGINE_MONITORING_URL

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    tasks = []  # Loaded dynamically based on config


class TransactionManagementUser(FastHttpUser):
    """
    Load test user for Transaction Management API.

    Priority: MEDIUM - Data ingestion and queries
    Target: 1,000-2,000 RPS, <200ms p99 latency
    Traffic Mix: 40% ingestion, 40% list, 20% detail
    """

    config = SERVICE_CONFIGS["transaction-management"]
    host = TRANSACTION_MGMT_URL

    def on_start(self):
        self.metrics = metrics_collector

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    tasks = []  # Loaded dynamically based on config


class RuleManagementUser(FastHttpUser):
    """
    Load test user for Rule Management API.

    Priority: LOW - Governance API, infrequent writes
    Target: 100-200 RPS, <500ms p99 latency
    Traffic Mix: 50% list, 30% get, 10% create, 10% update
    """

    config = SERVICE_CONFIGS["rule-management"]
    host = RULE_MGMT_URL
    wait_time = between(1.0, 2.0)

    def on_start(self):
        self.metrics = metrics_collector

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    tasks = []  # Loaded dynamically based on config


class OpsAnalystUser(FastHttpUser):
    """
    Load test user for Ops Analyst Agent.

    Priority: MEDIUM-LOW — advisory investigation engine
    Target: 500 RPS, P99 <= 2s (deterministic), P99 <= 5s (hybrid)
    Traffic Mix: 40% investigations, 40% worklist, 20% insights
    """

    config = SERVICE_CONFIGS["ops-analyst-agent"]
    host = OPS_ANALYST_URL
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.metrics = metrics_collector

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    tasks = []  # Loaded dynamically based on config


# =============================================================================
# Dynamic Task Loading
# =============================================================================


def load_tasks_for_service(service_name: str) -> dict:
    """Load task set for a service based on config."""
    config = SERVICE_CONFIGS[service_name]

    if service_name == "rule-engine":
        from tasksets.rule_engine import auth, monitoring

        tasks = {}

        if config.traffic_mix.preauth > 0:
            tasks[auth.AuthTaskset] = int(config.traffic_mix.preauth * 100)
        if config.traffic_mix.postauth > 0:
            tasks[monitoring.MonitoringTaskset] = int(config.traffic_mix.postauth * 100)

        return tasks

    elif service_name == "transaction-management":
        from tasksets.transaction_mgmt import ingestion

        tasks = {}

        if config.traffic_mix.ingestion > 0:
            tasks[ingestion.IngestionTaskset] = int(config.traffic_mix.ingestion * 100)
        if config.traffic_mix.list_query > 0:
            tasks[ingestion.ListQueryTaskset] = int(config.traffic_mix.list_query * 100)

        return tasks

    elif service_name == "rule-management":
        from tasksets.rule_management import rules

        tasks = {}

        if config.traffic_mix.list_rules > 0:
            tasks[rules.ListRulesTaskset] = int(config.traffic_mix.list_rules * 100)
        if config.traffic_mix.get_rule > 0:
            tasks[rules.GetRuleTaskset] = int(config.traffic_mix.get_rule * 100)

        return tasks

    elif service_name == "ops-analyst-agent":
        from tasksets.ops_analyst import investigations, worklist

        tasks = {}

        if config.traffic_mix.investigations > 0:
            tasks[investigations.InvestigationTaskset] = int(
                config.traffic_mix.investigations * 100
            )
        if config.traffic_mix.worklist > 0:
            tasks[worklist.WorklistTaskset] = int(config.traffic_mix.worklist * 100)

        return tasks

    return {}


# Load tasks based on environment variables or defaults
def auto_configure():
    """Auto-configure user classes based on what services are configured."""
    services_to_test = []

    if os.getenv("TEST_RULE_ENGINE", "true").lower() == "true":
        services_to_test.append("rule-engine")
        RuleEngineUser.tasks = load_tasks_for_service("rule-engine")

    if os.getenv("TEST_TRANSACTION_MGMT", "true").lower() == "true":
        services_to_test.append("transaction-management")
        TransactionManagementUser.tasks = load_tasks_for_service("transaction-management")

    if os.getenv("TEST_RULE_MGMT", "false").lower() == "true":
        services_to_test.append("rule-management")
        RuleManagementUser.tasks = load_tasks_for_service("rule-management")

    if os.getenv("TEST_OPS_ANALYST", "false").lower() == "true":
        services_to_test.append("ops-analyst-agent")
        OpsAnalystUser.tasks = load_tasks_for_service("ops-analyst-agent")

    print(f"Configured services for testing: {services_to_test}")


def get_enabled_user_classes():
    """Return the list of user classes enabled for this run."""
    enabled: list[type[FastHttpUser]] = []

    if os.getenv("TEST_RULE_ENGINE", "true").lower() == "true":
        enabled.append(RuleEngineUser)

    if os.getenv("TEST_TRANSACTION_MGMT", "true").lower() == "true":
        enabled.append(TransactionManagementUser)

    if os.getenv("TEST_RULE_MGMT", "false").lower() == "true":
        enabled.append(RuleManagementUser)

    if os.getenv("TEST_OPS_ANALYST", "false").lower() == "true":
        enabled.append(OpsAnalystUser)

    return enabled


auto_configure()


# =============================================================================
# Command-line Interface
# =============================================================================

if __name__ == "__main__":
    import argparse

    from locust.main import main as locust_main

    parser = argparse.ArgumentParser(description="Card Fraud Load Testing")

    # Service selection
    parser.add_argument(
        "--service",
        type=str,
        default="all",
        choices=["all", "rule-engine", "rule-mgmt", "trans-mgmt", "ops-analyst"],
        help="Service to load test",
    )

    # Load parameters
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--spawn-rate", type=int, default=10, help="Users spawned per second")
    parser.add_argument(
        "--run-time", type=str, default="5m", help="Duration of test (e.g., 5m, 1h)"
    )

    # Options
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no web UI)")
    parser.add_argument(
        "--scenario",
        type=str,
        default="normal",
        choices=["smoke", "baseline", "stress", "soak"],
        help="Test scenario",
    )
    parser.add_argument("--config", type=str, default="", help="Path to config file")

    args = parser.parse_args()

    # Build locust arguments
    locust_args = [
        "-f",
        "src/locustfile.py",
        "--users",
        str(args.users),
        "--spawn-rate",
        str(args.spawn_rate),
        "--run-time",
        args.run_time,
        "--html",
        "html-reports/locust/index.html",
        "--csv",
        "html-reports/locust/results",
    ]

    if args.headless:
        locust_args.append("--headless")

    # Select service(s) via environment variables consumed by auto_configure()
    os.environ["TEST_RULE_ENGINE"] = "true" if args.service in ["all", "rule-engine"] else "false"
    os.environ["TEST_TRANSACTION_MGMT"] = (
        "true" if args.service in ["all", "trans-mgmt"] else "false"
    )
    os.environ["TEST_RULE_MGMT"] = "true" if args.service in ["all", "rule-mgmt"] else "false"
    os.environ["TEST_OPS_ANALYST"] = (
        "true" if args.service in ["all", "ops-analyst"] else "false"
    )

    # Adjust config based on scenario
    if args.scenario == "smoke":
        locust_args.extend(["--users", str(min(args.users, 50)), "--run-time", "2m"])
    elif args.scenario == "stress":
        locust_args.extend(
            ["--users", str(args.users * 3), "--spawn-rate", str(args.spawn_rate * 2)]
        )
    elif args.scenario == "soak":
        locust_args.extend(["--run-time", "1h"])

    print(f"Starting load test: {args.service}")
    print(f"  Users: {args.users}")
    print(f"  Spawn rate: {args.spawn_rate}/s")
    print(f"  Duration: {args.run_time}")
    print(f"  Scenario: {args.scenario}")

    sys.argv = ["locust"] + locust_args
    locust_main()

