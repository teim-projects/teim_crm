from pathlib import Path

p = Path("crmapp/product_intelligence/recommendations/recommendation_engine.py")
s = p.read_text(encoding="utf-8")
original = s

def replace_once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f"STOP: Could not find {label}. File was not saved.")
    s = s.replace(old, new, 1)

# Import the model.
if "from crmapp.product_intelligence.recommendations.upsell_ml import UpsellMLEngine" not in s:
    replace_once(
        "from crmapp.product_intelligence.recommendations.upsell_engine import ProductUpsellEngine",
        "from crmapp.product_intelligence.recommendations.upsell_engine import ProductUpsellEngine\nfrom crmapp.product_intelligence.recommendations.upsell_ml import UpsellMLEngine",
        "upsell engine import"
    )

# Inject the model and optional verified historical training records.
if "upsell_training_records=None" not in s:
    replace_once(
        "upsell_rule_provider=None,",
        "upsell_rule_provider=None,\n        upsell_ml_engine=None,\n        upsell_training_records=None,",
        "constructor argument"
    )

if "self.upsell_ml_ready = False" not in s:
    replace_once(
        "        self.upsell_rule_provider = upsell_rule_provider\n",
        """        self.upsell_rule_provider = upsell_rule_provider
        # Train only with caller-supplied, verified historical upgrade outcomes.
        self.upsell_ml_engine = upsell_ml_engine or UpsellMLEngine()
        self.upsell_ml_ready = False
        if upsell_training_records:
            self.upsell_ml_engine.fit(upsell_training_records)
            self.upsell_ml_ready = True
""",
        "upsell model initialization"
    )

# Shared generic feature builder, usable for both training and inference.
if "def build_upsell_ml_features(" not in s:
    replace_once(
        "    def recommend(self, customer_id):",
        '''    @staticmethod
    def build_upsell_ml_features(candidate, product=None):
        """Build generic features; CRM-specific mappings belong in adapters."""
        product = product or candidate
        raw = {
            "candidate_type": candidate.get("candidate_type"),
            "category": product.get("category"),
            "product_type": product.get("product_type") or product.get("service_type"),
            "family": product.get("family"),
            "sub_family": product.get("sub_family"),
            "type": product.get("type"),
            "version": product.get("version"),
            "price": product.get("price", product.get("unit_price")),
            "relationship_strength": candidate.get("relationship_strength", 0),
            "upgrade_source_product_key": candidate.get("upgrade_source_product_key"),
        }
        features = {}
        for key, value in raw.items():
            if value is None or isinstance(value, (dict, list, tuple, set)):
                continue
            if isinstance(value, bool):
                features[key] = int(value)
            elif isinstance(value, (int, float)):
                features[key] = value
            else:
                value = str(value).strip()
                if value:
                    features[key] = value
        return features

    def recommend(self, customer_id):''',
        "recommend method"
    )

# Use ML probabilities for genuine upgrade candidates only.
if "ML_UPSELL_MODEL" not in s:
    replace_once(
        "        scored_candidates = self.scoring_engine.score_candidates(\\n",
        '''        # ML scores configured UPSELL candidates only; cross-sells remain distinct.
        if self.upsell_ml_ready:
            upsell_candidates = [
                candidate for candidate in eligible_candidates
                if candidate.get("candidate_type") == "UPSELL"
            ]
            ranked_upsells = self.upsell_ml_engine.rank_candidates([
                {
                    "product_key": self._product_key(candidate),
                    "features": self.build_upsell_ml_features(
                        candidate, product_map.get(self._product_key(candidate))
                    ),
                }
                for candidate in upsell_candidates
            ], limit=len(upsell_candidates))

            probability_by_key = {
                item["product_key"]: item["ml_probability"]
                for item in ranked_upsells
            }
            for candidate in upsell_candidates:
                key = self._product_key(candidate)
                if key in probability_by_key:
                    candidate["ml_probability"] = probability_by_key[key]
                    candidate["relationship_source"] = "ML_UPSELL_MODEL"

        scored_candidates = self.scoring_engine.score_candidates(
''',
        "candidate scoring point"
    )

# Include probability in each recommendation.
if '"ml_probability": candidate.get("ml_probability")' not in s:
    replace_once(
        '                "upgrade_reason": candidate.get("upgrade_reason"),\n',
        '                "upgrade_reason": candidate.get("upgrade_reason"),\n                "ml_probability": candidate.get("ml_probability"),\n',
        "recommendation output fields"
    )

if s == original:
    raise SystemExit("No changes made; the expected code may already be patched.")

p.write_text(s, encoding="utf-8")
print("Patch applied successfully.")
