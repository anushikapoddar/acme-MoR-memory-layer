"""Assumed operating constants.

Every number here is ASSUMED, not measured -- see section 6 of the problem
statement. They are gathered in one module so a real figure can replace an
assumed one without hunting through the codebase.
"""
from __future__ import annotations

# -- Section 6.1: assumed operating baseline -------------------------------
LIFETIME_APPLICATIONS = 4000
APPROVAL_RATE = 0.65
ACTIVE_MERCHANTS = 1900
CONFIRMED_BAD_RATE = 0.017          # of approvals
ANNUAL_VOLUME_USD = 150_000_000
HUMAN_TOUCH_RATE = 0.40
MEDIAN_DECISION_HOURS = 14
ANNUAL_ADMISSION_LOSS_USD = 350_000

# -- Section 6.2: the operating point --------------------------------------
COST_FALSE_APPROVE_USD = 25_000.0
COST_FALSE_DECLINE_USD = 4_000.0

#: Expected cost is equal when p*C_fa == (1-p)*C_fd, so the indifference
#: point is C_fd / (C_fa + C_fd). With the assumed costs that is ~0.1379.
DECLINE_THRESHOLD = COST_FALSE_DECLINE_USD / (
    COST_FALSE_APPROVE_USD + COST_FALSE_DECLINE_USD
)
#: Below this we auto-approve without a human; between the two a human decides.
AUTO_APPROVE_THRESHOLD = 0.04

# -- Card network monitoring (Visa VAMP, effective 1 Apr 2026) -------------
VAMP_ACQUIRER_ABOVE_STANDARD = 0.005   # 0.50%
VAMP_ACQUIRER_EXCESSIVE = 0.007        # 0.70%
VAMP_MERCHANT_EXCESSIVE = 0.015        # 1.50%
VAMP_MIN_EVENTS = 1500
ASSUMED_PORTFOLIO_VAMP = 0.0040        # 0.40%, thin headroom

# -- Section 2.1: prepaid / insolvency exposure ----------------------------
PREPAID_EXPOSURE_RATIO = 0.15
PREPAID_EXPOSURE_USD = ANNUAL_VOLUME_USD * PREPAID_EXPOSURE_RATIO  # ~$22.5M

# -- Assumed loss distribution by category (section 6.3, question 11) ------
LOSS_DISTRIBUTION = {
    "deceptive_billing": 0.35,
    "product_drift": 0.20,
    "undisclosed_illegality": 0.15,
    "insolvency": 0.12,
    "recidivist_ring": 0.08,
    "transaction_laundering": 0.05,
    "account_takeover": 0.03,
    "card_testing": 0.02,
}

# -- Risk postures (section 2.1) -------------------------------------------
POSTURES = {
    "deceiving": "Deceiving us",
    "drifting": "Drifting from us",
    "failing": "Failing",
    "attacked": "Being attacked",
    "memory": "Memory",
}

CATEGORY_POSTURE = {
    "undisclosed_illegality": "deceiving",
    "recidivist_ring": "deceiving",
    "transaction_laundering": "deceiving",
    "merchant_identity_fraud": "deceiving",
    "bust_out": "deceiving",
    "product_drift": "drifting",
    "deceptive_billing": "drifting",
    "ai_abuse_controls": "drifting",
    "insolvency": "failing",
    "concentration": "failing",
    "account_takeover": "attacked",
    "card_testing": "attacked",
}

#: Postures that say something about the *merchant's own conduct*. Precedent
#: retrieval matches on product and pitch, so it may only reason from these.
#: A merchant whose checkout was used for card testing, or whose account was
#: taken over, tells us nothing about the integrity of a merchant selling a
#: similar product -- they were the victim, not the actor.
PRECEDENT_RELEVANT_POSTURES = {"deceiving", "drifting"}

#: Laplace-style smoothing for precedent. Without it, one bad match in six
#: swings the likelihood ratio by an order of magnitude.
PRECEDENT_SMOOTHING = 4.0

#: Cosine floor for a retrieved neighbour to count as precedent. Measured, not
#: guessed: in this corpus every neighbour that genuinely went bad matches at
#: 0.24 or above, while the noise floor of shared boilerplate vocabulary sits
#: between 0.09 and 0.18. See App._precedent.
PRECEDENT_MIN_SIMILARITY = 0.20

