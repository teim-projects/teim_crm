
class ConfiguredUpsellRules:
    """
    Generic rule provider for explicitly verified product upgrades.

    Expected relationship format:
    {
        "source_product_key": "crm_a:basic",
        "target_product_key": "crm_a:premium",
        "strength": 90,
        "reason": "Verified upgrade for the same requirement",
    }

    CRM-specific relationships are injected by the integration layer.
    No upgrade is inferred from names, prices, or product IDs.
    """

    def __init__(self, relationships=None, source_crm=None):
        self.source_crm = (
            str(source_crm).strip().lower()
            if source_crm
            else None
        )
        self.rules = {}

        for relationship in relationships or []:
            if not isinstance(relationship, dict):
                continue

            source_key = str(
                relationship.get("source_product_key") or ""
            ).strip().lower()

            target_key = str(
                relationship.get("target_product_key") or ""
            ).strip().lower()

            if not source_key or not target_key:
                continue

            if source_key == target_key:
                continue

            if self.source_crm:
                prefix = f"{self.source_crm}:"
                if not (
                    source_key.startswith(prefix)
                    and target_key.startswith(prefix)
                ):
                    continue

            try:
                strength = float(relationship.get("strength", 0))
            except (TypeError, ValueError):
                continue

            if not 0 <= strength <= 100:
                continue

            rule = {
                "source_product_key": source_key,
                "target_product_key": target_key,
                "strength": strength,
                "reason": str(
                    relationship.get("reason") or ""
                ).strip(),
            }

            self.rules.setdefault(source_key, {})[target_key] = rule

    def get_upsell_products(self, source_product_key):
        source_key = str(source_product_key or "").strip().lower()
        return sorted(self.rules.get(source_key, {}).keys())

    def is_upsell(self, source_product_key, candidate_product_key):
        source_key = str(source_product_key or "").strip().lower()
        candidate_key = str(candidate_product_key or "").strip().lower()

        if not source_key or not candidate_key:
            return False

        if source_key == candidate_key:
            return False

        return candidate_key in self.rules.get(source_key, {})

    def get_rule(self, source_product_key, candidate_product_key):
        source_key = str(source_product_key or "").strip().lower()
        candidate_key = str(candidate_product_key or "").strip().lower()

        rule = self.rules.get(source_key, {}).get(candidate_key)
        return dict(rule) if rule else None



class SevaUpsellRules(ConfiguredUpsellRules):
    """
    SEVA-specific upgrade relationships.

    Candidate rules must be confirmed by SEVA before production use.
    """

    RULES = []

    def __init__(self):
        super().__init__(
            relationships=self.RULES,
            source_crm="seva",
        )

