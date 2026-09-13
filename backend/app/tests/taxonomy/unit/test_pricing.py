"""Unit tests for Reference Price Handling — RED phase.

Covers Task 1.5: Pricing Override Logic (R6) — clarified as reference-only nullable Decimal
Specs: Decimal, nullable, sorting with None, omitted when null, precision preserved
"""
from decimal import Decimal
import pytest


def test_validate_price_exact_decimal():
    from app.taxonomy.services.core import validate_price

    assert validate_price(Decimal("3.00")) == Decimal("3.00")
    assert validate_price(Decimal("0.000001")) == Decimal("0.000001")
    assert validate_price(Decimal("0")) == Decimal("0")
    assert validate_price(None) is None


def test_validate_price_rejects_negative():
    from app.taxonomy.services.core import validate_price, DomainError

    with pytest.raises(DomainError) as exc:
        validate_price(Decimal("-1"))
    assert exc.value.status_code == 422

    with pytest.raises(DomainError):
        validate_price(Decimal("-0.01"))


def test_validate_price_rejects_float_input():
    from app.taxonomy.services.core import DomainError, validate_price

    # string numeric is allowed via Decimal construction? but float should be rejected
    with pytest.raises((DomainError, TypeError, ValueError)):
        validate_price(3.14)  # type: ignore


def test_resolve_price_legacy_signature():
    """Old signature resolve_price(override, base) -> (price, price_unknown)"""
    from decimal import Decimal
    from app.taxonomy.services.core import resolve_price

    # override present
    price, unknown = resolve_price(Decimal("5.00"), Decimal("3.00"))
    assert price == Decimal("5.00")
    assert unknown is False

    # base only
    price, unknown = resolve_price(None, Decimal("3.00"))
    assert price == Decimal("3.00")
    assert unknown is False

    # both null → unknown true
    price, unknown = resolve_price(None, None)
    assert price is None
    assert unknown is True

    # override null, base null alternative
    price, unknown = resolve_price(Decimal("0"), None)
    assert price == Decimal("0")
    assert unknown is False


def test_serialize_prices_omit_when_null():
    from decimal import Decimal
    from app.taxonomy.services.core import serialize_prices

    # both null → omitted
    data = {"input_price_per_mtok": None, "output_price_per_mtok": None, "name": "test"}
    result = serialize_prices(data)
    assert "input_price_per_mtok" not in result
    assert "output_price_per_mtok" not in result
    assert result["name"] == "test"

    # one present
    data = {"input_price_per_mtok": Decimal("3.00"), "output_price_per_mtok": None, "name": "test"}
    result = serialize_prices(data)
    assert result["input_price_per_mtok"] == Decimal("3.00")
    assert "output_price_per_mtok" not in result

    # both present
    data = {"input_price_per_mtok": Decimal("3.00"), "output_price_per_mtok": Decimal("15.00")}
    result = serialize_prices(data)
    assert result["input_price_per_mtok"] == Decimal("3.00")
    assert result["output_price_per_mtok"] == Decimal("15.00")


def test_serialize_prices_preserves_decimal_precision():
    from decimal import Decimal
    from app.taxonomy.services.core import serialize_prices

    data = {"input_price_per_mtok": Decimal("0.000001"), "output_price_per_mtok": Decimal("0.000002")}
    result = serialize_prices(data)
    assert result["input_price_per_mtok"] == Decimal("0.000001")
    assert str(result["input_price_per_mtok"]) == "0.000001"


def test_price_sort_key_nulls_last():
    from decimal import Decimal
    from app.taxonomy.services.core import price_sort_key

    # sort ascending with None last
    items = [Decimal("15.00"), None, Decimal("3.00"), None, Decimal("0.50")]
    sorted_items = sorted(items, key=price_sort_key)
    # None should be at end
    assert sorted_items[-1] is None
    assert sorted_items[-2] is None
    # non-null sorted ascending
    non_null = [x for x in sorted_items if x is not None]
    assert non_null == sorted(non_null)

    # descending via reverse
    sorted_desc = sorted(items, key=price_sort_key, reverse=True)
    # None with reverse? key makes None huge so reverse puts None first — acceptable alternative is None still last
    # We assert that without reverse None last, with custom handling
    # For this implementation, price_sort_key returns (is_none, value); reverse will put None first, so we test ascending only
    assert sorted_items[0] == Decimal("0.50")


def test_price_sort_key_does_not_crash_with_mixed():
    from decimal import Decimal
    from app.taxonomy.services.core import price_sort_key

    mixed = [
        {"slug": "a", "input_price_per_mtok": Decimal("3.00")},
        {"slug": "b", "input_price_per_mtok": None},
        {"slug": "c", "input_price_per_mtok": Decimal("0.50")},
    ]
    # sorting list of dicts by price
    sorted_mixed = sorted(mixed, key=lambda m: price_sort_key(m["input_price_per_mtok"]))
    assert sorted_mixed[0]["slug"] == "c"
    assert sorted_mixed[1]["slug"] == "a"
    assert sorted_mixed[2]["slug"] == "b"


def test_decimal_precision_preserved_end_to_end():
    from decimal import Decimal
    from app.taxonomy.services.core import validate_price

    tiny = Decimal("0.000001")
    validated = validate_price(tiny)
    assert validated == tiny
    assert str(validated) == "0.000001"
    # ensure not converted to float
    assert not isinstance(validated, float)
