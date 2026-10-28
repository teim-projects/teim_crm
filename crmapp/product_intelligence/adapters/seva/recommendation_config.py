"""SEVA-specific complementary product relationships.

Product IDs belong only in this CRM-specific configuration,
never in the shared recommendation engine.
"""

SEVA_PRODUCT_RELATIONSHIPS = [
    {
        "source_product_key": "seva:1",
        "target_product_key": "seva:27",
        "strength": 70,
        "reason": "Consider cockroach monitoring traps alongside cockroach management.",
    },
    {
        "source_product_key": "seva:8",
        "target_product_key": "seva:31",
        "strength": 70,
        "reason": "Consider rodent bait stations alongside rodent management.",
    },
    {
        "source_product_key": "seva:8",
        "target_product_key": "seva:34",
        "strength": 65,
        "reason": "Consider rat snap traps alongside rodent management.",
    },
]
