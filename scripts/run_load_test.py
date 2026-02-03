"""
Main load test runner script.

Usage:
    uv run lt-web  # Start Locust web UI
    uv run lt-rule-engine --users=1000 --auth-mode none
    uv run lt-run --service all --users=1000 --run-time=10m --headless
"""

import argparse
import os
import sys

import httpx
from locust.main import main as locust_main

from src.generators import RuleGenerator
from src.utilities.harness import LoadTestHarness

LOCUSTFILE = "src/locustfile.py"

SERVICE_URL_ENV = {
    "rule-engine": ("RULE_ENGINE_URL", "http://localhost:8081"),
    "rule-mgmt": ("RULE_MGMT_URL", "http://localhost:8000"),
    "trans-mgmt": ("TRANSACTION_MGMT_URL", "http://localhost:8002"),
}

SERVICE_HEALTH_PATH = {
    "rule-engine": "/v1/evaluate/health",
    "rule-mgmt": "/api/v1/health",
    "trans-mgmt": "/api/v1/health",
}


def _services_for_selection(selection: str) -> list[str]:
    if selection == "all":
        return ["rule-engine", "rule-mgmt", "trans-mgmt"]
    return [selection]


def _preflight_services(selection: str) -> bool:
    """Validate target service endpoints before starting Locust."""
    services = _services_for_selection(selection)

    print("\nPreflight health checks:")
    for service in services:
        env_name, default_url = SERVICE_URL_ENV[service]
        base_url = os.getenv(env_name, default_url).rstrip("/")
        health_path = SERVICE_HEALTH_PATH[service]
        health_url = f"{base_url}{health_path}"
        try:
            response = httpx.get(health_url, timeout=10.0)
        except Exception as exc:
            print(f"  [FAIL] {service}: {health_url} ({exc})")
            return False
        if response.status_code != 200:
            print(f"  [FAIL] {service}: {health_url} (status {response.status_code})")
            return False
        print(f"  [OK] {service}: {health_url}")

    return True


def parse_args():
    parser = argparse.ArgumentParser(description="Card Fraud Load Testing")

    parser.add_argument(
        "--service",
        type=str,
        default="all",
        choices=["all", "rule-engine", "rule-mgmt", "trans-mgmt"],
        help="Service to load test",
    )

    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--spawn-rate", type=int, default=10, help="Users spawned per second")
    parser.add_argument("--run-time", type=str, default="5m", help="Duration of test")

    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument(
        "--scenario",
        type=str,
        default="baseline",
        choices=["smoke", "baseline", "stress", "soak", "spike", "seed-only"],
        help="Test scenario",
    )
    parser.add_argument(
        "--auth-mode",
        type=str,
        default="none",
        choices=["none", "auth0", "local"],
        help="Authentication mode for requests",
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip seed phase",
    )
    parser.add_argument(
        "--skip-teardown",
        action="store_true",
        help="Skip teardown phase",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom run ID (auto-generated if not provided)",
    )

    return parser.parse_args()


def run_rule_engine(
    users: int,
    spawn_rate: int,
    run_time: str,
    headless: bool,
    auth_mode: str = "none",
    harness: LoadTestHarness | None = None,
):
    """Run Rule Engine load test."""
    print(
        f"Starting Rule Engine load test: users={users}, "
        f"spawn={spawn_rate}/s, duration={run_time}, auth={auth_mode}"
    )

    # Set auth mode environment variable for Locust tasks to read
    os.environ["AUTH_MODE"] = auth_mode
    os.environ["TEST_RULE_ENGINE"] = "true"
    os.environ["TEST_TRANSACTION_MGMT"] = "false"
    os.environ["TEST_RULE_MGMT"] = "false"
    if harness:
        os.environ["LOADTEST_RUN_ID"] = harness.run_id

    args = [
        "-f",
        LOCUSTFILE,
        "--users",
        str(users),
        "--spawn-rate",
        str(spawn_rate),
        "--run-time",
        run_time,
        "--html",
        "html-reports/locust/rule-engine.html",
        "--csv",
        "html-reports/locust/rule-engine",
    ]

    if headless:
        args.append("--headless")

    # Run with harness integration
    if harness and harness.enable_seed:
        print("\nRunning with harness seed/teardown...")
        # Note: Actual seeding happens in main() before this call

    sys.argv = ["locust"] + args
    locust_main()


