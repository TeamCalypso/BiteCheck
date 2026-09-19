"""Resolver tests. No AWS, no network - this is the layer that replaces the scraper."""

import pytest

from bitecheck.core import resolver


class TestExtractAsin:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://www.amazon.in/Everest-Garam-Masala/dp/B08XYZ1234", "B08XYZ1234"),
            ("https://www.amazon.in/dp/B08XYZ1234", "B08XYZ1234"),
            ("https://www.amazon.in/gp/product/B08XYZ1234/ref=abc", "B08XYZ1234"),
            ("https://www.amazon.in/gp/aw/d/B08XYZ1234", "B08XYZ1234"),
            ("https://www.amazon.in/Some-Product/dp/b08xyz1234", "B08XYZ1234"),
            ("https://www.amazon.in/s?k=masala&asin=B08XYZ1234", "B08XYZ1234"),
        ],
    )
    def test_finds_asin(self, url, expected):
        assert resolver.extract_asin(url) == expected

    @pytest.mark.parametrize("url", ["", "https://www.amazon.in/s?k=garam+masala", "not a url"])
    def test_returns_none_when_absent(self, url):
        assert resolver.extract_asin(url) is None


class TestExtractSlugTitle:
    def test_recovers_readable_title(self):
        url = "https://www.amazon.in/Everest-Garam-Masala-Pouch-100g/dp/B08XYZ1234"
        assert resolver.extract_slug_title(url) == "Everest Garam Masala Pouch 100g"

    def test_short_form_url_has_no_slug(self):
        assert resolver.extract_slug_title("https://www.amazon.in/dp/B08XYZ1234") is None

    def test_rejects_slug_with_no_letters(self):
        url = "https://www.amazon.in/123-456-789/dp/B08XYZ1234"
        assert resolver.extract_slug_title(url) is None

    def test_strips_url_encoding(self):
        url = "https://www.amazon.in/Tata-Salt-1%2Dkg/dp/B08XYZ1234"
        assert "%" not in (resolver.extract_slug_title(url) or "")


class TestResolve:
    def test_happy_path(self):
        r = resolver.resolve("https://www.amazon.in/Everest-Garam-Masala/dp/B08XYZ1234")
        assert r.asin == "B08XYZ1234"
        assert r.slug_title == "Everest Garam Masala"
        assert r.canonical_url == "https://www.amazon.in/dp/B08XYZ1234"

    def test_rejects_unsupported_store(self):
        with pytest.raises(resolver.UnresolvableUrlError, match="not a supported store"):
            resolver.resolve("https://www.flipkart.com/x/dp/B08XYZ1234")

    def test_rejects_url_without_asin(self):
        with pytest.raises(resolver.UnresolvableUrlError, match="ASIN"):
            resolver.resolve("https://www.amazon.in/s?k=masala")


class TestBestEffortTitle:
    def test_prefers_extension_dom_over_slug(self):
        assert (
            resolver.best_effort_title("Slug Title", "DOM Title", "Catalog Title")
            == "DOM Title"
        )

    def test_falls_back_through_catalog_to_slug(self):
        assert resolver.best_effort_title("Slug Title", None, "Catalog Title") == "Catalog Title"
        assert resolver.best_effort_title("Slug Title", None, None) == "Slug Title"

    def test_none_when_nothing_available(self):
        assert resolver.best_effort_title(None, None, None) is None

    def test_ignores_blank_strings(self):
        assert resolver.best_effort_title("Slug", "   ", None) == "Slug"
