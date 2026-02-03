"""
CLI script to generate test user data.

Usage:
    uv run gen-users --count=1000 --output=fixtures/users.json
"""

import argparse
import json
import random
import uuid
from pathlib import Path

try:
    from faker import Faker
except ImportError:
    Faker = None


def generate_user(seed: int = None, country: str = None) -> dict:
    """Generate a single synthetic user."""
    if Faker:
        fake = Faker()
        if seed:
            Faker.seed(seed)

        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()
    else:
        first_name = f"User{random.randint(1000, 9999)}"
        last_name = f"Test{random.randint(1000, 9999)}"
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"

    if not country:
        country = random.choice(["IN", "US", "SG", "GB", "AU"])

    return {
        "user_id": f"user_{uuid.uuid4().hex[:16]}",
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "country": country,
        "created_at": "2026-01-01T00:00:00Z",
        "kyc_status": random.choice(["verified", "pending", "unverified"]),
        "risk_score": random.randint(0, 100),
    }


def generate_users(count: int, seed: int = None, country: str = None) -> list[dict]:
    """Generate a batch of synthetic users."""
    if seed:
        random.seed(seed)

    return [generate_user(seed=seed + i if seed else None, country=country) for i in range(count)]


def main():
    parser = argparse.ArgumentParser(description="Generate test user data")
    parser.add_argument("--count", type=int, default=1000, help="Number of users to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--country", type=str, default=None, help="Filter by country (IN, US, SG)")
    parser.add_argument(
        "--output", type=str, default="fixtures/users.json", help="Output file path"
    )

    args = parser.parse_args()

    print(f"Generating {args.count} users...")
    users = generate_users(args.count, seed=args.seed, country=args.country)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    with open(output_path, "w") as f:
        json.dump(users, f, indent=2)

    print(f"Generated {len(users)} users -> {output_path}")

    # Print sample
    print("\nSample user:")
    print(json.dumps(users[0], indent=2))


if __name__ == "__main__":
    main()