def run_rule_management(
    users: int,
    spawn_rate: int,
    run_time: str,
    headless: bool,
    auth_mode: str = "none",
    harness: LoadTestHarness | None = None,
):
    """Run Rule Management load test."""
    print(
        f"Starting Rule Mgmt load test: users={users}, "
        f"spawn={spawn_rate}/s, duration={run_time}, auth={auth_mode}"
    )

    os.environ["AUTH_MODE"] = auth_mode
    os.environ["TEST_RULE_ENGINE"] = "false"
    os.environ["TEST_TRANSACTION_MGMT"] = "false"
    os.environ["TEST_RULE_MGMT"] = "true"
    if harness:
        os.environ["LOADTEST_RUN_ID"] = harness.run_id

    args = [
        "-f",
        LOCUSTFILE,
        "--users",
        str(users),
        "--spawn-rate",
        str(spawn_rate),
        "--run-time",
        run_time,
        "--html",
        "html-reports/locust/rule-mgmt.html",
        "--csv",
        "html-reports/locust/rule-mgmt",
    ]

    if headless:
        args.append("--headless")

    sys.argv = ["locust"] + args
    locust_main()


def run_transaction_management(
    users: int,
    spawn_rate: int,
    run_time: str,
    headless: bool,
    auth_mode: str = "none",
    harness: LoadTestHarness | None = None,
):
    """Run Transaction Management load test."""
    print(
        f"Starting Transaction Mgmt: users={users}, "
        f"spawn={spawn_rate}/s, duration={run_time}, auth={auth_mode}"
    )

    os.environ["AUTH_MODE"] = auth_mode
    os.environ["TEST_RULE_ENGINE"] = "false"
    os.environ["TEST_TRANSACTION_MGMT"] = "true"
    os.environ["TEST_RULE_MGMT"] = "false"
    if harness:
        os.environ["LOADTEST_RUN_ID"] = harness.run_id

    args = [
        "-f",
        LOCUSTFILE,
        "--users",
        str(users),
        "--spawn-rate",
        str(spawn_rate),
        "--run-time",
        run_time,
        "--html",
        "html-reports/locust/trans-mgmt.html",
        "--csv",
        "html-reports/locust/trans-mgmt",
    ]

    if headless:
        args.append("--headless")

    sys.argv = ["locust"] + args
    locust_main()


