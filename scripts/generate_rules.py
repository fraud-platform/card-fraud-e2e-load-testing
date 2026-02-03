"""
CLI script to generate test rule data.

Usage:
    uv run gen-rules --count=100 --output=fixtures/rules.json
"""

import argparse
import json
import random
import uuid
from pathlib import Path


def generate_rule(seed: int = None, rule_type: str = "PREAUTH") -> dict:
    """Generate a single synthetic rule."""
    if seed:
        random.seed(seed)

    # Condition templates based on rule type
    if rule_type == "PREAUTH":
        conditions = [
            {
                "field": random.choice(["amount", "velocity", "country", "merchant_risk"]),
                "operator": random.choice([">", "<", "==", "in", "not in"]),
                "value": random.choice(
                    [
                        1000,
                        5000,
                        ["IN", "PK", "BD"],  # High-risk countries
                        ["7995", "6051"],  # High-risk MCCs
                    ]
                ),
            }
        ]
        actions = [
            {
                "type": random.choice(["decline", "review", "3ds", "allow"]),
                "reason": "Automated rule generated for load testing",
            }
        ]
    else:  # POSTAUTH
        conditions = [
            {
                "field": random.choice(["chargeback_ratio", "amount", "time_since_auth"]),
                "operator": random.choice([">", "<"]),
                "value": random.choice([0.02, 5000, 86400]),
            }
        ]
        actions = [
            {
                "type": random.choice(["flag", "review", "notify"]),
                "reason": "Post-auth analysis rule",
            }
        ]

    return {
        "rule_id": f"rule_{uuid.uuid4().hex[:12]}",
        "name": f"Load Test Rule {random.randint(1000, 9999)}",
        "description": f"Generated {rule_type} rule for load testing",
        "rule_type": rule_type,
        "priority": random.randint(1, 100),
        "status": random.choice(["draft", "active", "archived"]),
        "conditions": conditions,
        "actions": actions,
        "created_at": "2026-01-01T00:00:00Z",
        "version": "1.0.0",
    }


def generate_rules(count: int, seed: int = None, rule_type: str = None) -> list[dict]:
    """Generate a batch of synthetic rules."""
    if seed:
        random.seed(seed)

    rules = []
    for i in range(count):
        rt = rule_type if rule_type else random.choice(["PREAUTH", "POSTAUTH"])
        rule = generate_rule(seed=seed + i if seed else None, rule_type=rt)
        rules.append(rule)

    return rules


def main():
    parser = argparse.ArgumentParser(description="Generate test rule data")
    parser.add_argument("--count", type=int, default=100, help="Number of rules to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--rule-type",
        type=str,
        choices=["PREAUTH", "POSTAUTH"],
        default=None,
        help="Rule type (default: random mix)",
    )
    parser.add_argument(
        "--output", type=str, default="fixtures/rules.json", help="Output file path"
    )

    args = parser.parse_args()

    print(f"Generating {args.count} rules...")
    rules = generate_rules(args.count, seed=args.seed, rule_type=args.rule_type)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    with open(output_path, "w") as f:
        json.dump(rules, f, indent=2)

    print(f"Generated {len(rules)} rules -> {output_path}")

    # Print type summary
    type_counts = {}
    for rule in rules:
        rt = rule["rule_type"]
        type_counts[rt] = type_counts.get(rt, 0) + 1

    print("\nRule type summary:")
    for rt, count in sorted(type_counts.items()):
        pct = count / len(rules) * 100
        print(f"  {rt}: {count} ({pct:.1f}%)")

    # Print sample
    print("\nSample rule:")
    print(json.dumps(rules[0], indent=2))


if __name__ == "__main__":
    main()
