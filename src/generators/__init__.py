"""
Test data generators for load testing.
"""

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from faker import Faker

fake = Faker()


@dataclass
class TransactionTemplate:
    """Template for generating test transactions."""

    country: str
    card_networks: list[str]
    merchant_categories: list[str]
    currency: str
    amount_ranges: list[tuple]

    def generate(self) -> dict:
        """Generate a single transaction."""
        return {
            "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
            "occurred_at": (
                datetime.now(UTC) - datetime.timedelta(minutes=random.randint(0, 10080))
            ).isoformat()
            + "Z",
            "card_id": self._generate_card_id(),
            "card_last4": fake.credit_card_number()[-4:],
            "card_network": random.choice(self.card_networks),
            "merchant_id": f"M{random.randint(10000, 99999)}",
            "mcc": random.choice(self.merchant_categories),
            "ip": fake.ipv4(),
            "amount": self._generate_amount(),
            "currency": self.currency,
            # Use country_code to match rule-engine request schema.
            "country_code": self.country,
            "billing_address": {
                "city": fake.city(),
                "state": fake.state_abbr(),
                "country": self.country,
            },
            "device": {
                "type": random.choice(["mobile", "desktop", "tablet"]),
                "os": random.choice(["iOS", "Android", "Windows", "macOS"]),
                "browser": random.choice(["Chrome", "Safari", "Firefox", "Edge"]),
            },
        }

    def _generate_card_id(self) -> str:
        """Generate tokenized card ID."""
        prefix = random.choice(["4111", "5411", "3700", "6011"])
        masked = f"{prefix}{'*' * 8}{random.randint(1000, 9999)}"
        return masked

    def _generate_amount(self) -> float:
        """Generate amount in cents."""
        range_ = random.choice(self.amount_ranges)
        return round(random.uniform(range_[0], range_[1]), 2)


# Country-specific templates
TEMPLATES = {
    "IN": TransactionTemplate(
        country="IN",
        card_networks=["VISA", "MASTERCARD", "RUPAY"],
        merchant_categories=["5411", "5812", "4111", "7995", "5311", "5541", "5732"],
        currency="INR",
        amount_ranges=[(100, 5000), (5001, 25000), (25001, 100000), (100001, 500000)],
    ),
    "US": TransactionTemplate(
        country="US",
        card_networks=["VISA", "MASTERCARD", "AMEX", "DISCOVER"],
        merchant_categories=["5411", "5812", "4111", "7995", "5311", "5541", "5732"],
        currency="USD",
        amount_ranges=[(100, 5000), (5001, 50000), (50001, 200000), (200001, 1000000)],
    ),
}