def get_scenario_params(
    scenario: str, base_users: int, base_spawn_rate: int, base_run_time: str
) -> tuple[int, int, str]:
    """Get parameters adjusted for scenario."""
    scenario_config = {
        "smoke": {"users": 50, "spawn_rate": 10, "duration": "2m"},
        "baseline": {"users": base_users, "spawn_rate": base_spawn_rate, "duration": base_run_time},
        "stress": {"users": base_users * 3, "spawn_rate": base_spawn_rate * 3, "duration": "30m"},
        "soak": {"users": base_users, "spawn_rate": base_spawn_rate // 2, "duration": "1h"},
        "spike": {"users": base_users * 5, "spawn_rate": base_spawn_rate * 10, "duration": "5m"},
        "seed-only": {"users": 1, "spawn_rate": 1, "duration": "1m"},  # Minimal load, just seed
    }

    config = scenario_config.get(scenario, scenario_config["baseline"])
    return config["users"], config["spawn_rate"], config["duration"]


def main():
    """Main entry point."""
    args = parse_args()

    # Get scenario-adjusted parameters
    users, spawn_rate, run_time = get_scenario_params(
        args.scenario, args.users, args.spawn_rate, args.run_time
    )

    # Initialize harness for seed/test/teardown workflow
    harness = LoadTestHarness(
        run_id=args.run_id,
        enable_seed=not args.skip_seed,
        enable_teardown=not args.skip_teardown,
    )

    print(f"\n{'=' * 70}")
    print(f"LOAD TEST RUN - ID: {harness.run_id}")
    print(f"Service: {args.service}")
    print(f"Scenario: {args.scenario}")
    print(f"Auth Mode: {args.auth_mode}")
    print(f"Users: {users}, Spawn Rate: {spawn_rate}/s, Duration: {run_time}")
    print(f"Seed: {harness.enable_seed}, Teardown: {harness.enable_teardown}")
    print(f"{'=' * 70}\n")

    if not _preflight_services(args.service):
        print("\nERROR: One or more target services are unavailable.")
        print("Start shared containers first: doppler run -- uv run platform-up -- --apps")
        sys.exit(1)

    try:
        # SEED PHASE
        if harness.enable_seed:
            # For rule-mgmt service, seed rulesets
            if args.service in ["rule-mgmt", "all"]:
                rule_gen = RuleGenerator(seed=42)
                rulesets = [
                    rule_gen.generate_ruleset(ruleset_type="PREAUTH"),
                    rule_gen.generate_ruleset(ruleset_type="POSTAUTH"),
                ]
                if not harness.seed(rulesets=rulesets):
                    print("ERROR: Seed phase failed")
                    sys.exit(1)
            else:
                # Minimal seed for other services
                harness.seed()

        # TEST PHASE
        if args.scenario == "seed-only":
            print("\nSeed-only scenario complete. No load test executed.")
        elif args.service == "all":
            # Run all user classes in a single Locust run (no -T filter).
            # locustfile.py controls which services are active via TEST_* env vars.
            os.environ["AUTH_MODE"] = args.auth_mode
            os.environ["TEST_RULE_ENGINE"] = "true"
            os.environ["TEST_TRANSACTION_MGMT"] = "true"
            os.environ["TEST_RULE_MGMT"] = "true"
            os.environ["LOADTEST_RUN_ID"] = harness.run_id

            args_list = [
                "--users",
                str(users),
                "--spawn-rate",
                str(spawn_rate),
                "--run-time",
                run_time,
                "-f",
                LOCUSTFILE,
                "--html",
                "html-reports/locust/all-services.html",
                "--csv",
                "html-reports/locust/all-services",
            ]
            if args.headless:
                args_list.append("--headless")

            sys.argv = ["locust"] + args_list
            locust_main()
        elif args.service == "rule-engine":
            run_rule_engine(users, spawn_rate, run_time, args.headless, args.auth_mode, harness)
        elif args.service == "rule-mgmt":
            run_rule_management(users, spawn_rate, run_time, args.headless, args.auth_mode, harness)
        elif args.service == "trans-mgmt":
            run_transaction_management(
                users, spawn_rate, run_time, args.headless, args.auth_mode, harness
            )

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    finally:
        # TEARDOWN PHASE
        if harness.enable_teardown:
            harness.teardown()
            harness.write_run_metadata()


def web_ui():
    """Start Locust web UI for interactive testing."""
    print("Starting Locust Web UI...")
    print("Open http://localhost:8089 after Locust starts")
    print("\nUse Doppler for environment variables:")
    print("  doppler run -- uv run lt-web\n")

    # Start Locust in web mode
    sys.argv = [
        "locust",
        "-f",
        "src/locustfile.py",
    ]
    locust_main()


def _inject_service_arg(service: str):
    """Inject or replace --service argument for console-script wrappers."""
    argv = sys.argv[1:]
    if "--service" in argv:
        idx = argv.index("--service")
        # Replace value if present; otherwise append
        if idx + 1 < len(argv):
            argv[idx + 1] = service
        else:
            argv.append(service)
    else:
        argv = ["--service", service] + argv
    sys.argv = [sys.argv[0]] + argv


def cli_rule_engine():
    """Console entrypoint: run Rule Engine only."""
    _inject_service_arg("rule-engine")
    main()


def cli_rule_management():
    """Console entrypoint: run Rule Management only."""
    _inject_service_arg("rule-mgmt")
    main()


def cli_transaction_management():
    """Console entrypoint: run Transaction Management only."""
    _inject_service_arg("trans-mgmt")
    main()


if __name__ == "__main__":
    main()
