"""Deterministic synthetic merchant corpus.

The population is sized to the assumed numbers in section 6.1 and seeded so
every run produces the identical corpus -- a demo that changes between runs is
not a demo. Ground truth is authored here, which is what makes the replay
harness in ``replay.py`` exactly measurable.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import random
from dataclasses import dataclass, field, asdict
from typing import Optional

from . import config

SEED = 20260820
TODAY = _dt.date.fromisoformat(config.DEMO_TODAY)


def _d(days_ago: int) -> str:
    return (TODAY - _dt.timedelta(days=days_ago)).isoformat()


def _hash(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


@dataclass
class Merchant:
    id: str
    name: str
    domain: str
    country: str
    founder: str
    founder_email: str
    category_claimed: str
    pitch: str
    offering_claimed: str

    applied_at: str
    domain_age_days: int
    registrar: str
    nameserver: str
    site_template: str
    terms_hash: str
    payout_iban: str
    payout_branch: str
    payout_holder: str
    fulfilment: list[str]

    status: str = "pending"          # pending|approved|declined|terminated
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    rationale: Optional[str] = None

    # post-approval telemetry
    monthly_volume: float = 0.0
    settled_txns: int = 0
    disputes: int = 0
    fraud_reports: int = 0
    refund_rate: float = 0.0
    prepaid_balance: float = 0.0
    annual_plan_share: float = 0.0
    offering_observed: Optional[str] = None
    observed_category: Optional[str] = None
    last_observed_at: Optional[str] = None
    payout_changed_at: Optional[str] = None
    login_anomaly: bool = False
    micro_txn_share: float = 0.0
    forecast_monthly: float = 0.0

    # authored ground truth -- never shown to the decision engine
    truth_bad: bool = False
    truth_category: Optional[str] = None
    truth_note: str = ""

    scenario: Optional[str] = None   # marks the hand-authored narrative cases
    #: True for merchants that are real, publicly-named Acme merchants. Their
    #: product descriptions are factual (from Acme's own case studies); volumes
    #: and dispute figures are illustrative. See REAL_CUSTOMERS and the guard in
    #: build() -- a real merchant may never carry an adverse finding.
    real: bool = False
    #: Analyst declined this merchant in the live session. Distinct from
    #: authored ``truth_bad`` so seed declines do not rewrite the prior.
    learned_bad: bool = False

    # Acme signup / add-product packet (optional on the synthetic corpus)
    website: Optional[str] = None
    entity_type: Optional[str] = None          # individual | registered
    referral: Optional[str] = None
    signup_category: Optional[str] = None      # dropdown on app.acmemor.com
    tax_category: Optional[str] = None         # Add product tax category
    pricing_type: Optional[str] = None         # one_time | subscription | usage
    price_usd: float = 0.0
    entitlements: list[str] = field(default_factory=list)
    #: Share of settled volume in the merchant country's *local* night window
    #: (see config.local_night_label). Never UTC — 22:00 IST is not 22:00 ET.
    #: Post-approval: you cannot see this at signup, only after volume lands.
    night_txn_share: float = 0.0

    def vamp_ratio(self) -> float:
        if self.settled_txns <= 0:
            return 0.0
        return (self.disputes + self.fraud_reports) / self.settled_txns

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# vocabulary for the background population
# --------------------------------------------------------------------------
_PRE = ["Lumen", "Northwind", "Bookly", "Vellum", "Quartz", "Harbor", "Ember",
        "Sable", "Cobalt", "Nimbus", "Orchard", "Pinebase", "Kestrel", "Thistle",
        "Marlow", "Fathom", "Gable", "Verdant", "Lantern", "Copper", "Ridgeway",
        "Solstice", "Aster", "Bramble", "Cinder", "Dovetail", "Ellis", "Foxglove",
        "Grayson", "Hollow", "Ironwood", "Juniper", "Keystone", "Larkspur",
        "Meridian", "Nettle", "Oakfield", "Plumb", "Quill", "Rookery", "Sorrel",
        "Tamarind", "Umber", "Vesper", "Willow", "Yarrow", "Zephyr", "Alder"]
_SUF = ["Labs", "Cloud", "Studio", "Works", "Systems", "Stack", "Kit", "HQ",
        "Desk", "Flow", "Sync", "Forge", "Base", "Loop", "Grid", "Craft"]
_JOIN = ["forge", "base", "kit", "loop", "grid", "craft", "wave", "path",
         "ly", "io", "hub", "peak", "mint", "port", "field", "byte", "arc",
         "nest", "span", "well", "lane", "point", "shift", "core"]
_FIRST = ["Arun", "Maya", "Sofia", "Liam", "Noor", "Kenji", "Elena", "Tomas",
          "Priya", "Diego", "Anja", "Yusuf", "Clara", "Mateo", "Ines", "Rafal",
          "Leila", "Bjorn", "Nadia", "Owen", "Sanne", "Hugo", "Amara", "Viktor",
          "Rhea", "Kwame", "Freya", "Idris", "Marta", "Sean", "Yara", "Pieter",
          "Nina", "Omar", "Greta", "Tariq", "Lucia", "Adam", "Zoya", "Felix",
          "Hana", "Bruno", "Iris", "Samir"]
_LAST = ["Menon", "Okafor", "Lindqvist", "Ferreira", "Nakamura", "Duarte",
         "Abadi", "Kowalski", "Vasquez", "Bergman", "Iyer", "Novak", "Haddad",
         "Petrov", "Sandoval", "Whitfield", "Aoki", "Brennan", "Castellano",
         "Ahmadi", "Bakker", "Costa", "Delacroix", "Eriksen", "Fontaine",
         "Gupta", "Hoffman", "Ilyin", "Jansen", "Karlsson", "Laurent", "Marek",
         "Nowak", "Olsen", "Pereira", "Quintana", "Rossi", "Sorensen", "Tanaka",
         "Ueda", "Varga", "Weber", "Xu", "Yilmaz", "Zieliński", "Andersen",
         "Barros", "Chowdhury", "Dvorak", "Espinoza", "Falk", "Grimaldi",
         "Hassan", "Ibrahim", "Jokinen", "Kaur", "Larsen", "Moreau", "Nguyen",
         "Ostrowski", "Pavlov", "Rahman", "Silva", "Toure", "Ulrich", "Vidal",
         "Wallace", "Yakubu", "Zhang", "Alvarez", "Bianchi", "Chen", "Dahl",
         "Engel", "Fischer", "Garcia", "Holm", "Ivanov", "Jimenez", "Kim",
         "Lemaire", "Mensah", "Nilsson", "Ortega", "Park", "Reyes", "Suzuki",
         "Thomsen", "Uribe", "Voss", "Widmer", "Yoon", "Zapata", "Adeyemi",
         "Blomqvist", "Cruz", "Doyle"]
_COUNTRY = ["US", "IN", "GB", "DE", "SG", "AE", "BR", "NL", "PL", "CA", "AU", "NG"]
_REGISTRAR = ["Namecheap", "Cloudflare", "Porkbun", "GoDaddy", "Gandi", "Hover"]
_NS = ["ns.cloudflare", "ns.vercel", "ns.netlify", "ns.digitalocean",
       "ns.hetzner", "ns.route53", "ns.bunny"]
_TEMPLATE = ["tpl-astro-saas", "tpl-next-landing", "tpl-tailkit", "tpl-shipfast",
             "tpl-nuxt-studio", "tpl-plainhtml", "tpl-framer-a", "tpl-webflow-b"]
_BANK = ["Meridian Bank / Tallinn-04", "Northbay / Singapore-11", "Cresta / Lisbon-02",
         "Ardent / Dublin-07", "Halcyon / Riga-03", "Pinegrove / Toronto-09",
         "Solent / London-21", "Verity / Amsterdam-05"]
_CHANNELS = [["email"], ["discord"], ["github"], ["notion"], ["email", "discord"],
             ["github", "discord"], ["email", "notion"], ["telegram"]]

_LEGIT = [
    ("saas", "Team {x} analytics for small product teams", "analytics dashboard subscription"),
    ("saas", "Automated changelog and release notes for {x} repos", "release-notes SaaS"),
    ("digital_goods", "A pack of {x} UI icons and illustrations", "icon pack download"),
    ("templates_plugins_apps", "A {x} starter template for indie founders", "code template licence"),
    ("ai_product", "AI meeting summariser for {x} teams", "meeting summarisation SaaS"),
    ("ai_product", "AI code review assistant for {x} pull requests", "code review SaaS"),
    ("saas", "Uptime and status pages for {x} services", "monitoring subscription"),
    ("digital_goods", "A course on shipping {x} products solo", "video course access"),
    ("saas", "Invoicing and expense tracking for {x} freelancers", "invoicing SaaS"),
    ("templates_plugins_apps", "A Figma plugin for {x} design systems", "figma plugin licence"),
]
_X = ["remote", "solo", "async", "small", "bootstrapped", "technical", "distributed",
      "early-stage", "indie", "lean"]


#: Publicly named on acmemor.com/case-studies. Product descriptions are
#: taken from those case studies; operating figures are illustrative.
REAL_CUSTOMERS = [
    # (name, domain, country, founder, category, pitch, offering, monthly, txns, refund)
    ("Mole", "mole.sh", "CN", "Mole Team", "digital_goods",
     "A Mac cleanup and optimisation app, grown out of an open-source CLI. "
     "One-time purchase with an automated licence key.",
     "mac utility licence", 28_400, 1_180, 0.011),
    ("Vibe3D", "vibe3d.ai", "IN", "Vibe3D Team", "ai_product",
     "AI architectural rendering. Architects and interior designers produce "
     "presentation-grade renders in minutes instead of weeks.",
     "AI rendering subscription", 20_000, 640, 0.014),
    ("Draftly", "draftly.so", "IN", "Draftly Team", "ai_product",
     "AI-generated 3D websites for startups and creators, replacing "
     "$5,000 agency projects with a $25-$200 subscription.",
     "AI website builder subscription", 25_000, 700, 0.017),
    ("ReplyDaddy", "replydaddy.com", "IN", "ReplyDaddy Team", "marketing_outreach",
     "Finds relevant Reddit conversations and drafts contextual replies for "
     "agencies, SMBs and indie founders.",
     "reddit marketing subscription", 6_400, 210, 0.020),
    ("CatDoes", "catdoes.com", "DE", "CatDoes Team", "ai_product",
     "A no-code AI mobile app builder. AI agents handle design, logic and "
     "store deployment for non-technical founders.",
     "app builder subscription", 11_500, 430, 0.019),
    ("Indilingo", "indilingo.com", "IN", "Indilingo Team", "ai_product",
     "Learn Indian languages -- Tamil, Telugu, Kannada, Sanskrit -- with "
     "interactive lessons and real-time AI speaking practice.",
     "language learning subscription", 14_200, 1_640, 0.016),
    ("Scira AI", "scira.ai", "IN", "Scira Team", "ai_product",
     "Synthesises answers across the web into one sourced result, with "
     "GitHub, Notion and Slack integrations.",
     "AI research subscription", 18_600, 890, 0.013),
    ("PeerPush", "peerpush.net", "US", "PeerPush Team", "saas",
     "Structures product data so AI systems like ChatGPT and Perplexity can "
     "find and rank software. Ships an MCP server.",
     "software discovery subscription", 9_800, 340, 0.012),
    ("IndieKit", "indiekit.pro", "IN", "IndieKit Team", "templates_plugins_apps",
     "A production-ready Next.js boilerplate with auth, payments, database "
     "and AI integrations pre-built. The fastest way to launch a SaaS.",
     "boilerplate licence", 12_400, 360, 0.015),
    ("Betide Studio", "betidestudio.com", "SG", "Betide Team", "templates_plugins_apps",
     "Multiplayer, authentication and deployment plugins for Unreal Engine, "
     "sold through the Epic marketplace to ~40,000 developers.",
     "unreal engine plugin licence", 16_900, 520, 0.010),
    ("Healthify", "healthify.me", "IN", "Healthify Team", "saas",
     "India's health and fitness platform -- calorie and macro tracking with "
     "an AI coach and human nutritionist plans, sold as a subscription.",
     "health coaching subscription", 41_800, 3_240, 0.013),
    ("Parakeet AI", "parakeet-ai.com", "US", "Parakeet Team", "ai_product",
     "A real-time AI interview assistant. Transcribes the interviewer's "
     "question and drafts a structured answer, sold as hour credits.",
     "interview assistant credits", 22_300, 1_410, 0.021),
    ("MATIKS", "matiks.com", "IN", "Matiks Team", "digital_goods",
     "Mental-arithmetic and brain-training games on iOS and Android. Daily "
     "challenges and a ranked arena behind a subscription.",
     "brain training subscription", 13_700, 2_180, 0.014),
    ("GPAI", "gpai.app", "IN", "GPAI Team", "ai_product",
     "An AI STEM copilot for students -- photo and PDF problem solving, "
     "lecture-notes cheatsheets, and a STEM-tuned chat in one workspace.",
     "AI study subscription", 19_400, 2_760, 0.018),
    ("Cardboard", "cardboard.to", "US", "Cardboard Team", "ai_product",
     "An agentic video editor for growth and marketing teams. Plans start at "
     "$60/month with a project quota and a free trial.",
     "AI video editing subscription", 24_600, 380, 0.016),
    ("SurgeGrowth", "surgegrowth.io", "IN", "SurgeGrowth Team", "marketing_outreach",
     "Growth and demand-generation tooling for early-stage software teams, "
     "sold as a monthly subscription.",
     "growth tooling subscription", 8_900, 290, 0.019),
    ("Vaya", "vaya.app", "IN", "Vaya Team", "ai_product",
     "A consumer mobile app sold by subscription through the Acme checkout.",
     "consumer app subscription", 10_200, 1_120, 0.015),
]

REAL_CUSTOMER_NAMES = frozenset(n for n, *_ in REAL_CUSTOMERS)


def _real_customers() -> list[Merchant]:
    """Real, publicly-named Acme merchants -- seeded as what they are.

    All ten are healthy approved merchants with low dispute ratios. None
    carries an adverse finding, and ``build()`` asserts that none ever will:
    these are real businesses, and the corpus around them is randomised.
    """
    out: list[Merchant] = []
    for i, (name, domain, country, founder, cat, pitch,
            offering, monthly, txns, refund) in enumerate(REAL_CUSTOMERS):
        slug = domain.split(".")[0]
        applied = 240 + i * 17
        out.append(Merchant(
            id=f"m95{i:03d}", name=name, domain=domain, country=country,
            founder=founder, founder_email=f"team@{domain}",
            category_claimed=cat, pitch=pitch, offering_claimed=offering,
            applied_at=_d(applied), domain_age_days=600 + i * 40,
            registrar="Cloudflare", nameserver="ns.cloudflare",
            site_template=f"tpl-own-{slug}", terms_hash=_hash("terms", slug),
            payout_iban=f"{country} •••• {4100 + i * 7}",
            payout_branch=_BANK[i % len(_BANK)], payout_holder=name.upper(),
            fulfilment=["email"] if i % 2 else ["email", "github"],
            status="approved", decided_at=_d(applied - 1),
            decided_by="analyst.priya",
            rationale="Approved: real product, verifiable operator, clean history.",
            monthly_volume=float(monthly), settled_txns=txns,
            disputes=max(1, int(txns * 0.004)), fraud_reports=int(txns * 0.001),
            refund_rate=refund, annual_plan_share=0.25,
            prepaid_balance=round(monthly * 12 * 0.25 * 0.5, 2),
            forecast_monthly=round(monthly * 0.9, 2),
            offering_observed=offering, observed_category=cat,
            last_observed_at=_d(2 + i),
            real=True,
        ))
    return out


def _mk_id(n: int) -> str:
    return f"m{n:05d}"


# --------------------------------------------------------------------------
# the hand-authored narrative cases
# --------------------------------------------------------------------------
def _scenarios() -> list[Merchant]:
    """Cases the demo is built around. Written by hand so they are exact."""
    shared_ns = "ns.bunny"
    shared_tpl = "tpl-plainhtml"
    shared_terms = _hash("terms", "vellum-lineage")
    ring_branch = "Meridian Bank / Tallinn-04"
    ring_holder = "R MENON HOLDINGS"

    out: list[Merchant] = []

    # ---- Case C lineage: the terminated original --------------------------
    out.append(Merchant(
        id="m90001", forecast_monthly=45000, name="Vellum Reader", domain="vellumreader.com", country="EE",
        founder="R. Menon", founder_email="ops@vellumreader.com",
        category_claimed="ebooks_publications",
        pitch="An AI reading companion with a curated library of classic and modern titles.",
        offering_claimed="ebook library subscription",
        applied_at=_d(320), domain_age_days=14, registrar="Namecheap",
        nameserver=shared_ns, site_template=shared_tpl, terms_hash=shared_terms,
        payout_iban="EE •••• 4470", payout_branch=ring_branch, payout_holder=ring_holder,
        fulfilment=["telegram"], status="terminated", decided_at=_d(318),
        decided_by="analyst.priya", rationale="Approved: catalogue product, restricted category, demo looked legitimate.",
        monthly_volume=61_000, settled_txns=8_400, disputes=190, fraud_reports=42,
        refund_rate=0.09, offering_observed="ebook library subscription",
        observed_category="ebooks_publications", last_observed_at=_d(160),
        truth_bad=True, truth_category="undisclosed_illegality",
        truth_note="Publisher rights claim on day 74. No licences ever held.",
        scenario="vellum_terminated",
    ))

    # ---- Case C: high-dispute sibling, still active -----------------------
    out.append(Merchant(
        id="m90002", forecast_monthly=30000, name="Bookly Cloud", domain="booklycloud.io", country="EE",
        founder="R. Menon", founder_email="admin@booklycloud.io",
        category_claimed="ebooks_publications",
        pitch="Cloud bookshelf and reading progress sync across devices.",
        offering_claimed="reading sync subscription",
        applied_at=_d(240), domain_age_days=31, registrar="Namecheap",
        nameserver="ns.hetzner", site_template="tpl-framer-a",
        terms_hash=_hash("terms", "bookly"),
        payout_iban="EE •••• 8812", payout_branch=ring_branch, payout_holder=ring_holder,
        fulfilment=["email", "telegram"], status="approved", decided_at=_d(238),
        decided_by="analyst.priya", rationale="Approved with conditions: restricted category, requested rights documentation.",
        monthly_volume=38_000, settled_txns=5_100, disputes=168, fraud_reports=41,
        refund_rate=0.11, offering_observed="reading sync subscription",
        observed_category="ebooks_publications", last_observed_at=_d(6),
        truth_bad=True, truth_category="recidivist_ring",
        truth_note="Same beneficial owner as Vellum Reader. Dispute ratio 4.1%.",
        scenario="bookly_active",
    ))

    # ---- Case C: today's applicant, two hops from both --------------------
    out.append(Merchant(
        id="m90003", name="Lumen Labs", domain="lumenlabs.app", country="EE",
        founder="R. Menon", founder_email="hello@lumenlabs.app",
        category_claimed="ai_product",
        pitch="An AI reading companion that summarises and discusses books with you.",
        offering_claimed="AI reading assistant subscription",
        applied_at=_d(1), domain_age_days=11, registrar="Namecheap",
        nameserver=shared_ns, site_template=shared_tpl, terms_hash=shared_terms,
        payout_iban="EE •••• 4471", payout_branch=ring_branch, payout_holder=ring_holder,
        fulfilment=["telegram"], status="pending",
        truth_bad=True, truth_category="recidivist_ring",
        truth_note="Case C. Same operator as Vellum Reader, one account along at the same branch.",
        scenario="case_c",
    ))

    # ---- Case A: the rights case, in the queue today ----------------------
    out.append(Merchant(
        id="m90004", name="Kindle Grove", domain="kindlegrove.com", country="AE",
        founder="T. Abadi", founder_email="founder@kindlegrove.com",
        category_claimed="ebooks_publications",
        pitch="A 40,000-title reading companion. Search, summarise and read anything, $9/month.",
        offering_claimed="catalogue ebook subscription",
        applied_at=_d(2), domain_age_days=23, registrar="Porkbun",
        nameserver="ns.cloudflare", site_template="tpl-next-landing",
        terms_hash=_hash("terms", "kindlegrove"),
        payout_iban="AE •••• 2210", payout_branch="Northbay / Singapore-11",
        payout_holder="KINDLEGROVE FZ LLC", fulfilment=["email", "telegram"],
        status="pending",
        truth_bad=True, truth_category="undisclosed_illegality",
        truth_note="Case A. Catalogue scale with no rights documentation available.",
        scenario="case_a",
    ))

    # ---- Case B: approved honestly, drifted at month five -----------------
    out.append(Merchant(
        id="m90005", forecast_monthly=22000, name="Northwind Notes", domain="northwindnotes.com", country="GB",
        founder="S. Brennan", founder_email="sam@northwindnotes.com",
        category_claimed="ai_product",
        pitch="AI meeting summarisation for B2B sales teams. Records, transcribes, summarises.",
        offering_claimed="meeting summarisation SaaS",
        applied_at=_d(190), domain_age_days=420, registrar="Cloudflare",
        nameserver="ns.cloudflare", site_template="tpl-astro-saas",
        terms_hash=_hash("terms", "northwind"),
        payout_iban="GB •••• 7731", payout_branch="Solent / London-21",
        payout_holder="NORTHWIND NOTES LTD", fulfilment=["email", "github"],
        status="approved", decided_at=_d(189), decided_by="analyst.dan",
        rationale="Approved: clean B2B SaaS, real product, verifiable customers.",
        monthly_volume=27_500, settled_txns=3_900, disputes=96, fraud_reports=18,
        refund_rate=0.14, offering_observed="AI companion app with intimacy tier",
        observed_category="adult_nsfw", last_observed_at=_d(3),
        truth_bad=True, truth_category="product_drift",
        truth_note="Case B. Pivoted at month five into a prohibited category on the same account.",
        scenario="case_b",
    ))

    # ---- Deceptive billing: the highest-probability category --------------
    out.append(Merchant(
        id="m90006", forecast_monthly=40000, name="Quartz Habit", domain="quartzhabit.com", country="US",
        founder="J. Whitfield", founder_email="team@quartzhabit.com",
        category_claimed="saas",
        pitch="Habit tracking with streaks and coaching. 7-day free trial, then $19/month.",
        offering_claimed="habit tracking subscription",
        applied_at=_d(150), domain_age_days=200, registrar="GoDaddy",
        nameserver="ns.vercel", site_template="tpl-tailkit",
        terms_hash=_hash("terms", "quartz"),
        payout_iban="US •••• 5540", payout_branch="Pinegrove / Toronto-09",
        payout_holder="QUARTZ HABIT INC", fulfilment=["email"],
        status="approved", decided_at=_d(149), decided_by="analyst.dan",
        rationale="Approved: ordinary consumer SaaS.",
        monthly_volume=44_000, settled_txns=7_200, disputes=214, fraud_reports=31,
        refund_rate=0.19, offering_observed="habit tracking subscription",
        observed_category="saas", last_observed_at=_d(4),
        truth_bad=True, truth_category="deceptive_billing",
        truth_note="Cancellation requires email to support; trial converts silently at $19.",
        scenario="deceptive_billing",
    ))

    # ---- Failing: honest merchant, large prepaid obligation ---------------
    out.append(Merchant(
        id="m90007", forecast_monthly=60000, name="Harbor Stack", domain="harborstack.dev", country="DE",
        founder="M. Bergman", founder_email="m@harborstack.dev",
        category_claimed="saas",
        pitch="Infrastructure monitoring for small teams. Annual plans discounted 30%.",
        offering_claimed="monitoring subscription",
        applied_at=_d(400), domain_age_days=890, registrar="Hover",
        nameserver="ns.hetzner", site_template="tpl-nuxt-studio",
        terms_hash=_hash("terms", "harbor"),
        payout_iban="DE •••• 1180", payout_branch="Verity / Amsterdam-05",
        payout_holder="HARBOR STACK GMBH", fulfilment=["email", "github"],
        status="approved", decided_at=_d(399), decided_by="analyst.priya",
        rationale="Approved: established, clean, real customers.",
        monthly_volume=52_000, settled_txns=1_240, disputes=6, fraud_reports=1,
        refund_rate=0.02, prepaid_balance=486_000, annual_plan_share=0.71,
        offering_observed="monitoring subscription", observed_category="saas",
        last_observed_at=_d(5),
        truth_bad=True, truth_category="insolvency",
        truth_note="No fraud. Volume down 41% over two quarters against a $486k prepaid book.",
        scenario="insolvency",
    ))

    # ---- Being attacked: account takeover, payout redirected --------------
    out.append(Merchant(
        id="m90008", forecast_monthly=28000, name="Ember Desk", domain="emberdesk.io", country="CA",
        founder="A. Novak", founder_email="a@emberdesk.io",
        category_claimed="saas",
        pitch="Shared inbox and helpdesk for small support teams.",
        offering_claimed="helpdesk subscription",
        applied_at=_d(510), domain_age_days=1120, registrar="Namecheap",
        nameserver="ns.route53", site_template="tpl-astro-saas",
        terms_hash=_hash("terms", "ember"),
        payout_iban="CA •••• 9902", payout_branch="Halcyon / Riga-03",
        payout_holder="E DESK SERVICES", fulfilment=["email"],
        status="approved", decided_at=_d(509), decided_by="analyst.dan",
        rationale="Approved: ordinary B2B SaaS.",
        monthly_volume=31_000, settled_txns=980, disputes=4, fraud_reports=0,
        refund_rate=0.01, offering_observed="helpdesk subscription",
        observed_category="saas", last_observed_at=_d(2),
        payout_changed_at=_d(2), login_anomaly=True,
        truth_bad=True, truth_category="account_takeover",
        truth_note="Merchant is the victim. Payout bank changed two days ago from a new country.",
        scenario="account_takeover",
    ))

    # ---- Being attacked: card testing through the checkout ----------------
    out.append(Merchant(
        id="m90009", forecast_monthly=11000, name="Pinebase Kit", domain="pinebasekit.com", country="PL",
        founder="K. Kowalski", founder_email="k@pinebasekit.com",
        category_claimed="templates_plugins_apps",
        pitch="A component kit for React and Tailwind. One-time $29 licence.",
        offering_claimed="component kit licence",
        applied_at=_d(220), domain_age_days=640, registrar="Gandi",
        nameserver="ns.netlify", site_template="tpl-tailkit",
        terms_hash=_hash("terms", "pinebase"),
        payout_iban="PL •••• 3345", payout_branch="Cresta / Lisbon-02",
        payout_holder="PINEBASE SP Z OO", fulfilment=["email", "github"],
        status="approved", decided_at=_d(219), decided_by="analyst.priya",
        rationale="Approved: clean one-time digital licence.",
        monthly_volume=9_400, settled_txns=6_100, disputes=22, fraud_reports=280,
        refund_rate=0.03, micro_txn_share=0.63,
        offering_observed="component kit licence", observed_category="templates_plugins_apps",
        last_observed_at=_d(7),
        truth_bad=True, truth_category="card_testing",
        truth_note="Merchant is the victim. 63% of transactions are sub-$2 with no bot protection.",
        scenario="card_testing",
    ))

    # ---- Deceiving: transaction laundering, invisible on the site ---------
    out.append(Merchant(
        id="m90010", forecast_monthly=6000, name="Sable Sync", domain="sablesync.co", country="SG",
        founder="D. Aoki", founder_email="ops@sablesync.co",
        category_claimed="saas",
        pitch="File sync and backup for small studios. $12/month.",
        offering_claimed="file sync subscription",
        applied_at=_d(95), domain_age_days=70, registrar="Porkbun",
        nameserver="ns.digitalocean", site_template="tpl-plainhtml",
        terms_hash=_hash("terms", "sable"),
        payout_iban="SG •••• 6677", payout_branch="Northbay / Singapore-11",
        payout_holder="SABLE SYNC PTE", fulfilment=["email"],
        status="approved", decided_at=_d(94), decided_by="analyst.dan",
        rationale="Approved: small SaaS, forecast $6k/month.",
        monthly_volume=214_000, settled_txns=4_300, disputes=131, fraud_reports=58,
        refund_rate=0.08, offering_observed="file sync subscription",
        observed_category="saas", last_observed_at=_d(9),
        truth_bad=True, truth_category="transaction_laundering",
        truth_note="Processing 35x the underwritten forecast on a four-page site.",
        scenario="transaction_laundering",
    ))

    # ---- Two clean applicants in today's queue, to prove we approve -------
    out.append(Merchant(
        id="m90011", name="Thistle Forge", domain="thistleforge.dev", country="IN",
        founder="A. Iyer", founder_email="arun@thistleforge.dev",
        category_claimed="saas",
        pitch="CI pipeline insights for small engineering teams. $29/month per project.",
        offering_claimed="CI analytics subscription",
        applied_at=_d(1), domain_age_days=310, registrar="Cloudflare",
        nameserver="ns.cloudflare", site_template="tpl-astro-saas",
        terms_hash=_hash("terms", "thistle"),
        payout_iban="IN •••• 4408", payout_branch="Ardent / Dublin-07",
        payout_holder="THISTLE FORGE PVT LTD", fulfilment=["email", "github"],
        status="pending", scenario="clean_a",
    ))
    out.append(Merchant(
        id="m90012", name="Marlow Type", domain="marlowtype.com", country="NL",
        founder="L. Lindqvist", founder_email="lars@marlowtype.com",
        category_claimed="digital_goods",
        pitch="An original variable typeface family sold as a one-time licence.",
        offering_claimed="font licence download",
        applied_at=_d(2), domain_age_days=95, registrar="Gandi",
        nameserver="ns.netlify", site_template="tpl-framer-a",
        terms_hash=_hash("terms", "marlow"),
        payout_iban="NL •••• 7712", payout_branch="Verity / Amsterdam-05",
        payout_holder="MARLOW TYPE BV", fulfilment=["email"],
        status="pending", scenario="clean_b",
    ))

    # ---- Hours mismatch: claimed university courses, night-heavy volume --
    out.append(Merchant(
        id="m90020", forecast_monthly=16000, name="Nightwell Academy",
        domain="nightwell.academy", country="IN",
        founder="P. Sharma", founder_email="priya@nightwell.academy",
        category_claimed="ebooks_publications",
        pitch="Exam prep and recorded lectures in partnership with universities. "
              "Sold to students through campus tie-ups.",
        offering_claimed="university exam prep courses",
        applied_at=_d(95), domain_age_days=210, registrar="GoDaddy",
        nameserver="ns.godaddy", site_template="tpl-next-landing",
        terms_hash=_hash("terms", "nightwell"),
        payout_iban="IN •••• 6621", payout_branch="Ardent / Dublin-07",
        payout_holder="NIGHTWELL ACADEMY LLP",
        fulfilment=["telegram", "email"],
        status="approved", decided_at=_d(93), decided_by="analyst.dan",
        rationale="Approved: edtech, campus partnerships claimed.",
        monthly_volume=19_400, settled_txns=2_860, disputes=22, fraud_reports=4,
        refund_rate=0.06, offering_observed="university exam prep courses",
        observed_category="ebooks_publications", last_observed_at=_d(1),
        signup_category="edtech", tax_category="edtech",
        pricing_type="one_time", price_usd=49.0, entitlements=["telegram", "files"],
        website="https://nightwell.academy", entity_type="registered",
        night_txn_share=0.78,
        truth_bad=True, truth_category="undisclosed_illegality",
        truth_note="Claimed university daytime sales; 78% of volume lands 22:00–06:00 IST.",
        scenario="night_hours",
    ))
    return out


# --------------------------------------------------------------------------
def _background(rng: random.Random, n: int) -> list[Merchant]:
    """The ordinary population the planted cases have to hide inside."""
    out: list[Merchant] = []
    used: set[str] = set()
    for i in range(n):
        style = rng.random()
        if style < 0.45:
            base = f"{rng.choice(_PRE)} {rng.choice(_SUF)}"
        elif style < 0.8:
            base = f"{rng.choice(_PRE)}{rng.choice(_JOIN)}"
        else:
            base = f"{rng.choice(_PRE)}{rng.choice(_JOIN)} {rng.choice(_SUF)}"
        name = base
        bump = 1
        while name in used:
            bump += 1
            name = f"{base} {bump}"
        used.add(name)
        slug = name.lower().replace(" ", "")
        cat, pitch_t, offering = rng.choice(_LEGIT)
        founder = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
        applied = rng.randint(3, 545)
        m = Merchant(
            id=_mk_id(i + 1), name=name, domain=f"{slug}.{rng.choice(['com','io','dev','app','co'])}",
            country=rng.choice(_COUNTRY), founder=founder,
            founder_email=f"{rng.choice(['hi','team','hello','founder'])}@{slug}.com",
            category_claimed=cat, pitch=pitch_t.format(x=rng.choice(_X)),
            offering_claimed=offering, applied_at=_d(applied),
            domain_age_days=rng.choice([9, 21, 45, 90, 180, 365, 700, 1200]),
            registrar=rng.choice(_REGISTRAR), nameserver=rng.choice(_NS),
            site_template=rng.choice(_TEMPLATE),
            terms_hash=_hash("terms", slug), payout_iban=f"{rng.choice(_COUNTRY)} •••• {rng.randint(1000,9999)}",
            payout_branch=rng.choice(_BANK), payout_holder=name.upper(),
            fulfilment=list(rng.choice(_CHANNELS)),
        )
        r = rng.random()
        if applied <= 4 and rng.random() < 0.55:
            m.status = "pending"
            out.append(m)
            continue
        if r < 1 - config.APPROVAL_RATE:
            m.status = "declined"
            m.decided_at = _d(max(1, applied - 1))
            m.decided_by = rng.choice(["analyst.priya", "analyst.dan"])
            m.rationale = rng.choice([
                "Declined: prohibited category on review of the live site.",
                "Declined: could not verify the business or its operator.",
                "Declined: product did not match the described offering.",
                "Declined: thin product, no demonstrable deliverable.",
            ])
        else:
            m.status = "approved"
            m.decided_at = _d(max(1, applied - 1))
            m.decided_by = rng.choice(["analyst.priya", "analyst.dan"])
            m.rationale = rng.choice([
                "Approved: clear digital product, verifiable operator.",
                "Approved: ordinary SaaS, real customers, clean history.",
                "Approved with conditions: restricted category, disclaimers requested.",
                "Approved: one-time digital licence, low dispute profile.",
            ])
            m.monthly_volume = round(rng.lognormvariate(7.92, 1.0), 2)
            m.settled_txns = max(20, int(m.monthly_volume / rng.uniform(9, 90)))
            m.disputes = int(m.settled_txns * rng.uniform(0.0005, 0.0042))
            m.fraud_reports = int(m.settled_txns * rng.uniform(0.0, 0.0011))
            m.refund_rate = round(rng.uniform(0.005, 0.06), 4)
            m.annual_plan_share = round(rng.uniform(0.0, 0.60), 3)
            m.prepaid_balance = round(m.monthly_volume * 12 * m.annual_plan_share * 0.5, 2)
            m.forecast_monthly = round(m.monthly_volume * rng.uniform(0.7, 1.4), 2)
            m.offering_observed = m.offering_claimed
            m.observed_category = m.category_claimed
            m.last_observed_at = _d(rng.randint(1, 30))
        out.append(m)

    # authored ground truth for the background: a small number went bad
    approved = [m for m in out if m.status == "approved"]
    n_bad = max(0, int(len(approved) * config.CONFIRMED_BAD_RATE) - 8)
    cats = list(config.LOSS_DISTRIBUTION)
    weights = [config.LOSS_DISTRIBUTION[c] for c in cats]
    ring_seeds: list[Merchant] = []
    catalogue_pitches = [
        "A {n:,}-title reading library. Search, summarise and read anything, $9/month.",
        "Unlimited access to a catalogue of {n:,} books and audiobooks.",
        "An archive of {n:,} titles, papers and manuals in one searchable app.",
        "Every textbook you need -- {n:,} titles, one subscription.",
    ]
    for m in rng.sample(approved, n_bad):
        cat = rng.choices(cats, weights=weights, k=1)[0]
        m.truth_bad = True
        m.truth_category = cat
        m.truth_note = f"Confirmed {cat.replace('_', ' ')} after approval."
        m.status = "terminated"

        # The observable features have to match the category, or the corpus is
        # incoherent: a CI-analytics product cannot be an ebook rights case.
        if cat == "undisclosed_illegality":
            m.category_claimed = "ebooks_publications"
            m.pitch = rng.choice(catalogue_pitches).format(n=rng.randrange(8000, 90000, 1000))
            m.offering_claimed = "catalogue ebook subscription"
            m.observed_category = "ebooks_publications"
            m.offering_observed = m.offering_claimed
            if "telegram" not in m.fulfilment:
                m.fulfilment = m.fulfilment + ["telegram"]
        elif cat == "recidivist_ring":
            if ring_seeds:
                seed = rng.choice(ring_seeds)
                m.payout_holder = seed.payout_holder
                m.terms_hash = seed.terms_hash
                m.founder = seed.founder
            else:
                ring_seeds.append(m)
            m.domain_age_days = rng.choice([9, 14, 21])
        elif cat == "bust_out":
            m.domain_age_days = rng.choice([9, 12, 18, 25])
            if "telegram" not in m.fulfilment:
                m.fulfilment = m.fulfilment + ["telegram"]
            m.monthly_volume *= rng.uniform(3, 8)
            m.disputes = int(m.settled_txns * rng.uniform(0.03, 0.07))
        elif cat in ("deceptive_billing", "product_drift"):
            m.disputes = int(m.settled_txns * rng.uniform(0.02, 0.05))
            m.refund_rate = round(rng.uniform(0.17, 0.32), 4)
        if cat == "product_drift":
            m.observed_category = rng.choice(["adult_nsfw", "gambling", "crypto_nft"])
            m.offering_observed = "an offering unrelated to the underwritten product"
            # Roughly half have not been caught yet -- undetected drift sitting
            # in the live portfolio is exactly what the monitor exists to find.
            if rng.random() < 0.55:
                m.status = "approved"
                m.last_observed_at = _d(rng.randint(1, 12))
        if cat == "transaction_laundering":
            m.monthly_volume *= rng.uniform(8, 30)
        if cat == "insolvency":
            m.prepaid_balance = round(m.monthly_volume * rng.uniform(6, 14), 2)
        if cat == "card_testing":
            m.fraud_reports = int(m.settled_txns * rng.uniform(0.03, 0.09))
            m.micro_txn_share = round(rng.uniform(0.4, 0.8), 3)
        if cat == "account_takeover":
            m.payout_changed_at = _d(rng.randint(1, 40))
            m.login_anomaly = True
        if not ring_seeds:
            ring_seeds.append(m)
    return out


def build() -> list[Merchant]:
    """Return the full corpus: background population, authored cases, real customers."""
    rng = random.Random(SEED)
    merchants = _background(rng, config.LIFETIME_APPLICATIONS)
    merchants.extend(_scenarios())
    merchants.extend(_real_customers())

    # A real, named business must never sit next to an adverse finding. The
    # background population is randomised, so this is an assertion rather than
    # a convention -- a reseed that swept a real name into the bad sample would
    # otherwise ship silently.
    for m in merchants:
        if m.real or m.name in REAL_CUSTOMER_NAMES:
            assert not m.truth_bad, f"real customer {m.name} marked adverse"
            assert m.truth_category is None, f"real customer {m.name} has a bad category"
            assert m.status == "approved", f"real customer {m.name} not approved"
    return merchants


def summary(merchants: list[Merchant]) -> dict:
    approved = [m for m in merchants if m.status in ("approved", "terminated")]
    active = [m for m in merchants if m.status == "approved"]
    txns = sum(m.settled_txns for m in active)
    events = sum(m.disputes + m.fraud_reports for m in active)
    return {
        "total_applications": len(merchants),
        "pending": sum(1 for m in merchants if m.status == "pending"),
        "approved": len(active),
        "declined": sum(1 for m in merchants if m.status == "declined"),
        "terminated": sum(1 for m in merchants if m.status == "terminated"),
        "approval_rate": round(len(approved) / len(merchants), 4),
        "confirmed_bad": sum(1 for m in merchants if m.truth_bad),
        "portfolio_vamp": round(events / txns, 6) if txns else 0.0,
        "monthly_volume": round(sum(m.monthly_volume for m in active), 2),
        "prepaid_exposure": round(sum(m.prepaid_balance for m in active), 2),
    }
