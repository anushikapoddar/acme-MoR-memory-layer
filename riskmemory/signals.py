"""Signal detectors, one family per risk posture (section 2.1).

Each detector returns a Signal carrying a *likelihood ratio*: how much more
often this observation appears among merchants that went bad than among those
that did not. Likelihood ratios compose multiplicatively in odds space, which
is what lets the case brief show its arithmetic instead of a bare score.

Detectors may only read what a reviewer could read. ``truth_bad`` and
``truth_category`` are authored ground truth and never appear here.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, asdict
from typing import Optional

from . import config
from .corpus import Merchant, TODAY
from .graph import ContextGraph, Related

@dataclass
class Signal:
    id: str
    posture: str
    category: str
    title: str
    detail: str
    lr: float                 # likelihood ratio
    evidence: list[str]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["posture_label"] = config.POSTURES.get(self.posture, self.posture)
        return d


def _days_since(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    return (TODAY - _dt.date.fromisoformat(iso)).days


# ---------------------------------------------------------------- deceiving
def detect_deceiving(m: Merchant, graph: ContextGraph,
                     by_id: dict[str, Merchant]) -> list[Signal]:
    out: list[Signal] = []

    related = graph.related_merchants(m.id)
    bad_links = []
    for rel in related:
        other = by_id.get(rel.target)
        if other is None or other.id == m.id:
            continue
        if other.status == "terminated" or other.vamp_ratio() > config.VAMP_MERCHANT_EXCESSIVE:
            bad_links.append((rel, other))

    for rel, other in bad_links[:4]:
        state = ("terminated" if other.status == "terminated"
                 else f"dispute ratio {other.vamp_ratio()*100:.1f}%")
        routes = "; ".join(p.describe() for p in rel.paths)
        lr = 9.0 if other.status == "terminated" else 4.5
        lr *= (1.0 + 0.45 * (rel.corroboration - 1))
        out.append(Signal(
            id=f"graph_link:{other.id}", posture="deceiving",
            category="recidivist_ring",
            title=f"Linked to {other.name} ({state})",
            detail=(f"{rel.corroboration} independent route"
                    f"{'s' if rel.corroboration > 1 else ''} connect this applicant to "
                    f"a merchant we have already judged."),
            lr=round(min(lr, 40.0), 2), evidence=[routes],
        ))

    # NOTE: there is deliberately no hardcoded "catalogue implies piracy" rule.
    # That insight is not policy -- it is something the platform learns from the
    # Vellum Reader rights claim, arrives as a distilled semantic memory, and
    # only takes effect once it has passed the replay gate. Hardcoding it here
    # would pre-empt the very loop this system exists to demonstrate.

    if m.forecast_monthly > 0 and m.monthly_volume > 0:
        ratio = m.monthly_volume / m.forecast_monthly
        if ratio >= 4:
            out.append(Signal(
                id="volume_vs_forecast", posture="deceiving",
                category="transaction_laundering",
                title=f"Processing {ratio:.0f}x the underwritten forecast",
                detail=("Volume far above forecast on an unchanged product is the "
                        "classic signature of another business being processed "
                        "through this account."),
                lr=round(min(3.0 + ratio * 0.35, 22.0), 2),
                evidence=[f"forecast ${m.forecast_monthly:,.0f}/mo, "
                          f"actual ${m.monthly_volume:,.0f}/mo"],
            ))

    if m.domain_age_days <= 30 and "telegram" in m.fulfilment:
        out.append(Signal(
            id="young_domain_telegram", posture="deceiving",
            category="bust_out",
            title="Domain under 30 days old, fulfilment via Telegram",
            detail=("Neither is disqualifying alone -- most indie founders start "
                    "somewhere -- but together they are over-represented among "
                    "merchants that vanish."),
            lr=2.6, evidence=[f"domain {m.domain_age_days}d old",
                              f"fulfilment: {', '.join(m.fulfilment)}"],
        ))
    return out


# ---------------------------------------------------------------- drifting
def detect_drifting(m: Merchant, graph: ContextGraph,
                    by_id: dict[str, Merchant]) -> list[Signal]:
    out: list[Signal] = []
    if m.observed_category and m.observed_category != m.category_claimed:
        claimed_ok = m.category_claimed in config.POLICY_ACCEPTED
        now_bad = m.observed_category in config.POLICY_PROHIBITED
        lr = 26.0 if now_bad else 5.0
        out.append(Signal(
            id="category_drift", posture="drifting", category="product_drift",
            title=("Now selling a prohibited category" if now_bad
                   else "Observed offering has moved away from what we underwrote"),
            detail=(f"Underwritten as '{m.category_claimed}'"
                    f"{' (accepted)' if claimed_ok else ''}; observed as "
                    f"'{m.observed_category}'"
                    f"{' (prohibited)' if now_bad else ''}."),
            lr=lr,
            evidence=[f"claims_to_sell: {m.offering_claimed}",
                      f"observed_selling: {m.offering_observed}",
                      f"last observed {m.last_observed_at}"],
        ))

    if m.refund_rate >= 0.15 and m.settled_txns > 200:
        out.append(Signal(
            id="deceptive_billing", posture="drifting", category="deceptive_billing",
            title=f"Refund rate {m.refund_rate*100:.0f}% on a subscription product",
            detail=("Sustained high refunds on recurring billing is the signature of "
                    "a cancellation flow customers cannot find. The product may be "
                    "entirely real -- the billing practice is the exposure."),
            lr=round(3.0 + (m.refund_rate - 0.15) * 30, 2),
            evidence=[f"refund rate {m.refund_rate*100:.1f}%",
                      f"{m.disputes} disputes on {m.settled_txns:,} settled"],
        ))

    if _looks_like_education(m) and m.night_txn_share >= 0.55 and m.settled_txns >= 40:
        _, abbr, _, _ = config.local_night_window(m.country)
        night = config.local_night_label(m.country)
        out.append(Signal(
            id="hours_mismatch", posture="drifting", category="product_drift",
            title=f"{m.night_txn_share*100:.0f}% of volume lands at night ({abbr})",
            detail=("They underwrote as education sold through universities or schools. "
                    "Campus-tied products concentrate in daytime in the merchant's "
                    f"own timezone. Night is {night} — not UTC, not another market's "
                    "evening. Night-heavy volume is the pattern of a different buyer, "
                    "and often a different product."),
            lr=round(4.0 + m.night_txn_share * 8.0, 2),
            evidence=[f"night share {m.night_txn_share*100:.0f}% of {m.settled_txns:,} settled",
                      f"local night window: {night}",
                      f"claimed: {m.offering_claimed}"],
        ))
    return out


# ---------------------------------------------------------------- failing
def detect_failing(m: Merchant, graph: ContextGraph,
                   by_id: dict[str, Merchant], portfolio_volume: float = 0.0) -> list[Signal]:
    out: list[Signal] = []
    if m.prepaid_balance > 0 and m.monthly_volume > 0:
        months = m.prepaid_balance / m.monthly_volume
        if months >= 5:
            out.append(Signal(
                id="prepaid_exposure", posture="failing", category="insolvency",
                title=f"${m.prepaid_balance:,.0f} of prepaid service outstanding",
                detail=("Not fraud. If this merchant fails, Acme inherits the refunds "
                        f"on {months:.1f} months of service already paid for."),
                lr=round(min(1.6 + months * 0.16, 6.5), 2),
                evidence=[f"prepaid balance ${m.prepaid_balance:,.0f}",
                          f"annual plans {m.annual_plan_share*100:.0f}% of volume"],
            ))
    if portfolio_volume > 0 and m.monthly_volume / portfolio_volume > 0.02:
        out.append(Signal(
            id="concentration", posture="failing", category="concentration",
            title=f"{m.monthly_volume/portfolio_volume*100:.1f}% of portfolio volume",
            detail="Single-merchant concentration: their disputes move our ratio.",
            lr=1.8, evidence=[f"${m.monthly_volume:,.0f}/mo"],
        ))
    return out


# ---------------------------------------------------------------- attacked
def detect_attacked(m: Merchant, graph: ContextGraph,
                    by_id: dict[str, Merchant]) -> list[Signal]:
    out: list[Signal] = []
    days = _days_since(m.payout_changed_at)
    if days is not None and days <= 30:
        out.append(Signal(
            id="payout_change", posture="attacked", category="account_takeover",
            title=f"Payout details changed {days} day{'s' if days != 1 else ''} ago",
            detail=("Assessing the business tells you nothing here. The business is "
                    "fine; the account may not be."
                    + (" Login pattern is also anomalous." if m.login_anomaly else "")),
            lr=14.0 if m.login_anomaly else 4.0,
            evidence=[f"payout changed {m.payout_changed_at}",
                      f"login anomaly: {m.login_anomaly}"],
        ))
    if m.settled_txns > 200:
        fraud_ratio = m.fraud_reports / m.settled_txns
        if fraud_ratio > 0.02 and m.micro_txn_share > 0.3:
            out.append(Signal(
                id="card_testing", posture="attacked", category="card_testing",
                title=f"{m.micro_txn_share*100:.0f}% micro-transactions, "
                      f"{fraud_ratio*100:.1f}% fraud-reported",
                detail=("Their checkout is being used to test stolen cards. The "
                        "merchant is a victim, but the events land in our VAMP ratio."),
                lr=round(min(4.0 + fraud_ratio * 120, 18.0), 2),
                evidence=[f"{m.fraud_reports} fraud reports on {m.settled_txns:,} settled",
                          f"micro-transaction share {m.micro_txn_share*100:.0f}%"],
            ))
    return out


def _render_predicate(pred: dict) -> str:
    parts = []
    for c in pred.get("all", []):
        op = c["op"]
        if op == "ratio>=":
            parts.append(f"{c['field']} / {c.get('over')} >= {c['value']}")
        else:
            parts.append(f"{c['field']} {op} {c['value']}")
    return " and ".join(parts)


def profile_text(m: Merchant) -> str:
    """The text a semantic memory is matched against."""
    return " ".join([m.pitch, m.category_claimed, m.offering_claimed,
                     m.observed_category or "", " ".join(m.fulfilment)])


def _risk_themes(m: Merchant) -> set[str]:
    from .websearch import match_themes
    seen: set[str] = set()
    blob = " ".join([
        m.name or "",
        getattr(m, "pitch", "") or "",
        getattr(m, "offering_claimed", "") or "",
        getattr(m, "category_claimed", "") or "",
    ])
    for hit in match_themes(blob):
        seen.add(hit["theme"])
    report = getattr(m, "web_report", None) or {}
    for hit in report.get("themes") or []:
        theme = hit.get("theme")
        if theme:
            seen.add(theme)
    return seen


def memory_trigger(m: Merchant) -> str:
    """Retrieval key for analyst episodic memory and session precedent.

    Pitch alone is too brittle — “casino king” and “gambler ninjas” with
    different wording never match. Fold in the name and any gambling / adult /
    crypto themes surfaced from copy or the open-web lookup so a decline in
    the same vertical heats the next applicant even when the prose differs.
    """
    parts = [profile_text(m), m.name or ""]
    for theme in sorted(_risk_themes(m)):
        parts.append(theme)
    return " ".join(p for p in parts if p)


def detect_memory(m: Merchant, store, threshold: float = 0.13) -> list[Signal]:
    """Signals contributed by distilled semantic memory.

    This is the path by which a confirmed incident changes future decisions.
    Only *promoted* memories are consulted -- a candidate distilled from an
    incident has no effect until it passes the replay gate.
    """
    if store is None:
        return []
    from .memory import evaluate_predicate

    out: list[Signal] = []
    seen: set[str] = set()

    # 1) behavioural patterns, matched by structured predicate
    for mem in store.active("semantic", promoted_only=True):
        if not mem.predicate or mem.polarity != "adverse":
            continue
        if evaluate_predicate(mem.predicate, m):
            seen.add(mem.id)
            out.append(Signal(
                id=f"memory:{mem.id}", posture="memory",
                category=mem.category or "precedent",
                title="Matches a distilled behavioural pattern",
                detail=mem.text,
                lr=round(1.0 + mem.confidence * 11.0, 2),
                evidence=[f"predicate: {_render_predicate(mem.predicate)}",
                          f"confidence {mem.confidence:.2f}", f"source: {mem.source}"],
            ))

    # 2) content patterns, matched by text similarity
    hits = store.search(profile_text(m), limit=4, kind="semantic", promoted_only=True)
    for mem, sim in hits:
        if sim < threshold or mem.polarity != "adverse" or mem.id in seen:
            continue
        if mem.predicate:
            continue
        # Scaled by match strength, so a marginal match contributes
        # marginally rather than snapping to full weight.
        lr = 1.0 + (mem.confidence * 12.0) * min(sim / 0.35, 1.0)
        out.append(Signal(
            id=f"memory:{mem.id}", posture="memory",
            category=mem.category or "precedent",
            title="Matches a distilled pattern in memory",
            detail=mem.text,
            lr=round(lr, 2),
            evidence=[f"similarity {sim:.2f}", f"confidence {mem.confidence:.2f}",
                      f"source: {mem.source}"],
        ))

    # 3) analyst decisions this session — episodic, not distilled. A decline
    # of Nightline Casino should heat the next similar casino, not sit inert
    # in the memory list. Seed case-file notes are excluded (source is not
    # an analyst); the merchant is not scored against its own decision.
    hits = store.search(memory_trigger(m), limit=4, kind="episodic", promoted_only=True)
    themes = _risk_themes(m)
    for mem, sim in hits:
        if mem.id in seen or mem.subject == m.id:
            continue
        if mem.polarity != "adverse":
            continue
        if not str(mem.source or "").startswith("analyst"):
            continue
        theme_match = bool(mem.category and mem.category in themes)
        floor = 0.10 if theme_match else config.PRECEDENT_MIN_SIMILARITY
        if sim < floor:
            continue
        seen.add(mem.id)
        lr = 1.0 + (mem.confidence * 12.0) * min(sim / 0.35, 1.0)
        out.append(Signal(
            id=f"memory:{mem.id}", posture="memory",
            category=mem.category or "precedent",
            title="Matches a prior analyst decline",
            detail=mem.text,
            lr=round(lr, 2),
            evidence=[f"similarity {sim:.2f}", f"confidence {mem.confidence:.2f}",
                      f"source: {mem.source}"],
        ))
    return out


def _looks_like_education(m: Merchant) -> bool:
    blob = " ".join([
        m.pitch or "", m.offering_claimed or "",
        getattr(m, "signup_category", "") or "",
        getattr(m, "tax_category", "") or "",
        m.category_claimed or "",
    ]).lower()
    keys = ("edtech", "university", "universities", "school", "campus",
            "exam prep", "lecture", "course", "curriculum", "student")
    return any(k in blob for k in keys)


_THIN_LAUNCH = (
    "coming soon", "waitlist", "launching soon", "under construction",
    "placeholder", "teaser", "pre-launch", "join the waitlist",
)

_SERVICE_COPY = (
    "consulting", "freelance", "coaching", "custom design",
    "done for you", "done-for-you", "hourly", "we will build",
)

_PHYSICAL_COPY = ("t-shirt", "shipped to you", "merchandise", "mug", "supplement")
_GAMING_COPY = ("in-game currency", "game credits", "steam key", "roblox", "loot box")

#: Markets named in copy. Used to catch "Indian entity, US-night students"
#: at signup — the hours pattern before any volume exists.
_MARKET_CUES: list[tuple[str, tuple[str, ...]]] = [
    ("US", ("united states", "u.s.", "us high school", "us student",
            "american universit", "eastern time", "pacific time",
            "pm est", "pm pst", "8pm est", "9pm est", "est live",
            "ap exam", "sat prep")),
    ("GB", ("united kingdom", "gcse", "a-level", "uk student",
            "british universit")),
    ("IN", ("cbse", "jee", "neet", "indian universit", "ist live")),
    ("AE", ("uae student", "dubai universit")),
]
_LIVE_TZ = (
    "live class", "live classes", "live lecture", "live session",
    "timezone", "time zone", "pm est", "pm pst", "pm gmt", "pm ist",
)


def _named_markets(blob: str) -> list[str]:
    found: list[str] = []
    for iso, cues in _MARKET_CUES:
        if any(c in blob for c in cues):
            found.append(iso)
    return found


def detect_onboarding(m: Merchant) -> list[Signal]:
    """Signals from Acme's real signup + add-product packet.

    Only fires when the merchant carries a signup_category — that is the
    public form packet, not the synthetic corpus's internal taxonomy.
    """
    out: list[Signal] = []
    signup = getattr(m, "signup_category", None)
    if not signup:
        return out
    tier, mapped = config.map_signup_category(signup)
    if tier == "prohibited":
        out.append(Signal(
            id=f"policy:{mapped}", posture="deceiving", category=mapped,
            title="Signup category is on the Merchant Acceptance prohibited list",
            detail=("Acme's own form already labels this unsupported: physical goods, "
                    "manual services, gaming, marketplaces, and financial products "
                    "cannot be onboarded. The engine does not soften that into a maybe."),
            lr=28.0,
            evidence=[f"signup category: {signup}", f"policy: {mapped}"],
        ))
    elif tier == "restricted":
        out.append(Signal(
            id=f"policy:{mapped}", posture="deceiving", category=mapped,
            title="Category needs enhanced review under the acceptance policy",
            detail="Not an auto-decline, but not an auto-approve either.",
            lr=3.2,
            evidence=[f"signup category: {signup}"],
        ))

    geo = config.country_eligibility(m.country)
    if geo == "restricted":
        out.append(Signal(
            id="geo:restricted", posture="deceiving", category="undisclosed_illegality",
            title=f"Merchant country {m.country} is not on the accepted countries list",
            detail=("Eligibility is the country that issued the government ID, not tax "
                    "residence. If it is not on the accepted list, we cannot onboard."),
            lr=22.0,
            evidence=[f"country: {m.country}"],
        ))
    elif geo == "grandfathered":
        out.append(Signal(
            id="geo:grandfathered", posture="deceiving", category="undisclosed_illegality",
            title=f"{m.country} is grandfathered — new onboarding is not accepted",
            detail="Existing accounts may continue under monitoring; new merchants here are blocked.",
            lr=12.0,
            evidence=[f"country: {m.country}"],
        ))

    blob = f"{m.pitch} {m.offering_claimed} {m.name}".lower()
    signup_tier, _ = config.map_signup_category(signup)
    if signup_tier == "accepted":
        if any(w in blob for w in _SERVICE_COPY):
            out.append(Signal(
                id="mismatch:services", posture="deceiving",
                category="manual_digital_services",
                title="Copy describes a manual service while the category is digital",
                detail="Misclassifying services as SaaS is a listed policy-breach pattern.",
                lr=14.0, evidence=["matched service language in description"],
            ))
        if any(w in blob for w in _PHYSICAL_COPY):
            out.append(Signal(
                id="mismatch:physical", posture="deceiving", category="physical_goods",
                title="Copy describes physical goods on a digital category",
                lr=18.0, evidence=["matched physical-goods language"],
            ))
        if any(w in blob for w in _GAMING_COPY):
            out.append(Signal(
                id="mismatch:gaming", posture="deceiving",
                category="gaming_virtual_goods",
                title="Copy describes gaming / virtual goods on a digital category",
                lr=18.0, evidence=["matched gaming language"],
            ))

    if any(p in blob for p in _THIN_LAUNCH):
        out.append(Signal(
            id="thin:prelaunch", posture="deceiving", category="low_value_digital",
            title="Product copy reads as pre-launch or waitlist",
            detail="Placeholder and coming-soon offerings are unsupported: no immediate usable value.",
            lr=9.5, evidence=["matched pre-launch language"],
        ))

    fulfil = set(m.fulfilment or []) | set(getattr(m, "entitlements", None) or [])
    if _looks_like_education(m) and ("telegram" in fulfil or "discord" in fulfil):
        out.append(Signal(
            id="fulfil:chat_edtech", posture="deceiving", category="low_value_digital",
            title="Education product delivers via Telegram or Discord",
            detail=("Campus courses can use chat, but gated Telegram/Discord is also "
                    "how undisclosed catalogues get fulfilled. Stacks with hours and graph."),
            lr=3.4,
            evidence=[f"channels: {', '.join(sorted(fulfil))}"],
        ))

    # Early patterns: visible on the signup packet, no volume required.
    foreign = [iso for iso in _named_markets(blob) if iso != (m.country or "").upper()]
    live = any(p in blob for p in _LIVE_TZ)
    if foreign and (_looks_like_education(m) or live):
        night = config.local_night_label(m.country)
        out.append(Signal(
            id="audience:tz", posture="deceiving", category="product_drift",
            title="Copy sells into a market whose day is this merchant's night",
            detail=("The ID-issuing country sets local night hours "
                    f"({night}). The pitch names {', '.join(foreign)} students or "
                    "live classes. That is the Nightwell pattern at signup: you do "
                    "not need settled volume to see that the buyer is not a local campus."),
            lr=6.5,
            evidence=[f"merchant country {m.country} night is {night}",
                      f"named market: {', '.join(foreign)}"],
        ))

    price = float(getattr(m, "price_usd", 0) or 0)
    pricing = (getattr(m, "pricing_type", None) or "")
    if (signup_tier == "accepted" and pricing == "one_time" and 0 < price < 5
            and ("files" in fulfil or "telegram" in fulfil or "discord" in fulfil)):
        out.append(Signal(
            id="price:low_value", posture="deceiving", category="low_value_digital",
            title=f"${price:g} one-time digital with chat or file drop",
            detail=("Low-value digital packs are on the prohibited list. A sub-$5 "
                    "one-time download delivered over Telegram or a zip is that "
                    "pattern wearing an accepted category."),
            lr=11.0,
            evidence=[f"price ${price:g} {pricing}",
                      f"channels: {', '.join(sorted(fulfil))}"],
        ))

    entity = (getattr(m, "entity_type", None) or "")
    if entity == "individual" and _looks_like_education(m) and any(
            w in blob for w in ("university", "universities", "campus", "school partnership")):
        out.append(Signal(
            id="entity:solo_institution", posture="deceiving",
            category="merchant_identity_fraud",
            title="Individual account claiming a university or campus partnership",
            detail=("KYC starts as a person; the pitch claims an institution. "
                    "That gap is visible on the form, before any lecture is sold."),
            lr=4.8,
            evidence=[f"entity_type={entity}", "institutional language in copy"],
        ))

    chat_only = fulfil & {"telegram", "discord"}
    software = fulfil & {"github", "license"}
    if (mapped == "saas" and chat_only and not software
            and not _looks_like_education(m)):
        out.append(Signal(
            id="fulfil:chat_saas", posture="deceiving", category="productized_services",
            title="SaaS category, fulfilment only via Telegram or Discord",
            detail=("Software usually ships a licence, GitHub seat, or file. "
                    "Chat-only delivery on a SaaS tick is a community or service "
                    "wearing a software label — catchable at Add product."),
            lr=4.2,
            evidence=[f"channels: {', '.join(sorted(fulfil))}"],
        ))
    return out


def detect_copy(m: Merchant) -> list[Signal]:
    """Risk language in the name or purpose — works even when the web is down."""
    from .websearch import match_themes
    blob = " ".join([
        m.name,
        getattr(m, "pitch", "") or "",
        getattr(m, "offering_claimed", "") or getattr(m, "offering_claimed", "") or "",
        getattr(m, "category_claimed", "") or getattr(m, "category_claimed", "") or "",
    ])
    out: list[Signal] = []
    for theme in match_themes(blob):
        out.append(Signal(
            id=f"copy:{theme['theme']}", posture="deceiving",
            category=theme["theme"],
            title=f"Application copy matches {theme['theme'].replace('_', ' ')}",
            detail=(f"The name or purpose contains “{theme['matched']}”, which is "
                    "over-represented among merchants that later went bad."),
            lr=theme["lr"],
            evidence=[f"matched: {theme['matched']}"],
        ))
    return out


def detect_web(m: Merchant) -> list[Signal]:
    """Signals from a public-web lookup attached to the merchant for this run."""
    report = getattr(m, "web_report", None) or {}
    hits = report.get("hits") or []
    themes = report.get("themes") or []
    out: list[Signal] = []
    if report.get("status") == "empty":
        out.append(Signal(
            id="web:thin", posture="deceiving", category="thin_identity",
            title="No public web footprint found",
            detail=("Wikipedia and DuckDuckGo returned nothing under this name. "
                    "A brand-new or invented identity is weakly over-represented "
                    "among bust-out applications — not proof of fraud on its own."),
            lr=1.45,
            evidence=[f"query: {report.get('query') or m.name}"],
        ))
        return out
    seen = set()
    for theme in themes:
        if theme["theme"] in seen:
            continue
        seen.add(theme["theme"])
        src = next((h.get("title") for h in hits
                    if theme["matched"] in f"{h.get('title','')} {h.get('snippet','')}".lower()),
                   (hits[0].get("title") if hits else "open web"))
        out.append(Signal(
            id=f"web:{theme['theme']}", posture="deceiving",
            category=theme["theme"],
            title=f"Open web: {theme['theme'].replace('_', ' ')}",
            detail=(f"Public pages about this name mention “{theme['matched']}” "
                    f"(e.g. {src})."),
            lr=round(theme["lr"] * 0.85, 2),
            evidence=[h.get("url") or h.get("title") or "" for h in hits[:3]],
        ))
    return out


def detect_all(m: Merchant, graph: ContextGraph, by_id: dict[str, Merchant],
               portfolio_volume: float = 0.0, store=None) -> list[Signal]:
    sigs = (detect_deceiving(m, graph, by_id)
            + detect_drifting(m, graph, by_id)
            + detect_failing(m, graph, by_id, portfolio_volume)
            + detect_attacked(m, graph, by_id)
            + detect_onboarding(m)
            + detect_copy(m)
            + detect_web(m)
            + detect_memory(m, store))
    return sorted(sigs, key=lambda s: -s.lr)
