"""Distillation and the replay gate.

Section 4: a candidate memory distilled from a confirmed incident only reaches
the live decision policy if replaying it over the historical decision set
improves outcomes *without regressing* them. That delta is the anti-fragility
claim, and this module is what produces the number.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from . import config
from .corpus import Merchant
from .decision import decide
from .graph import ContextGraph
from .memory import Memory, MemoryStore
from .signals import detect_all

#: Recommendations that stop a merchant reaching the portfolio unexamined.
FLAGGING = {"decline", "escalate"}


@dataclass
class ReplayResult:
    population: int
    bad_total: int
    caught: int
    missed: int
    false_flags: int
    clean_total: int

    @property
    def recall(self) -> float:
        return self.caught / self.bad_total if self.bad_total else 0.0

    @property
    def false_flag_rate(self) -> float:
        return self.false_flags / self.clean_total if self.clean_total else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["recall"] = round(self.recall, 4)
        d["false_flag_rate"] = round(self.false_flag_rate, 4)
        return d


@dataclass
class GateOutcome:
    candidate: dict
    before: dict
    after: dict
    caught_delta: int
    false_flag_delta: int
    promoted: bool
    verdict: str

    def to_dict(self) -> dict:
        return asdict(self)


def distil(incident: Merchant, store: MemoryStore) -> Memory:
    """Turn a confirmed incident into a candidate semantic memory.

    Written as a general pattern rather than a fact about one merchant --
    a memory that only describes Vellum Reader can never catch Kindle Grove.
    """
    triggers = {
        "undisclosed_illegality":
            "catalogue library archive titles books audiobooks ebook unlimited "
            "access reading subscription rights licensing publisher",
        "recidivist_ring":
            "payout holder beneficial owner terms page terminated re-entry new "
            "entity nominee director shared",
        "product_drift":
            "ai companion intimacy chat character roleplay adult tier pivot "
            "meeting summarisation drift",
        "deceptive_billing":
            "subscription auto-renewal free trial cancel cancellation refund "
            "recurring billing monthly",
        "transaction_laundering":
            "volume forecast exceeded processing another business front site",
        "insolvency":
            "annual plan prepaid balance declining volume runway refunds owed",
        "account_takeover":
            "payout bank details changed login anomaly compromised account",
        "card_testing":
            "micro transactions small charges fraud reports enumeration bot checkout",
    }
    templates = {
        "undisclosed_illegality":
            ("Catalogue-scale ebook and content library offerings that cannot produce "
             "per-title rights or licensing documentation have repeatedly ended in "
             "rights claims against Acme. Treat unlimited titles, library and archive "
             "claims as requiring licences on file before approval."),
        "recidivist_ring":
            ("Applicants sharing a payout holder name, a beneficial owner or a verbatim "
             "terms page with a previously terminated merchant are re-entries under a "
             "new legal entity rather than new businesses."),
        "product_drift":
            ("Merchants underwritten as B2B AI tooling that later add companion or "
             "intimacy tiers move into a prohibited category on the same account "
             "without notifying us."),
        "deceptive_billing":
            ("Subscription products with sustained refund rates above 15 percent are "
             "signalling a cancellation flow customers cannot find, not a faulty "
             "product."),
        "transaction_laundering":
            ("Volume running several times above the underwritten forecast on an "
             "unchanged four-page site indicates another business being processed "
             "through the account."),
        "insolvency":
            ("Merchants selling annual plans while volume declines across consecutive "
             "quarters leave Acme holding the refunds on prepaid service."),
        "account_takeover":
            ("Payout bank details changed within days of an anomalous login pattern "
             "indicate a compromised merchant account rather than a dishonest merchant."),
        "card_testing":
            ("Checkouts with a majority of sub-two-dollar transactions and elevated "
             "fraud reports are being used to test stolen cards."),
    }
    # Behavioural lessons distil into predicates; content lessons into text
    # triggers. A refund-rate pattern keyed on pitch text would never generalise,
    # because the pitch of a deceptive-billing merchant reads like any other SaaS.
    predicates = {
        "deceptive_billing": {"all": [
            {"field": "refund_rate", "op": ">=", "value": 0.12},
            {"field": "settled_txns", "op": ">=", "value": 40}]},
        "transaction_laundering": {"all": [
            {"field": "monthly_volume", "op": "ratio>=", "value": 4.0,
             "over": "forecast_monthly"}]},
        "insolvency": {"all": [
            {"field": "prepaid_balance", "op": "ratio>=", "value": 5.0,
             "over": "monthly_volume"}]},
        "account_takeover": {"all": [
            {"field": "login_anomaly", "op": "==", "value": True}]},
        "card_testing": {"all": [
            {"field": "micro_txn_share", "op": ">=", "value": 0.35},
            {"field": "fraud_reports", "op": ">=", "value": 20}]},
    }
    cat = incident.truth_category or "undisclosed_illegality"
    text = templates.get(cat, f"Merchants resembling {incident.name} have gone bad.")
    rec = store.reconcile(
        text, trigger=triggers.get(cat), predicate=predicates.get(cat),
        kind="semantic", category=cat, polarity="adverse",
        confidence=0.72, source=f"distilled from incident: {incident.name}",
        observed_at=config.DEMO_TODAY, evidence=[incident.id, incident.truth_note],
        promoted=False,                     # must pass the gate first
    )
    return rec.memory


def replay(merchants: list[Merchant], graph: ContextGraph,
           by_id: dict[str, Merchant], store: MemoryStore,
           portfolio_volume: float, sample: Optional[list[Merchant]] = None,
           precedent=None) -> ReplayResult:
    """Re-decide historical cases under the memory as it currently stands.

    ``precedent`` is the live path's precedent lookup. Replay has to use the
    same decision function the queue uses, or the number it produces measures
    something other than the system we are actually running.
    """
    pool = sample if sample is not None else [
        m for m in merchants if m.status in ("approved", "terminated")
    ]
    caught = missed = false_flags = bad = clean = 0
    for m in pool:
        sigs = detect_all(m, graph, by_id, portfolio_volume, store)
        dec = decide(sigs, precedent(m) if precedent else None)
        flagged = dec.recommendation in FLAGGING
        if m.truth_bad:
            bad += 1
            caught += 1 if flagged else 0
            missed += 0 if flagged else 1
        else:
            clean += 1
            false_flags += 1 if flagged else 0
    return ReplayResult(len(pool), bad, caught, missed, false_flags, clean)


def run_gate(candidate: Memory, merchants: list[Merchant], graph: ContextGraph,
             by_id: dict[str, Merchant], store: MemoryStore,
             portfolio_volume: float, sample_size: int = 420,
             precedent=None) -> GateOutcome:
    """Replay with and without the candidate; promote only if it helps.

    Promotion requires strictly more bad merchants caught and no increase in
    merchants wrongly flagged. Without that second condition every incident
    makes the system more paranoid and the approval rate quietly collapses.
    """
    pool = [m for m in merchants if m.status in ("approved", "terminated")]
    bad = [m for m in pool if m.truth_bad]
    clean = [m for m in pool if not m.truth_bad]
    step = max(1, len(clean) // max(1, sample_size - len(bad)))
    sample = bad + clean[::step]

    candidate.promoted = False
    before = replay(merchants, graph, by_id, store, portfolio_volume, sample, precedent)

    candidate.promoted = True
    after = replay(merchants, graph, by_id, store, portfolio_volume, sample, precedent)

    caught_delta = after.caught - before.caught
    ff_delta = after.false_flags - before.false_flags
    promoted = caught_delta > 0 and ff_delta <= 0

    if promoted:
        verdict = (f"Promoted. Catches {caught_delta} more confirmed-bad merchant"
                   f"{'s' if caught_delta != 1 else ''} on replay with no increase in "
                   f"merchants wrongly flagged.")
    elif caught_delta <= 0:
        verdict = ("Held back. Replay shows no improvement on cases we previously "
                   "got wrong, so promoting it would add noise for nothing.")
    else:
        verdict = (f"Held back. Catches {caught_delta} more, but wrongly flags "
                   f"{ff_delta} additional legitimate merchant"
                   f"{'s' if ff_delta != 1 else ''} -- the paranoia the gate exists "
                   f"to prevent.")

    candidate.promoted = promoted
    return GateOutcome(
        candidate=candidate.to_dict(), before=before.to_dict(), after=after.to_dict(),
        caught_delta=caught_delta, false_flag_delta=ff_delta,
        promoted=promoted, verdict=verdict,
    )
