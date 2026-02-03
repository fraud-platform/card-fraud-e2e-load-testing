"""
CLI script to generate test ruleset data.

Usage:
    uv run gen-rulesets --count=10 --rules-per-set=20 --output=fixtures/rulesets.json
"""

import argparse
import json
import random
import uuid
from pathlib import Path


def generate_ruleset(
    seed: int = None, ruleset_size: int = 20, available_rules: list[str] = None
) -> dict:
    """Generate a single synthetic ruleset."""
    if seed:
        random.seed(seed)

    if available_rules:
        # Sample from available rules
        selected_rules = random.sample(available_rules, min(ruleset_size, len(available_rules)))
    else:
        # Generate synthetic rule IDs
        selected_rules = [f"rule_{uuid.uuid4().hex[:12]}" for _ in range(ruleset_size)]

    return {
        "ruleset_id": f"rs_{uuid.uuid4().hex[:12]}",
        "name": f"Load Test Ruleset {random.randint(1000, 9999)}",
        "description": "Generated ruleset for load testing",
        "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
        "rules": selected_rules,
        "status": random.choice(["draft", "published", "archived"]),
        "created_at": "2026-01-01T00:00:00Z",
        "activation_date": "2026-01-01T00:00:00Z" if random.random() > 0.3 else None,
        "metadata": {
            "owner": "load-test",
            "tags": ["generated", "test"],
        },
    }


def generate_rulesets(
    count: int, seed: int = None, ruleset_size: int = 20, available_rules: list[str] = None
) -> list[dict]:
    """Generate a batch of synthetic rulesets."""
    if seed:
        random.seed(seed)

    return [
        generate_ruleset(
            seed=seed + i if seed else None,
            ruleset_size=ruleset_size,
            available_rules=available_rules,
        )
        for i in range(count)
    ]


def load_rules_from_file(rules_file: str) -> list[str]:
    """Load rule IDs from a rules file."""
    with open(rules_file) as f:
        rules = json.load(f)
    return [r["rule_id"] for r in rules]


def main():
    parser = argparse.ArgumentParser(description="Generate test ruleset data")
    parser.add_argument("--count", type=int, default=10, help="Number of rulesets to generate")
    parser.add_argument("--rules-per-set", type=int, default=20, help="Number of rules per ruleset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--rules-file", type=str, default=None, help="Path to rules.json to sample from (optional)"
    )
    parser.add_argument(
        "--output", type=str, default="fixtures/rulesets.json", help="Output file path"
    )

    args = parser.parse_args()

    # Load available rules if provided
    available_rules = None
    if args.rules_file:
        print(f"Loading rules from {args.rules_file}...")
        available_rules = load_rules_from_file(args.rules_file)
        print(f"Loaded {len(available_rules)} rules")

    print(f"Generating {args.count} rulesets with {args.rules_per_set} rules each...")
    rulesets = generate_rulesets(
        args.count, seed=args.seed, ruleset_size=args.rules_per_set, available_rules=available_rules
    )

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    with open(output_path, "w") as f:
        json.dump(rulesets, f, indent=2)

    print(f"Generated {len(rulesets)} rulesets -> {output_path}")

    # Print status summary
    status_counts = {}
    for rs in rulesets:
        status = rs["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\nStatus summary:")
    for status, count in sorted(status_counts.items()):
        pct = count / len(rulesets) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")

    # Print sample
    print("\nSample ruleset:")
    print(json.dumps(rulesets[0], indent=2))


if __name__ == "__main__":
    main()
