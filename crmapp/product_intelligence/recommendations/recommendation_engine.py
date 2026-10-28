from crmapp.product_intelligence.cross_selling.cross_sell_ml import (
    CrossSellMLEngine,
)
from crmapp.product_intelligence.universal_features.customer_product_features import (
    UniversalCustomerProductFeatures,
)
from crmapp.product_intelligence.recommendations.candidate_generator import (
    ProductCandidateGenerator,
)
from crmapp.product_intelligence.recommendations.association_metrics import (
    ProductAssociationMetrics,
)
from crmapp.product_intelligence.recommendations.scoring_engine import (
    ProductScoringEngine,
)
from crmapp.product_intelligence.recommendations.output import (
    ProductRecommendationOutput,
)
from crmapp.product_intelligence.recommendations.eligibility import (
    ProductEligibility,
)
from crmapp.product_intelligence.recommendations.amc_renewal_engine import (
    AMCRenewalEngine,
)


class ProductRecommendationEngine:
    """CRM-independent product and AMC recommendation pipeline."""

    def __init__(
        self,
        source_crm,
        product_adapter,
        service_adapter,
        quotation_adapter,
        amc_adapter,
        eligibility=None,
        amc_renewal_engine=None,
        product_relationships=None,
        allow_historical_cross_sell=True,
        invoice_adapter=None,
    ):
        """Initialize the shared engine with injected CRM-specific components."""

        if not source_crm or not str(source_crm).strip():
            raise ValueError("source_crm must be provided.")

        self.source_crm = str(source_crm).strip().lower()

        adapters = {
            "product_adapter": product_adapter,
            "service_adapter": service_adapter,
            "quotation_adapter": quotation_adapter,
            "amc_adapter": amc_adapter,
        }

        missing = [
            name
            for name, adapter in adapters.items()
            if adapter is None
        ]

        if missing:
            raise ValueError(
                "All CRM adapters must be injected. Missing: "
                + ", ".join(missing)
            )

        # CRM-specific relationships are supplied by the integration layer.
        # The shared engine does not import or assume any CRM's configuration.
        self.product_relationships = list(
            product_relationships or []
        )

        self.allow_historical_cross_sell = bool(
            allow_historical_cross_sell
        )

        self.product_adapter = product_adapter
        self.service_adapter = service_adapter
        self.quotation_adapter = quotation_adapter
        self.amc_adapter = amc_adapter
        self.invoice_adapter = invoice_adapter

        self.customer_feature_builder = (
            UniversalCustomerProductFeatures()
        )
        self.candidate_generator = ProductCandidateGenerator()
        self.association_metrics_engine = ProductAssociationMetrics()
        self.cross_sell_ml_engine = CrossSellMLEngine()
        self.scoring_engine = ProductScoringEngine()
        self.output_formatter = ProductRecommendationOutput()

        self.eligibility = (
            eligibility
            if eligibility is not None
            else ProductEligibility()
        )

        self.amc_renewal_engine = (
            amc_renewal_engine
            if amc_renewal_engine is not None
            else AMCRenewalEngine()
        )

    def _product_key(self, record):
        """Build a product identity using the selected CRM namespace."""

        if record.get("product_key"):
            return str(record["product_key"])

        product_id = record.get("product_id")

        # If an adapter omits source_crm, use the explicitly selected CRM.
        source_crm = str(
            record.get("source_crm") or self.source_crm
        ).strip().lower()

        source_product_id = record.get(
            "source_product_id",
            product_id,
        )

        if source_product_id is None:
            return None

        source_product_id = str(source_product_id).strip()

        if not source_product_id:
            return None

        return f"{source_crm}:{source_product_id}"

    def _belongs_to_selected_crm(self, record):
        """Prevent records from different CRM namespaces from mixing."""

        record_crm = str(
            record.get("source_crm") or self.source_crm
        ).strip().lower()

        return record_crm == self.source_crm

    def recommend(self, customer_id):
        """Generate product recommendations for a customer."""

        products = self.product_adapter.get_universal_products()

        service_products = (
            self.service_adapter.get_universal_service_products()
        )

        quotation_products = (
            self.quotation_adapter.get_universal_quotation_products()
        )

        amc_products = (
            self.amc_adapter.get_universal_amc_products()
        )

        invoice_products = (
            self.invoice_adapter.get_universal_invoice_products()
            if self.invoice_adapter is not None
            else []
        )

        # Invoice training data must map unambiguously to catalogue products.
        invoice_products = [
            record for record in invoice_products
            if record.get("product_id") is not None
            and record.get("product_key")
            and record.get("product_mapping_status", "matched") == "matched"
        ]

        # Keep all input records within the selected CRM.
        products = [
            product
            for product in products
            if self._belongs_to_selected_crm(product)
        ]

        service_products = [
            record
            for record in service_products
            if self._belongs_to_selected_crm(record)
        ]

        quotation_products = [
            record
            for record in quotation_products
            if self._belongs_to_selected_crm(record)
        ]

        amc_products = [
            record
            for record in amc_products
            if self._belongs_to_selected_crm(record)
        ]

        invoice_products = [
            record
            for record in invoice_products
            if self._belongs_to_selected_crm(record)
        ]

        product_map = {
            self._product_key(product): product
            for product in products
            if self._product_key(product) is not None
        }

        customer_features = (
            self.customer_feature_builder.build_customer_features(
                customer_id=customer_id,
                service_products=service_products,
                quotation_products=quotation_products,
                amc_products=amc_products,
                source_crm=self.source_crm,
            )
        )

        association_metrics = self.association_metrics_engine.build(
            service_products
        )

        # The complete catalogue allows configured relationships to
        # recommend eligible products the customer has not used before.
        candidates = self.candidate_generator.generate(
            customer_id=customer_id,
            service_products=service_products,
            quotation_products=quotation_products,
            amc_products=amc_products,
            source_crm=self.source_crm,
            product_catalog=products,
            configured_relationships=self.product_relationships,
            allow_historical_cross_sell=(
                self.allow_historical_cross_sell
            ),
        )

        # Learn only from service and unambiguously matched invoice records.
        purchase_records = service_products + invoice_products
        self.cross_sell_ml_engine.fit(purchase_records)

        customer_purchase_records = [
            r for r in purchase_records
            if self.candidate_generator._belongs_to_customer(
                r, customer_id, self.source_crm
            )
        ]
        purchased_keys = {
            self._product_key(r)
            for r in customer_purchase_records
            if self._product_key(r) is not None
        }

        ml_predictions = self.cross_sell_ml_engine.recommend(purchased_keys)

        # Never recommend products already used, quoted, or covered by AMC.
        excluded_keys = set()
        for records in (
            service_products, invoice_products,
            quotation_products, amc_products
        ):
            for record in records:
                if self.candidate_generator._belongs_to_customer(
                    record, customer_id, self.source_crm
                ):
                    key = self._product_key(record)
                    if key is not None:
                        excluded_keys.add(key)

        candidate_by_key = {
            self._product_key(c): c
            for c in candidates
            if self._product_key(c) is not None
        }

        for prediction in ml_predictions:
            target_key = prediction["product_key"]
            if target_key in excluded_keys or target_key not in product_map:
                continue

            existing = candidate_by_key.get(target_key)
            if existing is not None:
                if existing.get("candidate_type") != "CROSS_SELL":
                    continue
                # Enrich an existing cross-sell rather than duplicating it.
                existing["ml_support"] = prediction["support"]
                existing["ml_confidence"] = prediction["confidence"]
                existing["ml_lift"] = prediction["lift"]
                existing["relationship_source"] = "ML_ASSOCIATION"
                continue

            product = product_map[target_key]
            candidate = {
                **product,
                "candidate_type": "CROSS_SELL",
                "service_count": 0,
                "total_quantity": 0,
                "amc_visit_count": 0,
                "amc_count": 0,
                "source_products": prediction["source_products"],
                "co_occurrence_count": 0,
                "quotation_interest": False,
                "relationship_source": "ML_ASSOCIATION",
                "relationship_strength": round(
                    prediction["confidence"] * 100
                ),
                "relationship_reason": (
                    "Learned product association: confidence "
                    f"{prediction['confidence']:.1%}, lift "
                    f"{prediction['lift']:.2f}"
                ),
                "ml_support": prediction["support"],
                "ml_confidence": prediction["confidence"],
                "ml_lift": prediction["lift"],
            }
            candidates.append(candidate)
            candidate_by_key[target_key] = candidate

        eligible_candidates = []

        for candidate in candidates:
            product_key = self._product_key(candidate)
            product = product_map.get(product_key)

            if product is None:
                continue

            if not self.eligibility.is_eligible(product):
                continue

            eligible_candidates.append(candidate)

        scored_candidates = self.scoring_engine.score_candidates(
            candidates=eligible_candidates,
            customer_features=customer_features,
            association_metrics_engine=self.association_metrics_engine,
            association_metrics=association_metrics,
        )

        recommendations = []

        for candidate in scored_candidates:
            product_key = self._product_key(candidate)
            product = product_map.get(product_key)

            if product is None:
                continue

            recommendations.append({
                "product_id": candidate.get("product_id"),
                "source_crm": (
                    product.get("source_crm") or self.source_crm
                ),
                "source_product_id": product.get(
                    "source_product_id",
                    candidate.get("source_product_id"),
                ),
                "product_key": product_key,
                "product_name": product["product_name"],
                "category": product.get("category"),
                "candidate_type": candidate["candidate_type"],
                "score": candidate["score"],
                "reasons": candidate["reasons"],
                "source_products": candidate.get(
                    "source_products", []
                ),
                "co_occurrence_count": candidate.get(
                    "co_occurrence_count", 0
                ),
                "quotation_interest": candidate.get(
                    "quotation_interest", False
                ),
                "relationship_source": candidate.get(
                    "relationship_source"
                ),
                "relationship_strength": candidate.get(
                    "relationship_strength", 0
                ),
                "relationship_reason": candidate.get(
                    "relationship_reason"
                ),
                "upgrade_source_product_key": candidate.get(
                    "upgrade_source_product_key"
                ),
                "upgrade_reason": candidate.get("upgrade_reason"),
            })

        return self.output_formatter.format_recommendations(
            customer_id=customer_id,
            recommendations=recommendations,
        )

    def recommend_amc_renewals(
        self,
        customer_id=None,
        today=None,
    ):
        """Generate AMC renewal recommendations for the selected CRM."""

        contracts = self.amc_adapter.get_universal_amc_contracts()

        contracts = [
            contract
            for contract in contracts
            if self._belongs_to_selected_crm(contract)
        ]

        recommendations = (
            self.amc_renewal_engine.generate_recommendations(
                contracts,
                today=today,
            )
        )

        if customer_id is not None:
            requested_customer = str(customer_id)

            recommendations = [
                item
                for item in recommendations
                if (
                    str(item.get("customer_id")) == requested_customer
                    and self._belongs_to_selected_crm(item)
                )
            ]

        return recommendations

    def recommend_all(self, customer_id, today=None):
        """Return product and AMC renewal recommendations together."""

        return {
            "customer_id": customer_id,
            "source_crm": self.source_crm,
            "product_recommendations": self.recommend(customer_id),
            "amc_renewal_recommendations": (
                self.recommend_amc_renewals(
                    customer_id=customer_id,
                    today=today,
                )
            ),
        }

