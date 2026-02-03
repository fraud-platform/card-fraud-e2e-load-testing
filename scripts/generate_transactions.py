"""
CLI script to generate test transaction data.

Usage:
    uv run gen-transactions --count=10000 --output=fixtures/transactions.json
"""

import argparse
import json
import random
import uuid
from datetime import UTC, datetime
from pathlib import Path

try:
    from faker import Faker

    fake = Faker()
except ImportError:
    fake = None


def generate_transaction(seed: int = None, country: str = None, risk_level: str = "normal") -> dict:
    """Generate a single synthetic transaction."""
    if seed:
        random.seed(seed)

    # Amount distribution based on risk level
    amount_ranges = {
        "normal": (100, 5000),
        "high": (5000, 50000),
        "suspicious": (50000, 500000),
    }

    amount = round(random.uniform(*amount_ranges[risk_level]), 2)

    # Country and currency correlation
    country_currency = {
        "IN": "INR",
        "US": "USD",
        "SG": "SGD",
        "GB": "GBP",
        "AU": "AUD",
    }

    if not country:
        country = random.choice(list(country_currency.keys()))
    currency = country_currency.get(country, "USD")

    # Card masking
    card_bin = random.choice(["4111", "5411", "3700", "4000"])
    card_last4 = str(random.randint(1000, 9999))
    card_id = f"{card_bin}{'*' * 8}{card_last4}"

    return {
        "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
        "occurred_at": datetime.now(UTC).isoformat(),
        "card_id": card_id,
        "card_last4": card_last4,
        "card_network": random.choice(["VISA", "MASTERCARD", "AMEX"]),
        "merchant_id": f"M{random.randint(10000, 99999)}",
        "mcc": random.choice(["5411", "5812", "4111", "7995", "5311", "5412", "5541"]),
        "ip": fake.ipv4() if fake else f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "amount": amount,
        "currency": currency,
        "country": country,
        "risk_level": risk_level,
    }


def generate_transactions(
    count: int, seed: int = None, distribution: dict[str, float] = None
) -> list[dict]:
    """Generate transactions with specified risk distribution."""
    if distribution is None:
        distribution = {"normal": 0.8, "high": 0.15, "suspicious": 0.05}

    if seed:
        random.seed(seed)

    transactions = []
    for i in range(count):
        # Determine risk level based on distribution
        rand = random.random()
        cumulative = 0
        risk_level = "normal"
        for level, prob in distribution.items():
            cumulative += prob
            if rand <= cumulative:
                risk_level = level
                break

        txn = generate_transaction(seed=seed + i if seed else None, risk_level=risk_level)
        transactions.append(txn)

    return transactions


def main():
    parser = argparse.ArgumentParser(description="Generate test transaction data")
    parser.add_argument(
        "--count", type=int, default=10000, help="Number of transactions to generate"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--output", type=str, default="fixtures/transactions.json", help="Output file path"
    )
    parser.add_argument(
        "--distribution",
        type=str,
        default="normal:0.8,high:0.15,suspicious:0.05",
        help="Risk level distribution (format: level:prob,level:prob)",
    )

    args = parser.parse_args()

    # Parse distribution
    distribution = {}
    for part in args.distribution.split(","):
        level, prob = part.split(":")
        distribution[level] = float(prob)

    print(f"Generating {args.count} transactions...")
    print(f"Distribution: {distribution}")

    transactions = generate_transactions(args.count, seed=args.seed, distribution=distribution)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    with open(output_path, "w") as f:
        json.dump(transactions, f, indent=2)

    print(f"Generated {len(transactions)} transactions -> {output_path}")

    # Print distribution summary
    risk_counts = {}
    for txn in transactions:
        level = txn["risk_level"]
        risk_counts[level] = risk_counts.get(level, 0) + 1

    print("\nDistribution summary:")
    for level, count in sorted(risk_counts.items()):
        pct = count / len(transactions) * 100
        print(f"  {level}: {count} ({pct:.1f}%)")

    # Print sample
    print("\nSample transaction:")
    print(json.dumps(transactions[0], indent=2))


if __name__ == "__main__":
    main()
