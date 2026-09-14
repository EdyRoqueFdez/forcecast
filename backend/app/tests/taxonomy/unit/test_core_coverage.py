"""Additional unit tests for core.py — coverage boost for missing lines.

Covers: _transliterate CJK paths, invalid status coercion, translation edge cases,
        validate_price non-Decimal, price_sort_key non-Decimal input.
"""
from decimal import Decimal
import pytest


class TestTransliterateCJK:
    def test_transliterate_cjk_with_pinyin_map(self):
        from app.taxonomy.services.core import normalize_slug
        result = normalize_slug("文心一言")
        assert result == "wen-xin-yi-yan"

    def test_transliterate_cjk_unknown_char(self):
        from app.taxonomy.services.core import _transliterate
        result = _transliterate("龍")
        assert isinstance(result, str)
        assert all(ord(c) < 128 or c.isspace() for c in result)

    def test_transliterate_mixed_cjk_and_latin(self):
        from app.taxonomy.services.core import normalize_slug
        result = normalize_slug("文 Hello 心")
        assert "hello" in result
        assert "wen" in result
        assert "xin" in result

    def test_transliterate_cjk_only_unknown(self):
        from app.taxonomy.services.core import _transliterate
        result = _transliterate("龍虎")
        assert isinstance(result, str)

    def test_transliterate_non_cjk_unicode(self):
        from app.taxonomy.services.core import normalize_slug
        result = normalize_slug("Ñoño")
        assert result == "nono"

    def test_transliterate_accented_chars(self):
        from app.taxonomy.services.core import normalize_slug
        assert normalize_slug("São Paulo") == "sao-paulo"
        assert normalize_slug("München") == "munchen"

    def test_transliterate_pypinyin_installed(self, monkeypatch):
        import sys
        from types import ModuleType
        mock_pypinyin = ModuleType("pypinyin")

        def mock_lazy_pinyin(ch):
            mapping = {"文": ["wen"], "心": ["xin"], "一": ["yi"], "言": ["yan"]}
            return mapping.get(ch, ["?"])

        mock_pypinyin.lazy_pinyin = mock_lazy_pinyin
        monkeypatch.setitem(sys.modules, "pypinyin", mock_pypinyin)
        from app.taxonomy.services.core import normalize_slug
        result = normalize_slug("文心一言 4.0")
        assert result == "wen-xin-yi-yan-4-0"

    def test_transliterate_pypinyin_exception_fallback(self, monkeypatch):
        import sys
        from types import ModuleType
        mock_pypinyin = ModuleType("pypinyin")

        def mock_lazy_pinyin(ch):
            if ch == "心":
                raise RuntimeError("pypinyin internal error")
            return [ch]

        mock_pypinyin.lazy_pinyin = mock_lazy_pinyin
        monkeypatch.setitem(sys.modules, "pypinyin", mock_pypinyin)
        from app.taxonomy.services.core import normalize_slug
        result = normalize_slug("文心")
        assert isinstance(result, str)

    def test_transliterate_pypinyin_empty_result(self, monkeypatch):
        import sys
        from types import ModuleType
        mock_pypinyin = ModuleType("pypinyin")

        def mock_lazy_pinyin(ch):
            if ch == "心":
                return []
            return [ch]

        mock_pypinyin.lazy_pinyin = mock_lazy_pinyin
        monkeypatch.setitem(sys.modules, "pypinyin", mock_pypinyin)
        from app.taxonomy.services.core import normalize_slug
        result = normalize_slug("文心")
        assert isinstance(result, str)

    def test_transliterate_pypinyin_exception_unknown_char(self, monkeypatch):
        import sys
        from types import ModuleType
        mock_pypinyin = ModuleType("pypinyin")

        def mock_lazy_pinyin(ch):
            if ch == "龍":
                raise RuntimeError("unknown char")
            return [ch]

        mock_pypinyin.lazy_pinyin = mock_lazy_pinyin
        monkeypatch.setitem(sys.modules, "pypinyin", mock_pypinyin)
        from app.taxonomy.services.core import normalize_slug
        result = normalize_slug("文龍")
        assert isinstance(result, str)


class TestCoerceModelStatusInvalid:
    def test_coerce_model_status_invalid_string(self):
        from app.taxonomy.services.core import _coerce_model_status, DomainError
        with pytest.raises(DomainError) as exc:
            _coerce_model_status("invalid_status")
        assert exc.value.status_code == 422
        assert "Invalid ModelStatus" in str(exc.value)

    def test_coerce_model_status_valid_string(self):
        from app.taxonomy.services.core import _coerce_model_status
        from app.taxonomy.models.enums import ModelStatus
        result = _coerce_model_status("draft")
        assert result == ModelStatus.DRAFT

    def test_coerce_model_status_enum_passthrough(self):
        from app.taxonomy.services.core import _coerce_model_status
        from app.taxonomy.models.enums import ModelStatus
        result = _coerce_model_status(ModelStatus.APPROVED)
        assert result == ModelStatus.APPROVED


