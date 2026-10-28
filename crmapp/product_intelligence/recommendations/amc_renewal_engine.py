
from datetime import date


class AMCRenewalEngine:
    """CRM-independent AMC contract renewal recommendations."""

    def __init__(self, review_days=30, upcoming_days=60):
        if review_days < 0 or upcoming_days < review_days:
            raise ValueError(
                "Use non-negative windows with upcoming_days >= review_days."
            )

        self.review_days = review_days
        self.upcoming_days = upcoming_days

    @staticmethod
    def _normalise(value):
        return str(value or "").strip().casefold()

    @staticmethod
    def _contract_key(record):
        source_crm = str(
            record.get("source_crm") or ""
        ).strip().lower()

        contract_id = record.get("amc_id")

        if contract_id is None:
            contract_id = record.get("contract_id")

        if contract_id is None:
            return None

        return f"{source_crm}:{contract_id}"

    def generate_recommendations(self, amc_records, today=None):
        """
        Generate one recommendation per eligible contract.

        Input records may contain repeated rows because one contract can
        have multiple AMC visits. Contract identities prevent duplicates.
        """
        today = today or date.today()
        contracts = {}

        for record in amc_records or []:
            if not isinstance(record, dict):
                continue

            contract_key = self._contract_key(record)

            if contract_key is None:
                continue

            # Keep one record per CRM-specific contract.
            contracts.setdefault(contract_key, record)

        recommendations = []

        for contract_key, record in contracts.items():
            status = self._normalise(record.get("contract_status"))
            active = record.get("contract_is_active")
            end_date = record.get("contract_end_date")

            if status != "active" or active not in (True, 1):
                continue

            if not isinstance(end_date, date):
                continue

            days_remaining = (end_date - today).days

            # Do not recommend renewal for already-ended contracts.
            if days_remaining < 0:
                continue

            # A recorded renewal request means don't prompt again.
            if record.get("renewal_requested_at") is not None:
                continue

            if days_remaining <= self.review_days:
                recommendation_type = "AMC_RENEWAL"
                score = 90
                reason = (
                    f"Active AMC contract ends in {days_remaining} day(s); "
                    "review renewal."
                )
            elif days_remaining <= self.upcoming_days:
                recommendation_type = "AMC_UPCOMING_RENEWAL"
                score = 65
                reason = (
                    f"Active AMC contract ends in {days_remaining} day(s); "
                    "plan an upcoming renewal."
                )
            else:
                continue

            recommendations.append({
                "customer_id": record.get("customer_id"),
                "source_crm": record.get("source_crm") or "",
                "contract_id": record.get(
                    "amc_id", record.get("contract_id")
                ),
                "contract_key": contract_key,
                "contract_number": record.get("contract_number"),
                "contract_end_date": end_date,
                "days_to_expiry": days_remaining,
                "recommendation_type": recommendation_type,
                "score": score,
                "reasons": [reason],
                "renewal_status": record.get("renewal_status"),
            })

        return sorted(
            recommendations,
            key=lambda item: (
                item["days_to_expiry"],
                item["contract_key"],
            ),
        )
