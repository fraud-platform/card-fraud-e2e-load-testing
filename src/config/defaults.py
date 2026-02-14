"""
Default configurations for load testing.
Loads settings from environment with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TrafficMix:
    """Traffic mix configuration."""

    preauth: float = 1.0  # 100% AUTH for AUTH-only load test
    postauth: float = 0.0  # 0% MONITORING for AUTH-only load test


@dataclass
class RuleEngineConfig:
    """Configuration for Rule Engine load testing."""

    # Target metrics
    target_rps: int = 10000
    p50_latency_threshold_ms: float = 5.0
    p95_latency_threshold_ms: float = 15.0
    p99_latency_threshold_ms: float = 30.0
    error_rate_threshold: float = 0.01  # 1%

    # User scaling
    users_light: int = 500
    users_normal: int = 1000
    users_heavy: int = 3000
    users_stress: int = 5000

    # Spawn rates
    spawn_rate_normal: int = 100
    spawn_rate_fast: int = 500

    # Test durations
    duration_smoke: str = "2m"
    duration_normal: str = "10m"
    duration_stress: str = "30m"
    duration_soak: str = "1h"

    # Traffic mix
    traffic_mix: TrafficMix | None = None

    def __post_init__(self):
        if self.traffic_mix is None:
            self.traffic_mix = TrafficMix()

    @classmethod
    def from_env(cls) -> RuleEngineConfig:
        """Load from environment variables."""
        preauth = float(
            os.getenv("RULE_ENGINE_PREAUTH_WEIGHT", os.getenv("RULE_ENGINE_AUTH_WEIGHT", "1.0"))
        )
        postauth = float(
            os.getenv(
                "RULE_ENGINE_POSTAUTH_WEIGHT",
                os.getenv("RULE_ENGINE_MONITORING_WEIGHT", "0.0"),
            )
        )

        # Keep mix deterministic and valid for Locust task weighting.
        if preauth < 0:
            preauth = 0.0
        if postauth < 0:
            postauth = 0.0
        total = preauth + postauth
        if total <= 0:
            preauth = 1.0
            postauth = 0.0
        else:
            preauth = preauth / total
            postauth = postauth / total

        return cls(
            target_rps=int(os.getenv("RULE_ENGINE_RPS", str(cls().target_rps))),
            p50_latency_threshold_ms=float(
                os.getenv("RULE_ENGINE_P50_MS", str(cls().p50_latency_threshold_ms))
            ),
            p95_latency_threshold_ms=float(
                os.getenv("RULE_ENGINE_P95_MS", str(cls().p95_latency_threshold_ms))
            ),
            p99_latency_threshold_ms=float(
                os.getenv("RULE_ENGINE_P99_MS", str(cls().p99_latency_threshold_ms))
            ),
            users_normal=int(os.getenv("RULE_ENGINE_USERS", str(cls().users_normal))),
            traffic_mix=TrafficMix(preauth=preauth, postauth=postauth),
        )


@dataclass
class TransactionMgmtTrafficMix:
    """Traffic mix for Transaction Management."""

    ingestion: float = 0.40
    list_query: float = 0.40
    detail_query: float = 0.20


@dataclass
class TransactionManagementConfig:
    """Configuration for Transaction Management load testing."""

    target_rps: int = 2000
    p99_latency_threshold_ms: float = 200.0
    error_rate_threshold: float = 0.01

    users_light: int = 100
    users_normal: int = 200
    users_heavy: int = 500

    traffic_mix: TransactionMgmtTrafficMix | None = None

    def __post_init__(self):
        if self.traffic_mix is None:
            self.traffic_mix = TransactionMgmtTrafficMix()

    @classmethod
    def from_env(cls) -> TransactionManagementConfig:
        return cls(
            target_rps=int(os.getenv("TRANS_MGMT_RPS", str(cls().target_rps))),
        )


@dataclass
class RuleMgmtTrafficMix:
    """Traffic mix for Rule Management."""

    list_rules: float = 0.50
    get_rule: float = 0.30
    create_rule: float = 0.10
    update_rule: float = 0.10


@dataclass
class RuleManagementConfig:
    """Configuration for Rule Management load testing."""

    # LOW priority - governance API
    target_rps: int = 200
    p99_latency_threshold_ms: float = 500.0
    error_rate_threshold: float = 0.01

    users_light: int = 20
    users_normal: int = 50
    users_heavy: int = 100

    traffic_mix: RuleMgmtTrafficMix | None = None

    def __post_init__(self):
        if self.traffic_mix is None:
            self.traffic_mix = RuleMgmtTrafficMix()

    @classmethod
    def from_env(cls) -> RuleManagementConfig:
        return cls()


@dataclass
class OpsAnalystTrafficMix:
    """Traffic mix for Ops Analyst Agent."""

    investigations: float = 0.40
    worklist: float = 0.40
    insights: float = 0.20


@dataclass
class OpsAnalystConfig:
    """Configuration for Ops Analyst Agent load testing.

    Advisory investigation engine — moderate RPS, higher latency tolerance.
    """

    # MEDIUM-LOW priority — advisory engine
    target_rps: int = 500
    p99_latency_threshold_ms: float = 2000.0
    error_rate_threshold: float = 0.01

    users_light: int = 10
    users_normal: int = 25
    users_heavy: int = 50

    traffic_mix: OpsAnalystTrafficMix | None = None

    def __post_init__(self):
        if self.traffic_mix is None:
            self.traffic_mix = OpsAnalystTrafficMix()

    @classmethod
    def from_env(cls) -> OpsAnalystConfig:
        return cls(
            target_rps=int(os.getenv("OPS_ANALYST_RPS", str(cls().target_rps))),
        )


# Service registry
SERVICE_CONFIGS = {
    "rule-engine": None,  # Loaded lazily
    "rule-management": None,
    "transaction-management": None,
    "ops-analyst-agent": None,
}


def load_config() -> dict:
    """Load all configurations from environment."""
    return {
        "rule-engine": get_service_config("rule-engine"),
        "rule-management": get_service_config("rule-management"),
        "transaction-management": get_service_config("transaction-management"),
        "ops-analyst-agent": get_service_config("ops-analyst-agent"),
    }


def get_service_config(service_name: str):
    """Get config for a specific service."""
    config_map = {
        "rule-engine": RuleEngineConfig,
        "rule-management": RuleManagementConfig,
        "transaction-management": TransactionManagementConfig,
        "ops-analyst-agent": OpsAnalystConfig,
    }

    if service_name not in config_map:
        raise ValueError(f"Unknown service: {service_name}")

    # Return cached config or create new one
    if SERVICE_CONFIGS[service_name] is None:
        SERVICE_CONFIGS[service_name] = config_map[service_name].from_env()

    return SERVICE_CONFIGS[service_name]


# Scenario configurations
SCENARIOS = {
    "smoke": {
        "users": 50,
        "spawn_rate": 10,
        "duration": "2m",
        "description": "Quick validation that services are operational",
    },
    "baseline": {
        "users": 1000,
        "spawn_rate": 100,
        "duration": "10m",
        "description": "Establish baseline performance metrics",
    },
    "stress": {
        "users": 5000,
        "spawn_rate": 500,
        "duration": "30m",
        "description": "Find breaking point and measure degradation",
    },
    "soak": {
        "users": 1000,
        "spawn_rate": 50,
        "duration": "1h",
        "description": "Detect memory leaks and resource exhaustion",
    },
    "spike": {
        "users": 5000,
        "spawn_rate": 1000,
        "duration": "5m",
        "description": "Sudden traffic spike to test burst handling",
    },
    "seed-only": {
        "users": 1,
        "spawn_rate": 1,
        "duration": "1m",
        "description": "Seed artifacts and validate visibility without sustained load",
    },
}


def get_scenario_config(scenario_name: str) -> dict:
    """Get configuration for a test scenario."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    return SCENARIOS[scenario_name]


