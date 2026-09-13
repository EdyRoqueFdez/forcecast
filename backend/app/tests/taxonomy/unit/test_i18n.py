"""Unit tests for i18n fallback logic — RED phase.

Covers Task 1.4: i18n Fallback Logic (R5)
Specs: 5 locales en, es, pt, fr, zh; fallback chain requested→en→base; unsupported → 406
"""
import pytest


def test_resolve_translation_exact_match():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    translations = {Locale.EN: "Hello", Locale.ES: "Hola", Locale.FR: "Bonjour"}
    text, used = resolve_translation(translations, Locale.ES)
    assert text == "Hola"
    assert used == Locale.ES

    text, used = resolve_translation(translations, Locale.FR)
    assert text == "Bonjour"
    assert used == Locale.FR


def test_resolve_translation_fallback_to_en():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    translations = {Locale.EN: "Hello", Locale.ES: "Hola"}
    # request pt not present → fallback to en
    text, used = resolve_translation(translations, Locale.PT)
    assert text == "Hello"
    assert used == Locale.EN

    # request zh missing → en fallback
    text, used = resolve_translation(translations, Locale.ZH)
    assert text == "Hello"
    assert used == Locale.EN


def test_resolve_translation_fallback_chain_all_locales():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    # Only EN available, all other requests fallback to EN
    translations = {Locale.EN: "Hello"}
    for loc in [Locale.ES, Locale.PT, Locale.FR, Locale.ZH]:
        text, used = resolve_translation(translations, loc)
        assert text == "Hello"
        assert used == Locale.EN


def test_resolve_translation_string_keys():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    # keys as strings should also work
    translations = {"en": "Hello", "es": "Hola"}
    text, used = resolve_translation(translations, Locale.ES)
    assert text == "Hola"
    assert used == Locale.ES

    text, used = resolve_translation(translations, "pt")
    assert text == "Hello"
    assert used == Locale.EN


def test_resolve_translation_with_string_locale_param():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    translations = {Locale.EN: "Hello", Locale.ZH: "你好"}
    text, used = resolve_translation(translations, "zh")
    assert text == "你好"
    assert used == Locale.ZH


def test_resolve_translation_custom_fallback():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    translations = {Locale.ES: "Hola", Locale.FR: "Bonjour"}
    # fallback explicitly to ES when PT missing and EN not present
    text, used = resolve_translation(translations, Locale.PT, fallback=Locale.ES)
    assert text == "Hola"
    assert used == Locale.ES


def test_resolve_translation_unsupported_locale_406():
    from app.taxonomy.services.core import resolve_translation, DomainError

    translations = {"en": "Hello"}
    with pytest.raises(DomainError) as exc:
        resolve_translation(translations, "de")
    assert exc.value.status_code == 406

    with pytest.raises(DomainError) as exc:
        resolve_translation(translations, "xx")
    assert exc.value.status_code == 406


def test_resolve_translation_unsupported_locale_case_insensitive():
    from app.taxonomy.services.core import resolve_translation, DomainError

    translations = {"en": "Hello"}
    with pytest.raises(DomainError) as exc:
        resolve_translation(translations, "DE")
    assert exc.value.status_code == 406


def test_resolve_translation_empty_translations_raises():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation, DomainError

    with pytest.raises(DomainError) as exc:
        resolve_translation({}, Locale.EN)
    # Could be 404 or 406 — but must raise DomainError
    assert exc.value.status_code in (404, 406)


def test_resolve_translation_does_not_mutate_input():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    translations = {Locale.EN: "Hello", Locale.ES: "Hola"}
    original = dict(translations)
    resolve_translation(translations, Locale.PT)
    assert translations == original


def test_resolve_translation_returns_tuple():
    from app.taxonomy.models.enums import Locale
    from app.taxonomy.services.core import resolve_translation

    translations = {Locale.EN: "Hello"}
    result = resolve_translation(translations, Locale.EN)
    assert isinstance(result, tuple)
    assert len(result) == 2
