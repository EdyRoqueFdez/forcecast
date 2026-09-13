"""Unit tests for slug normalization — RED phase.

Covers Task 1.2: Slug Normalization (R3)
Specs: R3 — lower, trim, NFKC, transliterate, hyphens, collapse, strip, truncate
"""
import pytest

# hypothesis property tests will run if hypothesis is installed; fallback to parametrized
try:
    from hypothesis import given, strategies as st, settings as hyp_settings
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False


def test_normalize_slug_basic_examples():
    from app.taxonomy.services.core import normalize_slug

    assert normalize_slug("Claude 3.5 Sonnet (2024-10-22)") == "claude-3-5-sonnet-2024-10-22"
    assert normalize_slug("  Hello  World  ") == "hello-world"
    assert normalize_slug("GPT-4__Turbo") == "gpt-4-turbo"
    assert normalize_slug("foo/bar.baz") == "foo-bar-baz"
    assert normalize_slug("---hello---") == "hello"
    assert normalize_slug("a  b   c") == "a-b-c"


def test_normalize_slug_lowercase_and_ascii():
    from app.taxonomy.services.core import normalize_slug

    assert normalize_slug("HELLO") == "hello"
    assert normalize_slug("MiXeD CaSe") == "mixed-case"
    # only ascii alnum + hyphen
    result = normalize_slug("Héllo Wörld")
    assert result == result.lower()
    assert all(c.isalnum() or c == "-" for c in result)


def test_normalize_slug_collapse_and_strip():
    from app.taxonomy.services.core import normalize_slug

    assert normalize_slug("a---b___c") == "a-b-c"
    assert normalize_slug("a  ..  b // c (d)") == "a-b-c-d"
    assert not normalize_slug("test").startswith("-")
    assert not normalize_slug("test").endswith("-")
    assert "--" not in normalize_slug("a--b")
    assert "--" not in normalize_slug("a   b")


def test_normalize_slug_idempotent():
    from app.taxonomy.services.core import normalize_slug

    samples = [
        "claude-3-5-sonnet-2024-10-22",
        "hello-world",
        "gpt-4-turbo",
        "wen-xin-yi-yan-4-0",
        "test-slug",
    ]
    for s in samples:
        assert normalize_slug(s) == normalize_slug(normalize_slug(s)), f"idempotent failed for {s}"


def test_normalize_slug_unicode_nfkc():
    from app.taxonomy.services.core import normalize_slug

    # composed vs decomposed é should normalize same
    # e + combining accent = é via NFKC
    decomposed = "e\u0301"  # e + combining acute
    composed = "\u00e9"  # é
    assert normalize_slug(decomposed) == normalize_slug(composed)
    # transliterated result should be deterministic
    assert normalize_slug("Café") == "cafe"


def test_normalize_slug_pinyin_transliteration():
    from app.taxonomy.services.core import normalize_slug

    # Chinese → pinyin
    result = normalize_slug("文心一言 4.0")
    assert result == "wen-xin-yi-yan-4-0", f"got {result}"
    # ensure ascii only
    assert all(ord(c) < 128 for c in result)


def test_normalize_slug_empty_and_edge():
    from app.taxonomy.services.core import normalize_slug

    assert normalize_slug("") == ""
    assert normalize_slug("   ") == ""
    assert normalize_slug("---") == ""
    assert normalize_slug("___") == ""
    assert normalize_slug("123") == "123"


def test_normalize_slug_truncate():
    from app.taxonomy.services.core import normalize_slug

    long_input = "a" * 300
    result = normalize_slug(long_input)
    assert len(result) <= 255
    # tasks.md says max 64? but spec says 255 — we enforce 255 but also test that overly long is truncated
    assert len(result) == 255
    # truncated result still no leading/trailing hyphen
    assert not result.startswith("-")
    assert not result.endswith("-")


def test_normalize_slug_non_alnum_removed():
    from app.taxonomy.services.core import normalize_slug

    assert normalize_slug("hello@#$%^&*world") == "hello-world"
    assert normalize_slug("test!test") == "test-test"


if HAS_HYPOTHESIS:
    @given(st.text(min_size=0, max_size=50))
    @hyp_settings(max_examples=100)
    def test_property_idempotent(s):
        from app.taxonomy.services.core import normalize_slug

        once = normalize_slug(s)
        twice = normalize_slug(once)
        assert once == twice

    @given(st.text(min_size=0, max_size=50))
    @hyp_settings(max_examples=100)
    def test_property_lowercase(s):
        from app.taxonomy.services.core import normalize_slug

        result = normalize_slug(s)
        assert result == result.lower()

    @given(st.text(min_size=0, max_size=50))
    @hyp_settings(max_examples=100)
    def test_property_ascii_only(s):
        from app.taxonomy.services.core import normalize_slug

        result = normalize_slug(s)
        assert all(c.isalnum() or c == "-" for c in result)
        assert all(ord(c) < 128 for c in result)

    @given(st.text(min_size=0, max_size=50))
    @hyp_settings(max_examples=100)
    def test_property_no_double_hyphen(s):
        from app.taxonomy.services.core import normalize_slug

        result = normalize_slug(s)
        assert "--" not in result

    @given(st.text(min_size=0, max_size=50))
    @hyp_settings(max_examples=100)
    def test_property_no_leading_trailing_hyphen(s):
        from app.taxonomy.services.core import normalize_slug

        result = normalize_slug(s)
        if result:
            assert not result.startswith("-")
            assert not result.endswith("-")

    @given(st.text(min_size=1, max_size=300))
    @hyp_settings(max_examples=50)
    def test_property_max_length(s):
        from app.taxonomy.services.core import normalize_slug

        result = normalize_slug(s)
        assert len(result) <= 255