class TestCoerceProviderStatusInvalid:
    def test_coerce_provider_status_invalid_string(self):
        from app.taxonomy.services.core import _coerce_provider_status, DomainError
        with pytest.raises(DomainError) as exc:
            _coerce_provider_status("bogus")
        assert exc.value.status_code == 422
        assert "Invalid ProviderStatus" in str(exc.value)

    def test_coerce_provider_status_valid_string(self):
        from app.taxonomy.services.core import _coerce_provider_status
        from app.taxonomy.models.enums import ProviderStatus
        result = _coerce_provider_status("active")
        assert result == ProviderStatus.ACTIVE


class TestCoerceCategoryStatusInvalid:
    def test_coerce_category_status_invalid_string(self):
        from app.taxonomy.services.core import _coerce_category_status, DomainError
        with pytest.raises(DomainError) as exc:
            _coerce_category_status("not_a_status")
        assert exc.value.status_code == 422
        assert "Invalid CategoryStatus" in str(exc.value)

    def test_coerce_category_status_valid_string(self):
        from app.taxonomy.services.core import _coerce_category_status
        from app.taxonomy.models.enums import CategoryStatus
        result = _coerce_category_status("active")
        assert result == CategoryStatus.ACTIVE


class TestResolveTranslationEdgeCases:
    def test_invalid_locale_keys_skipped(self):
        from app.taxonomy.models.enums import Locale
        from app.taxonomy.services.core import resolve_translation
        translations = {"en": "Hello", "invalid_key": "Bad", "es": "Hola"}
        text, used = resolve_translation(translations, Locale.ES)
        assert text == "Hola"
        assert used == Locale.ES

    def test_all_invalid_keys_raises_404(self):
        from app.taxonomy.services.core import resolve_translation, DomainError
        translations = {"invalid1": "foo", "invalid2": "bar"}
        with pytest.raises(DomainError) as exc:
            resolve_translation(translations, "en")
        assert exc.value.status_code == 404
        assert "No valid translations" in str(exc.value)

    def test_requested_and_fallback_missing_raises_404(self):
        from app.taxonomy.models.enums import Locale
        from app.taxonomy.services.core import resolve_translation, DomainError
        translations = {Locale.ES: "Hola"}
        with pytest.raises(DomainError) as exc:
            resolve_translation(translations, Locale.FR)
        assert exc.value.status_code == 404
        assert "Translation not found" in str(exc.value)

    def test_fallback_to_en_when_requested_missing(self):
        from app.taxonomy.models.enums import Locale
        from app.taxonomy.services.core import resolve_translation
        translations = {Locale.EN: "Hello"}
        text, used = resolve_translation(translations, Locale.PT)
        assert text == "Hello"
        assert used == Locale.EN

    def test_empty_value_in_translation_skipped(self):
        from app.taxonomy.models.enums import Locale
        from app.taxonomy.services.core import resolve_translation, DomainError
        translations = {Locale.EN: "", Locale.ES: "Hola"}
        with pytest.raises(DomainError) as exc:
            resolve_translation(translations, Locale.FR)
        assert exc.value.status_code == 404


class TestValidatePriceEdgeCases:
    def test_validate_price_rejects_int(self):
        from app.taxonomy.services.core import validate_price, DomainError
        with pytest.raises(DomainError) as exc:
            validate_price(42)
        assert exc.value.status_code == 422

    def test_validate_price_rejects_string(self):
        from app.taxonomy.services.core import validate_price, DomainError
        with pytest.raises(DomainError) as exc:
            validate_price("3.14")
        assert exc.value.status_code == 422

    def test_validate_price_accepts_zero(self):
        from app.taxonomy.services.core import validate_price
        assert validate_price(Decimal("0")) == Decimal("0")

    def test_validate_price_accepts_large(self):
        from app.taxonomy.services.core import validate_price
        assert validate_price(Decimal("999999.99")) == Decimal("999999.99")


class TestPriceSortKeyEdgeCases:
    def test_price_sort_key_with_int(self):
        from app.taxonomy.services.core import price_sort_key
        result = price_sort_key(42)
        assert result[0] == 0
        assert result[1] == Decimal("42")

    def test_price_sort_key_with_float(self):
        from app.taxonomy.services.core import price_sort_key
        result = price_sort_key(3.14)
        assert result[0] == 0
        assert result[1] == Decimal("3.14")

    def test_price_sort_key_with_string_number(self):
        from app.taxonomy.services.core import price_sort_key
        result = price_sort_key("10.5")
        assert result[0] == 0
        assert result[1] == Decimal("10.5")

    def test_price_sort_key_with_unconvertible(self):
        from app.taxonomy.services.core import price_sort_key
        result = price_sort_key("not_a_number")
        assert result == (1, Decimal("Infinity"))

    def test_price_sort_key_with_none(self):
        from app.taxonomy.services.core import price_sort_key
        result = price_sort_key(None)
        assert result == (1, Decimal("Infinity"))

    def test_price_sort_key_with_valid_decimal(self):
        from app.taxonomy.services.core import price_sort_key
        result = price_sort_key(Decimal("5.00"))
        assert result == (0, Decimal("5.00"))


class TestDomainError:
    def test_domain_error_str(self):
        from app.taxonomy.services.core import DomainError
        err = DomainError("Not found", status_code=404)
        assert str(err) == "404 Not found"
        assert err.status_code == 404
        assert err.message == "Not found"

    def test_domain_error_default_status(self):
        from app.taxonomy.services.core import DomainError
        err = DomainError("Conflict")
        assert err.status_code == 409