# -- Acme MoR merchant acceptance policy taxonomy ------------------------------
POLICY_ACCEPTED = {"saas", "digital_goods", "templates_plugins_apps", "ai_product"}
POLICY_RESTRICTED = {
    "ai_content_generation", "marketing_outreach", "resume_hiring_exam",
    "spiritual_astrology", "audio_music_chatbot", "ebooks_publications",
    "productized_services",
}
POLICY_PROHIBITED = {
    "adult_nsfw", "manual_digital_services", "low_value_digital",
    "physical_goods", "in_person_services", "unlicensed_financial",
    "company_registration", "licensed_professional", "travel_booking",
    "gambling", "crypto_nft", "gaming_virtual_goods", "piracy_ip_violation",
    "streaming_iptv", "hosting_vpn_telecom", "surveillance_tools",
    "spam_scraping", "proxy_anti_tos", "cheating_tools", "weapons_violence",
    "health_diagnostics", "miracle_claims", "dating_social_matching",
    "religious_guidance", "donations_no_deliverable", "marketplace_resale",
}

#: Signup dropdown on app.acmemor.com — coarser than the policy taxonomy.
#: Maps to (tier, internal category). Prohibited here is a hard do-not-onboard.
SIGNUP_CATEGORY = {
    "saas_ai_digital": ("accepted", "saas"),
    "edtech": ("accepted", "ebooks_publications"),
    "services": ("prohibited", "manual_digital_services"),
    "financial_services": ("prohibited", "unlicensed_financial"),
    "physical_products": ("prohibited", "physical_goods"),
    "gaming": ("prohibited", "gaming_virtual_goods"),
    "marketplace": ("prohibited", "marketplace_resale"),
    "others": ("restricted", "productized_services"),
}

#: Add-product tax category on the Acme catalogue form.
TAX_CATEGORY = {
    "digital_products": "digital_goods",
    "saas": "saas",
    "ebook": "ebooks_publications",
    "edtech": "ebooks_publications",
}

#: ISO-2 of countries eligible to onboard (ID-issuing country), from
#: docs.acmemor.com/miscellaneous/accepted-countries-and-territories
#: as of 1 Sep 2026. Anything else is a geo block.
ACCEPTED_COUNTRY_ISO = frozenset("""
AL AD AI AG AR AM AW AU AT AZ BS BH BB BE BZ BJ BM BT BO BA BW BR VG BN BG BF
CV KH CA KY CL CN CO KM CK CR HR CW CY CZ DK DJ DM DO EC SV EE SZ ET FK FO FJ
FI FR PF GA GM GE DE GH GI GR GL GD GU GT GG GN GW GY HN HK HU IS IN ID IE IM
IL IT JM JP JE JO KZ KI KG LV LS LR LI LT LU MG MW MY MV ML MT MR MU MX MD MC
MN ME MS MZ NA NP NL NC NZ NE MK NO OM PW PA PY PE PH PL PT PR QA KR RO RW KN
LC MF PM VC WS SM ST SA SN RS SC SL SG SX SK SI SB ZA ES LK SR SE CH TW TJ TZ
TH TL TG TO TT TN TR TM TC UG AE GB US UY UZ VU VN VI WF ZM ZW
""".split())

#: Supported before 23 Mar 2026; new onboarding is not. Enhanced monitoring.
GRANDFATHERED_COUNTRY_ISO = frozenset(
    "BD EG GQ ER MH FM MA NR NG TV UA".split())


def map_signup_category(raw: str) -> tuple[str, str]:
    """Return (tier, internal_category) for a signup or legacy category id."""
    cat = (raw or "").strip()
    if cat in SIGNUP_CATEGORY:
        return SIGNUP_CATEGORY[cat]
    if cat in POLICY_PROHIBITED:
        return "prohibited", cat
    if cat in POLICY_RESTRICTED:
        return "restricted", cat
    if cat in POLICY_ACCEPTED:
        return "accepted", cat
    if cat in TAX_CATEGORY:
        mapped = TAX_CATEGORY[cat]
        return map_signup_category(mapped)
    return "restricted", "saas"


