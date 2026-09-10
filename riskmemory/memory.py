"""The memory layer.

Section 4 of the problem statement: memory is *reconciled*, not appended.
Every write resolves to one of ADD / UPDATE / INVALIDATE / NO-OP, and every
record carries provenance, confidence and an observation time distinct from
its write time so any past decision can be replayed against the memory as it
stood at the time.
"""
from __future__ import annotations

import datetime as _dt
import itertools
from dataclasses import dataclass, field, asdict
from typing import Optional

from . import config
from .retrieval import TfIdf

_ALLOWED_FIELDS = {
    "refund_rate", "settled_txns", "disputes", "fraud_reports", "monthly_volume",
    "forecast_monthly", "prepaid_balance", "annual_plan_share", "micro_txn_share",
    "domain_age_days", "login_anomaly",
}
_OPS = {
    ">=": lambda a, b: a >= b, ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b, "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
    "ratio>=": lambda a, b: a >= b,
}


def evaluate_predicate(pred: Optional[dict], merchant) -> bool:
    """Evaluate a stored predicate against a merchant.

    Deliberately a tiny whitelisted interpreter rather than anything eval-like:
    memories are written by an automated distiller, and a memory that could
    execute arbitrary code would be a remote-code-execution hole dressed up as
    a learning loop.
    """
    if not pred:
        return False
    conds = pred.get("all") or []
    if not conds:
        return False
    for c in conds:
        field, op, value = c.get("field"), c.get("op"), c.get("value")
        if field not in _ALLOWED_FIELDS or op not in _OPS:
            return False
        actual = getattr(merchant, field, None)
        if actual is None:
            return False
        if op == "ratio>=":
            denom = getattr(merchant, c.get("over", ""), None)
            if not denom:
                return False
            actual = actual / denom
        try:
            if not _OPS[op](actual, value):
                return False
        except TypeError:
            return False
    return True

ADD, UPDATE, INVALIDATE, NOOP, DISPUTED = (
    "ADD", "UPDATE", "INVALIDATE", "NO-OP", "DISPUTED")

_ids = itertools.count(1)


@dataclass
class Memory:
    id: str
    kind: str                 # episodic | semantic | procedural
    text: str                 # the human-readable statement, shown in briefs
    trigger: str              # the retrieval key -- what this is matched against
    subject: Optional[str]    # merchant id, or None for a general pattern
    category: Optional[str]
    polarity: str             # adverse | clearing | neutral
    confidence: float
    source: str               # provenance: who or what asserted this
    observed_at: str
    written_at: str
    #: Optional structured condition, e.g. {"all": [{"field": "refund_rate",
    #: "op": ">=", "value": 0.12}]}. Text triggers catch *content* patterns;
    #: predicates catch *behavioural* ones. Section 2.1 of the problem statement
    #: is precisely about needing both.
    predicate: Optional[dict] = None
    status: str = "active"    # active | superseded | invalidated | disputed
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None
    evidence: list[str] = field(default_factory=list)
    promoted: bool = True     # semantic memories may await the replay gate

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Reconciliation:
    action: str
    memory: Memory
    against: Optional[Memory] = None
    similarity: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "memory": self.memory.to_dict(),
            "against": self.against.to_dict() if self.against else None,
            "similarity": round(self.similarity, 4),
            "reason": self.reason,
        }