class TransactionGenerator:
    """Generates realistic transaction data for load testing."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        fake.seed_instance(seed)

    def generate(self, country: str | None = None, risk_level: str = "normal") -> dict:
        """Generate a single transaction."""
        if country is None:
            country = random.choice(list(TEMPLATES.keys()))

        template = TEMPLATES.get(country, TEMPLATES["IN"])
        tx = template.generate()

        # Adjust amount based on risk level
        if risk_level == "high":
            tx["amount"] = random.uniform(25001, 100000)
        elif risk_level == "suspicious":
            tx["amount"] = random.uniform(100001, 500000)
            tx["ip"] = "192.168.1.1"  # Suspicious: private IP

        return tx

    def generate_batch(
        self, count: int, country: str | None = None, distribution: dict | None = None
    ) -> list[dict]:
        """Generate a batch of transactions."""
        if distribution is None:
            distribution = {"normal": 0.8, "high": 0.15, "suspicious": 0.05}

        transactions = []
        for _ in range(count):
            risk = random.choices(list(distribution.keys()), weights=list(distribution.values()))[0]

            transactions.append(self.generate(country, risk))

        return transactions

    def generate_preauth(self) -> dict:
        """Generate a PREAUTH transaction."""
        return self.generate()

    def generate_postauth(self) -> dict:
        """Generate a POSTAUTH transaction."""
        return self.generate()


class UserGenerator:
    """Generates realistic user/card holder data."""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        fake.seed_instance(seed)

    def generate(self, country: str | None = None) -> dict:
        """Generate a single user."""
        if country is None:
            country = random.choice(["IN", "US", "SG"])

        Faker.seed(random.randint(0, 1000000))

        return {
            "user_id": str(uuid.uuid4()),
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "card_number": self._generate_card_number(),
            "country": country,
            "address": {
                "street": fake.street_address(),
                "city": fake.city(),
                "state": fake.state(),
                "postal_code": fake.zipcode(),
                "country": country,
            },
        }

    def _generate_card_number(self) -> str:
        """Generate a valid-looking card number."""
        prefixes = {"VISA": "4", "MASTERCARD": "5", "AMEX": "3", "RUPAY": "6"}
        network = random.choice(list(prefixes.keys()))
        prefix = prefixes[network]
        return f"{prefix}{random.randint(100000000000000, 999999999999999)}"

    def generate_batch(self, count: int) -> list[dict]:
        """Generate a batch of users."""
        return [self.generate() for _ in range(count)]


class RuleGenerator:
    """Generates test rule definitions."""

    def __init__(self, seed: int = 42):
        random.seed(seed)

    def generate(self, rule_type: str = "PREAUTH") -> dict:
        """Generate a single rule."""
        conditions = [
            {"op": "GT", "field": "amount", "value": 5000},
            {"op": "EQ", "field": "card_network", "value": "VISA"},
            {"op": "IN", "field": "mcc", "values": ["7995", "5816"]},
            {"op": "EXISTS", "field": "is_3ds_verified", "value": False},
        ]

        rule = {
            "rule_id": f"R-{random.randint(1000, 9999)}",
            "rule_version": 1,
            "enabled": True,
            "priority": random.randint(1, 100),
            "condition": {"op": "AND", "args": random.sample(conditions, k=random.randint(1, 2))},
        }

        if rule_type == "PREAUTH":
            rule["action"] = {
                "decision": random.choice(["DECLINE", "REVIEW"]),
                "reason_code": f"RULE_{random.randint(100, 999)}",
            }
        else:
            rule["action"] = {
                "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
                "tags": [f"tag_{i}" for i in range(random.randint(1, 3))],
            }

        return rule

    def generate_batch(self, count: int, rule_type: str = "PREAUTH") -> list[dict]:
        """Generate a batch of rules."""
        return [self.generate(rule_type) for _ in range(count)]

    def generate_ruleset(
        self,
        ruleset_type: str = "PREAUTH",
        rule_count: int = 5,
        country: str = "US",
        environment: str = "local",
    ) -> dict:
        """
        Generate a complete ruleset with multiple rules.

        Args:
            ruleset_type: "PREAUTH" (maps to CARD_AUTH) or "POSTAUTH" (maps to CARD_MONITORING)
            rule_count: Number of rules to generate
            country: Country code (e.g., "US", "IN")
            environment: Environment (e.g., "local", "prod")

        Returns:
            Ruleset dict with standard rule management format
        """
        rules = self.generate_batch(rule_count, ruleset_type)

        # Map ruleset type to standard ruleset keys
        ruleset_key_map = {
            "PREAUTH": "CARD_AUTH",
            "POSTAUTH": "CARD_MONITORING",
        }
        ruleset_key = ruleset_key_map.get(ruleset_type, "CARD_AUTH")

        # Determine region from country (simplified mapping)
        region_map = {
            "US": "AMERICAS",
            "CA": "AMERICAS",
            "MX": "AMERICAS",
            "BR": "AMERICAS",
            "IN": "APAC",
            "SG": "APAC",
            "AU": "APAC",
            "GB": "EMEA",
            "DE": "EMEA",
            "FR": "EMEA",
        }
        region = region_map.get(country, "GLOBAL")

        return {
            "ruleset_id": f"rs_{uuid.uuid4().hex[:12]}",
            "ruleset_key": ruleset_key,
            "country": country,
            "region": region,
            "environment": environment,
            "version": 1,
            "type": ruleset_type,
            "enabled": True,
            "rules": rules,
            "metadata": {
                "created_at": datetime.now(UTC).isoformat() + "Z",
                "source": "load-test",
            },
        }


if __name__ == "__main__":
    # Demo: Generate sample data
    tx_gen = TransactionGenerator()
    user_gen = UserGenerator()
    rule_gen = RuleGenerator()

    print("Sample transaction:")
    import json

    print(json.dumps(tx_gen.generate(), indent=2))

    print("\nSample user:")
    print(json.dumps(user_gen.generate(), indent=2))

    print("\nSample rule:")
    print(json.dumps(rule_gen.generate(), indent=2))