def country_eligibility(iso: str) -> str:
    code = (iso or "").strip().upper()
    if code in ACCEPTED_COUNTRY_ISO:
        return "accepted"
    if code in GRANDFATHERED_COUNTRY_ISO:
        return "grandfathered"
    return "restricted"


#: Representative IANA timezone for the ID-issuing country. Night hours are
#: always local to this zone — never UTC. The US is collapsed to Eastern as a
#: demo stand-in; a live system would use the merchant's stated operating tz.
COUNTRY_TZ = {
    "US": ("America/New_York", "ET"),
    "CA": ("America/Toronto", "ET"),
    "GB": ("Europe/London", "UK"),
    "IE": ("Europe/Dublin", "IST-IE"),
    "IN": ("Asia/Kolkata", "IST"),
    "PK": ("Asia/Karachi", "PKT"),
    "AE": ("Asia/Dubai", "GST"),
    "SG": ("Asia/Singapore", "SGT"),
    "JP": ("Asia/Tokyo", "JST"),
    "KR": ("Asia/Seoul", "KST"),
    "AU": ("Australia/Sydney", "AEST"),
    "NZ": ("Pacific/Auckland", "NZST"),
    "DE": ("Europe/Berlin", "CET"),
    "FR": ("Europe/Paris", "CET"),
    "NL": ("Europe/Amsterdam", "CET"),
    "PL": ("Europe/Warsaw", "CET"),
    "EE": ("Europe/Tallinn", "EET"),
    "BR": ("America/Sao_Paulo", "BRT"),
    "ZA": ("Africa/Johannesburg", "SAST"),
    "NG": ("Africa/Lagos", "WAT"),
    "RU": ("Europe/Moscow", "MSK"),
    "IR": ("Asia/Tehran", "IRST"),
}

#: Local clock window treated as "night" for hours_mismatch. Same clock times,
#: different UTC instants, once the country timezone is applied.
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6


def local_night_window(iso: str) -> tuple[str, str, int, int]:
    """Return (iana_tz, abbreviation, start_hour, end_hour) for a country."""
    code = (iso or "").strip().upper()
    tz, abbr = COUNTRY_TZ.get(code, (f"local/{code or '??'}", code or "local"))
    return tz, abbr, NIGHT_START_HOUR, NIGHT_END_HOUR


def local_night_label(iso: str) -> str:
    tz, abbr, start, end = local_night_window(iso)
    return f"{start:02d}:00–{end:02d}:00 {abbr} ({tz})"

# -- Acme MoR platform facts (acmemor.com, 20 Aug 2026) ----------
PLATFORM_NAME = "Acme MoR"
PLATFORM_TAGLINE = "Merchant of record for digital products"
COUNTRIES_SUPPORTED = 220
BUILDERS_ON_PLATFORM = 50_000
BUSINESSES_ON_PLATFORM = 25_000

#: The product surface Acme actually sells. Merchants use these, so risk
#: signals differ by product: usage-based billing produces different dispute
#: patterns from a one-time licence.
PLATFORM_FEATURES = [
    "Merchant of Record", "Subscriptions", "Credit-Based Billing",
    "Usage-Based Billing", "Adaptive Currency", "Local Payment Methods",
    "Reporting & Analytics", "In-App Purchases", "Fraud Protection",
    "No Code Checkout", "Purchasing Power Parity", "Discount Codes",
    "Multi Brand Support", "Storefront", "Affiliate Program",
    "Digital Product Delivery", "License Keys",
]

#: Acme's own brand palette. The UI reads these so the console
#: and config cannot drift apart.
BRAND = {
    "lime":   "#1A4A38",   # signature dark green
    "forest": "#004F32",   # dark ground
    "green":  "#2F7A52",
    "blue":   "#1264FF",
    "pink":   "#EE46BC",
    "purple": "#7A5AF8",
    "yellow": "#C4922A",
    "orange": "#FF8B37",
    "red":    "#E83439",
    "ink":    "#12261C",   # body text -- a green-black, not a grey
    "muted":  "#5C7468",
    "rule":   "#E7E7E7",
}

DEMO_TODAY = "2026-08-20"
