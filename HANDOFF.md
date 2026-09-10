# Handoff

**Merchant Risk Memory** — an anti-fragile memory layer with a context graph for
merchant risk at a merchant-of-record platform.

Anushika Poddar · 20 August 2026

---

## 1. What this is

Acme is the merchant of record. Every merchant it admits borrows Acme's licences
and Acme's liability, and merchants transact under shared Acme merchant
identifiers — so one bad actor's dispute ratio pollutes a pool every honest
merchant depends on. **The cost of a bad merchant is not bounded by their volume.
It is bounded by Acme's standing with its acquirers.**

Today those decisions are made from isolated, point-in-time evidence, using human
judgement that does not persist, against outcomes that arrive months later and are
never fed back. The same losses recur, and the reasoning behind a rejection lives
in one analyst's head.

This turns every decision, incident and outcome into durable, connected,
retrievable memory — so each new decision carries what the platform has already
learned, and adverse events measurably strengthen future decisions rather than
merely being survived.

It is a **working demo on synthetic data**, not a production system. See §7.

## 2. Run it

```bash
./run.sh                                      # http://127.0.0.1:8765
python3 -m unittest discover -s tests -q      # 56 tests
```

**No dependencies.** Python 3.11+ standard library and vanilla JavaScript. No
pip install, no npm, no build step, nothing to configure. The TF-IDF, the
stemmer, the cosine similarity and the graph search are all hand-rolled — not
for purity, but so that a founder can clone this and have it running in ten
seconds with no environment to debug.

## 3. Layout

```
riskmemory/
  config.py      assumed constants, Acme brand palette, platform features
  corpus.py      deterministic synthetic population (seed 20260820) + real customers
  graph.py       context graph, entity resolution, corroborating-path search
  retrieval.py   hand-rolled TF-IDF + cosine + 4-rule stemmer, no numpy
  memory.py      add / update / invalidate / no-op / disputed lifecycle, predicates
  signals.py     detectors, one family per risk posture
  decision.py    likelihood ratios in odds space, 13.8% operating point
  monitor.py     lifecycle alerts and drift reconciliation
  replay.py      pattern distillation and the replay gate
  converse.py    intent parsing and evidence-cited answers
  app.py         application state, overview(), directory(), brief()
  server.py      stdlib HTTP server
web/             index.html, app.js, styles.css, assets/
tests/           56 tests
docs/            the three source documents + the merged artifact
```

Roughly 3,400 lines of Python, 1,400 of web, 470 of tests.

## 4. The four risk postures

The taxonomy is the spine of the whole system — detectors, memory categories and
alerts are all organised by it. Framing everything as "fraud" is what causes two
of these four to go uncovered entirely.

| Posture | The merchant is… | Example |
|---|---|---|
| **Deceiving us** | lying at intake | undisclosed illegality, a re-entry under a new legal entity |
| **Drifting from us** | changing after approval | a B2B tool that quietly adds a prohibited tier |
| **Failing** | going under, honestly | selling annual plans while volume declines; Acme holds the refunds |
| **Being attacked** | the victim | payout redirection, card testing, account takeover |

**Failing** and **being attacked** are invisible to any fraud-detection framing —
in both, the merchant has done nothing wrong — yet they carry real liability. A
merchant with $486k of undelivered prepaid service is a larger exposure than most
fraudsters, and card-testing victims must never be counted as adverse precedent
(see §6).

## 5. How a decision is made

1. **Retrieve** — the applicant's profile is matched against past cases by TF-IDF
   cosine, and against active memories by text trigger *or* structured predicate.
2. **Corroborate** — the context graph finds routes to merchants already judged.
   Shared entities above degree 40 are treated as hubs and never carry
   corroboration: a shared payment processor is not evidence.
3. **Combine** — each signal contributes a likelihood ratio, combined in odds
   space with damping (0.62) for correlated signals, against a base rate.
4. **Decide** — the operating point is derived, not chosen: a false approve costs
   ~$25k, a false decline ~$4k, so the ratio is ~6:1 and the decline threshold is
   **P(bad) ≥ 13.8%**. Change the two costs and the threshold moves with them.
5. **Reconcile** — the rationale you type is what memory learns from. It is
   reconciled against what is already held: add, update, invalidate, no-op or
   flag as disputed, with provenance and supersession preserved.

Nothing is decided by a model. The arithmetic is deterministic and reproducible,
which is the point — an explanation of why a merchant was declined has to survive
an acquirer asking about it eight months later.

## 6. Design decisions that look like bugs

These are the ones most likely to be "fixed" by someone who doesn't know why they
are there. Each has a test.