class MemoryStore:
    #: above this two statements are treated as the same claim
    SAME_CLAIM = 0.86
    #: above this they are about the same thing, so polarity decides the action
    RELATED = 0.45
    #: a contradiction must beat the held fact by this margin to invalidate it
    CONTRADICTION_MARGIN = 0.05

    def __init__(self, prime_corpus: Optional[list[str]] = None) -> None:
        self.records: dict[str, Memory] = {}
        self.log: list[Reconciliation] = []
        self.index = TfIdf()
        if prime_corpus:
            self.index.prime(prime_corpus)

    # -- writing ------------------------------------------------------------
    def _key(self, m: Memory) -> str:
        return f"{m.subject or '*'}|{m.category or '*'}"

    def _peers(self, m: Memory) -> list[Memory]:
        k = self._key(m)
        return [r for r in self.records.values()
                if r.status == "active" and self._key(r) == k and r.id != m.id]

    def reconcile(
        self,
        text: str,
        *,
        trigger: Optional[str] = None,
        predicate: Optional[dict] = None,
        kind: str = "episodic",
        subject: Optional[str] = None,
        category: Optional[str] = None,
        polarity: str = "neutral",
        confidence: float = 0.7,
        source: str = "system",
        observed_at: Optional[str] = None,
        evidence: Optional[list[str]] = None,
        promoted: bool = True,
    ) -> Reconciliation:
        """Resolve a candidate fact against what memory already holds."""
        now = _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds")
        cand = Memory(
            id=f"mem{next(_ids):05d}", kind=kind, text=text.strip(),
            trigger=(trigger or text).strip(), predicate=predicate, subject=subject,
            category=category, polarity=polarity, confidence=round(confidence, 4),
            source=source, observed_at=observed_at or config.DEMO_TODAY,
            written_at=now, evidence=evidence or [], promoted=promoted,
        )

        best: Optional[Memory] = None
        best_sim = 0.0
        cv = self.index.vector(cand.text)
        for peer in self._peers(cand):
            sim = TfIdf.cosine(cv, self.index.vector(peer.text))
            if sim > best_sim:
                best, best_sim = peer, sim

        if best is not None and best_sim >= self.SAME_CLAIM:
            if cand.confidence <= best.confidence + 1e-9:
                rec = Reconciliation(NOOP, cand, best, best_sim,
                                     "Already held at equal or higher confidence.")
                self.log.append(rec)
                return rec
            best.status = "superseded"
            best.superseded_by = cand.id
            cand.supersedes = best.id
            self._store(cand)
            rec = Reconciliation(UPDATE, cand, best, best_sim,
                                 f"Refines an existing fact: confidence "
                                 f"{best.confidence:.2f} -> {cand.confidence:.2f}.")
            self.log.append(rec)
            return rec

        if (best is not None and best_sim >= self.RELATED
                and best.polarity != "neutral" and cand.polarity != "neutral"
                and best.polarity != cand.polarity):
            # A contradiction only wins if it is better evidenced than what it
            # contradicts. Without this guard a single confidently-wrong fact
            # can overwrite a well-evidenced one and propagate into every later
            # decision -- the memory-poisoning failure in section 9.6.
            if cand.confidence > best.confidence + self.CONTRADICTION_MARGIN:
                best.status = "invalidated"
                best.superseded_by = cand.id
                cand.supersedes = best.id
                self._store(cand)
                rec = Reconciliation(
                    INVALIDATE, cand, best, best_sim,
                    f"Contradicts a held {best.polarity} fact at higher confidence "
                    f"({cand.confidence:.2f} vs {best.confidence:.2f}); the old fact is "
                    f"superseded, never deleted.")
                self.log.append(rec)
                return rec
            cand.status = "disputed"
            self._store(cand)
            rec = Reconciliation(
                DISPUTED, cand, best, best_sim,
                f"Contradicts a held {best.polarity} fact but is not better evidenced "
                f"({cand.confidence:.2f} vs {best.confidence:.2f}). Both retained, "
                f"flagged for a human.")
            self.log.append(rec)
            return rec

        self._store(cand)
        rec = Reconciliation(ADD, cand, best, best_sim, "No comparable fact held.")
        self.log.append(rec)
        return rec

    def _store(self, m: Memory) -> None:
        self.records[m.id] = m
        # The index holds the *trigger*, not the prose. A distilled pattern is
        # written to be read by a human ("...have repeatedly ended in rights
        # claims against Acme"), which makes a poor retrieval key against a
        # two-line merchant pitch. Separating the two keeps both jobs honest.
        self.index.add(m.id, m.trigger or m.text)

    # -- reading ------------------------------------------------------------
    def active(self, kind: Optional[str] = None, promoted_only: bool = True) -> list[Memory]:
        out = [m for m in self.records.values() if m.status == "active"]
        if kind:
            out = [m for m in out if m.kind == kind]
        if promoted_only:
            out = [m for m in out if m.promoted]
        return out

    def for_subject(self, subject: str) -> list[Memory]:
        return [m for m in self.records.values()
                if m.subject == subject and m.status == "active"]

    def search(self, text: str, limit: int = 6, kind: Optional[str] = None,
               promoted_only: bool = True) -> list[tuple[Memory, float]]:
        pool = {m.id for m in self.active(kind, promoted_only)}
        hits = self.index.search(text, limit=limit, candidates=pool)
        return [(self.records[i], s) for i, s in hits if i in self.records]

    def counts(self) -> dict:
        from collections import Counter
        by_action = Counter(r.action for r in self.log)
        by_kind = Counter(m.kind for m in self.records.values() if m.status == "active")
        return {
            "total": len(self.records),
            "active": sum(1 for m in self.records.values() if m.status == "active"),
            "superseded": sum(1 for m in self.records.values() if m.status == "superseded"),
            "invalidated": sum(1 for m in self.records.values() if m.status == "invalidated"),
            "disputed": sum(1 for m in self.records.values() if m.status == "disputed"),
            "pending_gate": sum(1 for m in self.records.values()
                                if m.status == "active" and not m.promoted),
            "by_action": dict(by_action),
            "by_kind": dict(by_kind),
            # drives the sidebar status meter -- how sure the layer is of what
            # it currently believes, averaged over records still in force
            "mean_confidence": round(
                sum(m.confidence for m in self.records.values() if m.status == "active")
                / max(1, sum(1 for m in self.records.values() if m.status == "active")), 3),
        }
