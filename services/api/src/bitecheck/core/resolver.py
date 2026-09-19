"""Turn a messy Amazon URL into an ASIN and a human-readable title.

This module exists because we cannot fetch the product page server-side. Amazon blocks
datacenter IPs, so a Lambda that requests amazon.in gets a 503 or a CAPTCHA the large
majority of the time. What we *can* rely on is the URL itself: Amazon puts a slugified
product name in the path, which is enough for the normalizer to work with.

No network, no AWS. Pure functions, easy to test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

# /dp/B0XXXXXXXX, /gp/product/B0XXXXXXXX, /product/B0XXXXXXXX and the -/en/ locale variants.
_ASIN_IN_PATH = re.compile(
    r"/(?:dp|gp/product|gp/aw/d|product)/([A-Z0-9]{10})(?:[/?]|$)",
    re.IGNORECASE,
)
# Fallback: ?asin=... or a bare 10-char token that looks like an ASIN.
_ASIN_IN_QUERY = re.compile(r"[?&](?:asin|ASIN)=([A-Z0-9]{10})\b")

# The slug is the path segment immediately before /dp/ on a canonical Amazon URL.
_SLUG_BEFORE_DP = re.compile(r"/([^/]+)/(?:dp|gp/product)/[A-Z0-9]{10}", re.IGNORECASE)

# Slug noise that carries no product meaning.
_SLUG_STOPWORDS = {"ref", "dp", "gp", "product", "amazon", "in"}

_ALLOWED_HOSTS = ("amazon.in", "amzn.in", "amazon.com")


@dataclass(frozen=True)
class ResolvedUrl:
    asin: str
    slug_title: str | None
    host: str

    @property
    def canonical_url(self) -> str:
        return f"https://www.amazon.in/dp/{self.asin}"


class UnresolvableUrlError(ValueError):
    """Raised when no ASIN can be recovered. The caller returns HTTP 400."""


def extract_asin(url: str) -> str | None:
    """Pull the 10-character ASIN out of an Amazon URL, or None."""
    if not url:
        return None
    match = _ASIN_IN_PATH.search(url) or _ASIN_IN_QUERY.search(url)
    return match.group(1).upper() if match else None


def extract_slug_title(url: str) -> str | None:
    """Recover a readable product title from the URL slug.

    ``/Everest-Garam-Masala-Pouch-100g/dp/B0XXXXXXXX`` becomes
    ``"Everest Garam Masala Pouch 100g"``.

    Returns None for short-form URLs like ``/dp/B0XXXXXXXX`` that carry no slug, which is
    a normal and expected case, not an error.
    """
    if not url:
        return None
    # Match against the path only. Matching the whole URL lets "//www.amazon.in/dp/B0..."
    # satisfy the leading "/([^/]+)/" and return the hostname as the product title.
    path = urlparse(url).path or url
    match = _SLUG_BEFORE_DP.search(path)
    if not match:
        return None

    raw = unquote(match.group(1))
    words = [w for w in raw.split("-") if w]
    words = [w for w in words if w.lower() not in _SLUG_STOPWORDS]
    if not words:
        return None

    title = " ".join(words).strip()
    # A slug of pure noise (hashes, ref tokens) is worse than nothing: it would send the
    # normalizer looking for a product that does not exist.
    if len(title) < 3 or not any(c.isalpha() for c in title):
        return None
    return title


def resolve(url: str) -> ResolvedUrl:
    """Parse an Amazon product URL.

    Raises UnresolvableUrlError when there is no ASIN to work with.
    """
    asin = extract_asin(url)
    if not asin:
        raise UnresolvableUrlError(
            "Could not find a product ID (ASIN) in that link. "
            "Copy the URL from the product page address bar; it should contain /dp/."
        )

    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if host and not any(host.endswith(h) for h in _ALLOWED_HOSTS):
        raise UnresolvableUrlError(
            f"{host} is not a supported store. BiteCheck currently reads amazon.in links."
        )

    return ResolvedUrl(asin=asin, slug_title=extract_slug_title(url), host=host or "amazon.in")


def best_effort_title(
    slug_title: str | None,
    extracted_title: str | None = None,
    catalog_name: str | None = None,
) -> str | None:
    """Pick the most trustworthy title available.

    Order matters: the extension's DOM read is the real page title, the curated catalog is
    human-checked, and the slug is a last resort because Amazon truncates and mangles it.
    """
    for candidate in (extracted_title, catalog_name, slug_title):
        if candidate and candidate.strip():
            return candidate.strip()
    return None