| Looks wrong | Why it is right |
|---|---|
| Card-testing victims excluded from precedent | They are victims. Counting them as bad-merchant precedent flagged a clean merchant at the threshold. |
| Contradictions need a 0.05 confidence margin | Without it, a low-confidence claim can invalidate a well-evidenced fact — memory poisoning. Weaker contradictions become `DISPUTED` for a human. |
| Graph hubs suppressed above degree 40 | Otherwise every merchant is "related" to every other through their payment processor, and corroboration means nothing. |
| A memory naming a number carries a predicate | A pattern about refund rates matched on prose fires on any pitch containing "subscription" and "free trial". Behavioural lessons gate on the observable. |
| Precedent has a 0.20 similarity floor | Below it, neighbours match only on `subscription`, `saas`, `github`, `email` — the corpus's vocabulary, not the merchant's. Measured: real precedent sits at 0.24+. |
| `catalogue_rights` is not a hardcoded rule | It was, and it pre-empted the memory the system is supposed to *learn*. Deleting it is what let the replay gate demonstrate anything. |
| Cases sorted by P(bad) alone, not alert severity | Severity sorting buried a 93% decline underneath a 19% medium alert. |

## 7. Data provenance — read this before demoing

**The corpus is generated locally**, in `corpus.py`, from seed 20260820. It is
not scraped, not downloaded, not sourced from anywhere. The application makes no
network calls of its own.

**All 17 publicly-named Acme merchants are seeded** — Mole, Vibe3D, Draftly,
ReplyDaddy, CatDoes, Indilingo, Scira AI, PeerPush, IndieKit, Betide Studio,
Healthify, Parakeet AI, MATIKS, GPAI, Cardboard, SurgeGrowth, Vaya — as a clean
control population against ~4,000 invented merchants. Their product descriptions
are factual, from public sources. Their **operating figures are illustrative**,
and the interface says so.

> ### Hard rule, enforced in code
>
> **A real merchant never appears next to an adverse finding.** Not flagged, not
> declined, not in a fraud ring, not graph-linked to a terminated merchant, never
> carrying a "went bad" label, never cited as adverse precedent.
>
> These are real businesses. A screenshot showing one two hops from a piracy
> termination would be defamatory in effect regardless of intent. The corpus is
> randomised, so this is an assertion in `corpus.build()` plus six tests that
> **fail the build** — not a convention. Every fraud ring and every termination
> uses an invented name.

Two of these customers tripped that guard during the build, and both failures
were the same mistake — prose similarity mistaken for evidence. Both are fixed
with regression tests (§6, rows 4 and 5). The guard did its job.

## 8. The numbers we assumed

The founders were asked and these were assumed in order to keep building. Every
one is a constant in `config.py`, not a value buried in logic — change it and the
system moves.

| Assumed | Value | Drives |
|---|---|---|
| Cost of a false approve | $25,000 | the operating point |
| Cost of a false decline | $4,000 | the operating point |
| ⇒ decline threshold | **P(bad) ≥ 13.8%** | every decision |
| Auto-approve below | 4% | queue volume |
| VAMP acquirer above-standard | 0.50% | portfolio alerts |
| VAMP merchant excessive | 1.50% (from 1 Apr 2026) | merchant alerts |

Live demo figures: 4,029 applications, 2,579 approved merchants, VAMP 0.353%
against a 0.50% ceiling, 18,473 graph entities / 41,777 relationships, 18 active
memories at 0.906 mean confidence, 36 merchants needing a human.

## 9. Where Claude goes — and where it must not

The Claude layer is **designed but not wired in**. This is the largest piece of
remaining work, and the constraints matter more than the code.

| Claude does | Claude never |
|---|---|
| Compose the answer from retrieved context | **Decide** — the P(bad) arithmetic stays deterministic |
| Read an unstructured application into fields | Invent evidence not present in the retrieval |
| Draft a candidate memory from a rationale | Write to memory silently — reconciliation is explicit |
| Suggest a distilled pattern after an incident | Promote a pattern past the replay gate |

**The API key must never reach the browser.** It lives in an environment variable
on the server; the browser calls our own endpoint; our server calls Anthropic. A
key in client-side code is readable via view-source and billable by whoever finds
it. Set it yourself before running — it should never be pasted into a file, a
chat, or this repository:

```bash
export ANTHROPIC_API_KEY=...
./run.sh
```

Every screen renders without a key; the console degrades to the deterministic
path.

## 10. What is left

1. **Wire in the Claude API layer** — server-side key, grounded composition over
   retrieved context only, graceful fallback. Designed, not built.
2. **Real data.** Everything here is synthetic. The first honest test is whether
   the four postures survive contact with Acme's actual decline reasons.
3. **Calibration.** The likelihood ratios are hand-set. With real outcomes they
   should be fitted, and the replay gate becomes the mechanism for doing it
   safely.
4. **Two uncovered postures need real signals.** Failing and being attacked are
   modelled, but their detectors lean on fields a production system would have to
   actually source — prepaid balance, login anomalies, payout changes.

## 11. Documents

- **[Merged artifact](https://claude.ai/code/artifact/31f3b9ac-a375-4662-a191-6dab48fde813)** — problem statement, pipeline diagrams and console design as one tabbed page. *Share this one.*
- Sources and the build script are in `docs/`. Edit a source, re-run
  `build_merged.py`, republish. Never edit the merged file directly.

*Note: the tabbed page is rendered in an iframe, so `#console`-style deep links
do not survive being shared — the reader always lands on tab 1.*
