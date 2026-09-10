"""Inbound merchant packets — what Acme already collected at signup.

In production this is the payload from signup + add-product + KYC, delivered
by webhook or the merchant API. Here it is a seeded inbox so an analyst can
import instead of re-typing. Manual fill stays available for edge cases.
"""
from __future__ import annotations

from . import config

# Shape matches the public Acme forms. `name` is business name.
INBOUND = [
    {
        "id": "app_lumen",
        "source": "acme.signup",
        "stage": "product_form_pending",
        "kyc": "not_started",
        "note": "Linked to a terminated merchant on the graph",
        "packet": {
            "full_name": "R. Menon",
            "name": "Lumen Labs",
            "website": "https://lumenlabs.app",
            "signup_category": "saas_ai_digital",
            "country": "EE",
            "entity_type": "registered",
            "referral": "Google Search",
            "purpose": "An AI reading companion that summarises and discusses books with you.",
            "product_name": "Lumen Reader",
            "tax_category": "saas",
            "pricing_type": "subscription",
            "price": 9,
            "entitlements": ["telegram"],
        },
    },
    {
        "id": "app_kindle",
        "source": "acme.signup",
        "stage": "product_form_pending",
        "kyc": "not_started",
        "note": "Catalogue / rights case",
        "packet": {
            "full_name": "T. Abadi",
            "name": "Kindle Grove",
            "website": "https://kindlegrove.com",
            "signup_category": "edtech",
            "country": "AE",
            "entity_type": "registered",
            "referral": "LinkedIn",
            "purpose": "A 40,000-title reading companion. Search, summarise and read anything, $9/month.",
            "product_name": "Grove Library",
            "tax_category": "ebook",
            "pricing_type": "subscription",
            "price": 9,
            "entitlements": ["telegram", "files"],
        },
    },
    {
        "id": "app_thistle",
        "source": "acme.signup",
        "stage": "kyc_pending",
        "kyc": "pending",
        "note": "Clean CI analytics applicant",
        "packet": {
            "full_name": "A. Iyer",
            "name": "Thistle Forge",
            "website": "https://thistleforge.dev",
            "signup_category": "saas_ai_digital",
            "country": "IN",
            "entity_type": "registered",
            "referral": "Twitter/X",
            "purpose": "CI pipeline insights for small engineering teams. $29/month per project.",
            "product_name": "Forge Insights",
            "tax_category": "saas",
            "pricing_type": "subscription",
            "price": 29,
            "entitlements": ["github", "license"],
        },
    },
    {
        "id": "app_nightwell",
        "source": "acme.live",
        "stage": "on_platform",
        "kyc": "approved",
        "note": "Edtech on the book — night-heavy volume",
        "packet": {
            "full_name": "P. Sharma",
            "name": "Nightwell Academy",
            "website": "https://nightwell.academy",
            "signup_category": "edtech",
            "country": "IN",
            "entity_type": "registered",
            "referral": "Referred by someone",
            "purpose": "Exam prep and recorded lectures in partnership with universities. Sold to students through campus tie-ups.",
            "product_name": "Campus Prep",
            "tax_category": "edtech",
            "pricing_type": "one_time",
            "price": 49,
            "entitlements": ["telegram", "files"],
        },
    },
    {
        "id": "app_services",
        "source": "acme.signup",
        "stage": "disclaimer",
        "kyc": "not_started",
        "note": "Self-selected Services — policy block",
        "packet": {
            "full_name": "M. Ortega",
            "name": "Quill Harbor Freelance Co",
            "website": "https://quillharbor.co",
            "signup_category": "services",
            "country": "US",
            "entity_type": "individual",
            "referral": "ChatGPT",
            "purpose": "Custom design and freelance coaching for founders.",
            "product_name": "Harbor Studio hours",
            "tax_category": "digital_products",
            "pricing_type": "one_time",
            "price": 199,
            "entitlements": ["discord"],
        },
    },
    {
        "id": "app_gaming",
        "source": "acme.signup",
        "stage": "disclaimer",
        "kyc": "not_started",
        "note": "Gaming category — policy block",
        "packet": {
            "full_name": "J. Park",
            "name": "Nimbus Drop Skins",
            "website": "https://nimbusdrops.app",
            "signup_category": "gaming",
            "country": "KR",
            "entity_type": "registered",
            "referral": "Reddit",
            "purpose": "In-game currency packs and cosmetic drops for mobile titles.",
            "product_name": "Drop credits",
            "tax_category": "digital_products",
            "pricing_type": "one_time",
            "price": 4.99,
            "entitlements": ["license"],
        },
    },
    {
        "id": "app_geo",
        "source": "acme.signup",
        "stage": "signup",
        "kyc": "not_started",
        "note": "Country not on the accepted list",
        "packet": {
            "full_name": "S. Khan",
            "name": "Cedar PK Ledger Co",
            "website": "https://cedarpk.io",
            "signup_category": "saas_ai_digital",
            "country": "PK",
            "entity_type": "registered",
            "referral": "Google Search",
            "purpose": "Inventory software for independent furniture retailers.",
            "product_name": "Cedar Stock",
            "tax_category": "saas",
            "pricing_type": "subscription",
            "price": 19,
            "entitlements": ["license"],
        },
    },
    {
        "id": "app_mismatch",
        "source": "acme.signup",
        "stage": "product_form_pending",
        "kyc": "not_started",
        "note": "Ticked SaaS; copy is consulting",
        "packet": {
            "full_name": "L. Chen",
            "name": "Northline Consulting Pack",
            "website": "https://northlinepack.com",
            "signup_category": "saas_ai_digital",
            "country": "US",
            "entity_type": "individual",
            "referral": "Perplexity",
            "purpose": "Done for you consulting and freelance coaching packaged as a dashboard.",
            "product_name": "Northline OS",
            "tax_category": "saas",
            "pricing_type": "subscription",
            "price": 79,
            "entitlements": ["notion", "discord"],
        },
    },
    {
        "id": "app_audience",
        "source": "acme.signup",
        "stage": "product_form_pending",
        "kyc": "not_started",
        "note": "IN entity; live US-night classes — hours pattern at signup",
        "packet": {
            "full_name": "R. Nair",
            "name": "Westbrook AP Live",
            "website": "https://westbrookap.live",
            "signup_category": "edtech",
            "country": "IN",
            "entity_type": "registered",
            "referral": "YouTube",
            "purpose": "Live AP exam prep for US high school students. Classes run 8pm–11pm EST every weeknight.",
            "product_name": "EST Night AP",
            "tax_category": "edtech",
            "pricing_type": "subscription",
            "price": 39,
            "entitlements": ["telegram", "files"],
        },
    },
    {
        "id": "app_lowvalue",
        "source": "acme.signup",
        "stage": "product_form_pending",
        "kyc": "not_started",
        "note": "Sub-$5 file drop on an accepted category",
        "packet": {
            "full_name": "K. Bell",
            "name": "Mint Icon Pack Co",
            "website": "https://minticonpack.com",
            "signup_category": "saas_ai_digital",
            "country": "US",
            "entity_type": "individual",
            "referral": "Reddit",
            "purpose": "Two thousand icons, instant zip download after payment.",
            "product_name": "Mint pack",
            "tax_category": "digital_products",
            "pricing_type": "one_time",
            "price": 1.99,
            "entitlements": ["files", "telegram"],
        },
    },
    {
        "id": "app_solo_uni",
        "source": "acme.signup",
        "stage": "kyc_pending",
        "kyc": "pending",
        "note": "Person KYC, university partnership in the pitch",
        "packet": {
            "full_name": "A. Mehta",
            "name": "Campus Relay Notes",
            "website": "https://campusrelay.notes",
            "signup_category": "edtech",
            "country": "IN",
            "entity_type": "individual",
            "referral": "Referred by someone",
            "purpose": "Recorded lectures in partnership with universities, resold to campus students.",
            "product_name": "Relay lectures",
            "tax_category": "edtech",
            "pricing_type": "one_time",
            "price": 29,
            "entitlements": ["files"],
        },
    },
]


def list_applications() -> list[dict]:
    out = []
    for row in INBOUND:
        p = row["packet"]
        out.append({
            "id": row["id"],
            "source": row["source"],
            "stage": row["stage"],
            "kyc": row["kyc"],
            "note": row["note"],
            "name": p["name"],
            "country": p["country"],
            "signup_category": p["signup_category"],
            "website": p.get("website"),
        })
    return out


def get_application(app_id: str) -> dict | None:
    for row in INBOUND:
        if row["id"] == app_id:
            return row
    return None


def packet_for_assess(app_id: str) -> dict | None:
    """Flatten an inbound row into the /api/assess body."""
    row = get_application(app_id)
    if not row:
        return None
    packet = dict(row["packet"])
    packet["application_id"] = row["id"]
    packet["category"] = packet.get("signup_category")
    return packet
