import pytest
from pydantic import ValidationError

from app.conversations.schemas import ProductVersionCreate


def test_product_type_accepts_enumerated_type_and_keeps_generic_specs():
    product = {"name": "跑步外套", "product_type": "clothing", "fabric": "棉", "size": "M"}
    assert ProductVersionCreate(product=product).product == product


def test_product_type_rejects_unknown_or_non_text_values_but_preserves_legacy_products():
    for value in ("custom-unreviewed-type", 1, None):
        with pytest.raises(ValidationError):
            ProductVersionCreate(product={"name": "商品", "product_type": value})
    legacy = {"name": "历史商品", "category": "家居", "custom": {"fact": "保留"}}
    assert ProductVersionCreate(product=legacy).product == legacy
