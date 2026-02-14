"""
Seed and teardown harness for load testing.

Manages the lifecycle of a load test run:
1. Generate run_id
2. Seed test data and artifacts
3. Run load test
4. Teardown and cleanup

Usage:
    from utilities.harness import LoadTestHarness

    harness = LoadTestHarness()
    harness.seed()
    harness.run()
    harness.teardown()
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

try:
    # Package-style imports (used by console script entry points).
    from src.utilities.minio_client import (
        cleanup_run_artifacts,
        get_run_artifacts,
        publish_ruleset,
    )
except ModuleNotFoundError:
    # Backward-compatible imports when running with src on PYTHONPATH.
    from utilities.minio_client import (
        cleanup_run_artifacts,
        get_run_artifacts,
        publish_ruleset,
    )

HEALTH_PATH_BY_SERVICE = {
    "rule-engine": "/v1/evaluate/health",
    "rule-mgmt": "/api/v1/health",
    "trans-mgmt": "/api/v1/health",
}


class LoadTestHarness:
    """
    Manages the complete load test lifecycle with idempotency.

    Every run gets a unique run_id. All resources are tagged with this ID
    for easy cleanup and tracking.
    """

    def __init__(
        self,
        run_id: str | None = None,
        bucket: str = "fraud-gov-artifacts",
        enable_seed: bool = True,
        enable_teardown: bool = True,
    ):
        """
        Initialize the harness.

        Args:
            run_id: Optional run ID (generated if not provided)
            bucket: MinIO/S3 bucket for artifacts
            enable_seed: Whether to run seed phase
            enable_teardown: Whether to run teardown phase
        """
        self.run_id = run_id or f"lt-{uuid.uuid4().hex[:12]}"
        self.bucket = bucket
        self.enable_seed = enable_seed
        self.enable_teardown = enable_teardown

        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.seeded_artifacts: list = []

    def seed(self, rulesets: list | None = None, rules: list | None = None) -> bool:
        """
        Seed phase: publish artifacts and validate setup.

        Args:
            rulesets: List of ruleset dicts to publish
            rules: List of rule dicts to publish

        Returns:
            True if seeding successful
        """
        if not self.enable_seed:
            print("Seed phase disabled")
            return True

        print(f"\n{'=' * 60}")
        print(f"SEED PHASE - Run ID: {self.run_id}")
        print(f"{'=' * 60}\n")

        self.start_time = datetime.now()

        # Publish rulesets
        if rulesets:
            print(f"\nPublishing {len(rulesets)} rulesets...")
            for ruleset in rulesets:
                key = publish_ruleset(ruleset, self.bucket, self.run_id)
                if key:
                    self.seeded_artifacts.append(key)
                    print(f"  Published: {key}")
                else:
                    print(f"  FAILED to publish ruleset: {ruleset.get('ruleset_id', 'unknown')}")

        # TODO: Publish rules if needed
        if rules:
            print(f"\nPublishing {len(rules)} rules...")
            # Rules would be published to rule-management API
            # For now, just log
            print("  (Rule publishing via API not yet implemented)")

        # Validate artifacts are visible
        print("\nValidating artifact visibility...")
        artifacts = get_run_artifacts(self.bucket, self.run_id, "rulesets")
        if artifacts:
            print(f"  Found {len(artifacts)} artifacts in bucket")
            for artifact in artifacts[:5]:  # Show first 5
                print(f"    - {artifact}")
        else:
            print("  WARNING: No artifacts found in bucket")

        print(f"\nSeed phase complete. Artifacts tagged with run_id: {self.run_id}")
        return True

    def health_check(self, service_urls: dict) -> dict:
        """
        Check health of all required services.

        Args:
            service_urls: Dict of service names to URLs

        Returns:
            Dict with health status per service
        """
        import httpx

        results = {}

        print("\nHealth checking services...")
        for name, url in service_urls.items():
            health_path = HEALTH_PATH_BY_SERVICE.get(name, "/health")
            health_url = f"{url.rstrip('/')}{health_path}"
            try:
                response = httpx.get(health_url, timeout=5.0)
                healthy = response.status_code == 200
                results[name] = {
                    "healthy": healthy,
                    "status_code": response.status_code,
                }
                status = "[OK]" if healthy else "[FAIL]"
                print(f"  {status} {name}: {health_url}")
            except Exception as exc:
                results[name] = {"healthy": False, "error": str(exc)}
                print(f"  [FAIL] {name}: {health_url} - {exc}")

        return results

    def teardown(self, force: bool = False) -> bool:
        """
        Teardown phase: cleanup artifacts and resources.

        Args:
            force: Cleanup even if enable_teardown is False

        Returns:
            True if teardown successful
        """
        if not self.enable_teardown and not force:
            print("Teardown phase disabled")
            return True

        print(f"\n{'=' * 60}")
        print(f"TEARDOWN PHASE - Run ID: {self.run_id}")
        print(f"{'=' * 60}\n")

        self.end_time = datetime.now()

        # Cleanup MinIO artifacts
        deleted = cleanup_run_artifacts(self.bucket, self.run_id)
        print(f"\nDeleted {deleted} artifacts from bucket")

        # TODO: Cleanup other resources (transactions, etc.)
        # This would involve calling the respective APIs

        # Generate cleanup report
        duration = None
        if self.start_time:
            duration = self.end_time - self.start_time

        print(f"\nRun duration: {duration}")
        print(f"Teardown complete for run_id: {self.run_id}")

        return True

    def write_run_metadata(
        self,
        output_dir: str = "html-reports",
        metadata: dict | None = None,
    ) -> Path:
        """
        Write run metadata to file for tracking.

        Args:
            output_dir: Directory for metadata file

        Returns:
            Path to metadata file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        base_metadata = {
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "bucket": self.bucket,
            "seeded_artifacts": self.seeded_artifacts,
            "seed_enabled": self.enable_seed,
            "teardown_enabled": self.enable_teardown,
        }
        if metadata:
            base_metadata.update(metadata)

        metadata_file = output_path / f"run-metadata-{self.run_id}.json"
        with open(metadata_file, "w") as f:
            json.dump(base_metadata, f, indent=2)

        return metadata_file


def create_run_id() -> str:
    """Generate a unique run ID."""
    return f"lt-{uuid.uuid4().hex[:12]}"


def get_env_run_id() -> str | None:
    """Get run_id from environment variable."""
    return os.getenv("LOADTEST_RUN_ID")
