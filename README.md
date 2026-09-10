# Merchant Risk Memory

Acme is the merchant of record. If we onboard a bad merchant, the risk is ours.
This demo is a **risk memory** for that problem.

The system **recommends**. A person **decides**. What they write down is what
**memory learns** from.

It runs on **invented merchants** so we can show the loop. It is not live on
Acme's data.

## How a decision works

There is no neural network in the background. Nothing here is trained on Acme.
The percentage you see is **evidence stacked on a starting guess**, and you
can open the working.

**When you assess someone**

1. Pull in what they already gave Acme: signup, product, country on their ID,
   how they deliver access. You should not have to type that again.
2. Start from a simple fact: **most approvals are fine.** In this demo we treat
   that as "about 1.7% of approvals later go bad."
3. Then look for things that would change your mind: they picked a category we
   do not support, their copy does not match the form, they are linked to
   someone we already terminated, their campus product sells at night in
   *their* timezone, the open web is empty, we have declined someone who looks
   like this.
4. Those findings push the 1.7% up or leave it alone. The result is the
   **chance of going bad** on the card. If you want the working, open
   **Why this recommendation?** and then **The calculation**.
5. The system says Approve, Review, or Decline. **You** still decide, and the
   two lines you type are what it remembers.

**About that 1.7%**  
It is a **starting point**, not a number the engine discovered. We assumed
roughly 45 merchants later confirmed bad, out of about 2,600 approvals. That
is a plausible book for a demo, not a figure from Acme's warehouse. If nothing
suspicious fires, the score stays near 1.7% (ordinary SaaS). If you see 84%,
read it as: we started at 1.7%, and the evidence got very strong.

**What we made up vs what the computer actually does**

We made up the 1.7%. We made up the idea that a wrong approval costs about
six times a wrong decline (that is how we get a roughly 13.8% "think hard"
line). We also made up how heavy each finding is. Those live in `config.py`
so a real Acme number can replace them.

The computer works out **which findings fired**, **how they stack**, **who this
applicant is connected to**, and **whether we have seen this kind of merchant
before**.

**What "it learns" means**  
If you decline someone for looking like a casino, the next applicant who looks
like a casino should come in hotter. A furniture SaaS should not. That is
memory, not the system retraining itself overnight. We only assumed about 45
merchants known to be bad, which is too few to train a classifier, so we
retrieve, we graph, and we remember decisions instead.

**What we have checked, and what we have not**

We have checked that quiet merchants stay quiet, that the stories we planted
(Lumen, Nightwell, services, the wrong country) actually fire, that a decline
does not punish the whole book, and that real named Acme merchants are never
used as "see, this went badly."

We have **not** checked that 1.7% is Acme's real rate, or that 84% is the true
chance this merchant fails. That would take old applications with known
endings. Until then, treat the percentage as **how strong the evidence is**,
not a forecast from the live book.

In one sentence: we can notice the right things at signup, show our working,
and get better when an analyst decides. We cannot yet say the percentage is
Acme's true probability.

## Next steps

The next step is integrating with Acme's actual system.

1. **Signup integration:** Direct sync with the merchant's responses in the
   product form.
2. **Outcomes:** Who we approved, who we declined, and who later went bad.
   With those real endings, the assumed 1.7% and the weights in `config.py`
   can be replaced with Acme's numbers.
3. **Live ops:** Disputes, prepaid balances, and payout changes for merchants
   already on the platform will update in the memory layer.
4. **Write decisions back:** Human decisions made so far, and decisions going
   forward, will be integrated. After we connect to the actual system, the
   memory layer will update itself from those calls.

## Run it

```bash
./run.sh
```

Opens <http://127.0.0.1:8765>. **No extra installs.** Python 3.11+ standard
library only. No pip, no npm, no build step.

```bash
python3 -m unittest discover -s tests -q     # 82 tests
```

Longer context: **[HANDOFF.md](HANDOFF.md)**.

## What you’ll see

| View | What it shows |
|---|---|
| **Homepage** | Portfolio snapshot and **Assess a merchant** |
| **Assessment history** | Session assessments and recorded decisions |
| **Merchants** | The corpus, searchable, ranked by P(bad) |
| **Memory layer** | Add / update / invalidate / no-op, plus the replay gate |
| **Evaluations** | Queue and live alerts |
| **Context graph** | Corroborating routes to merchants already judged |
| **Alerts** | Post-approval lifecycle, by risk posture |

### Try it in this order

1. **Assess a merchant**, then **Import from Acme**. This is the form they already filled.
2. **Westbrook AP Live**. An Indian entity running live classes at 8pm Eastern. Caught at signup, before any money moves.
3. **Nightwell Academy**. The same idea once they are live. "Night" means night **in India**, not on a UTC clock.
4. **Lumen Labs**. The form looks fine. The graph still ties them to someone we already terminated. Decline them and write why. That is the learning step.
5. **Quill Harbor**. They picked Services on the form. We do not take that. Decline.

## Acme brand and real customers

Colours come from `acmemor.com/brand`: lime `#C6FE1E`, forest `#004F32`, blue
`#1264FF`, and their actual body ink `#00160D` — a green-black, not a grey. The dark
theme uses their forest-green family rather than a neutral black. `config.BRAND` holds
the palette and a test asserts the stylesheet stays in sync with it.

All **seventeen** real, publicly-named Acme merchants are seeded — **Mole, Vibe3D,
Draftly, ReplyDaddy, CatDoes, Indilingo, Scira AI, PeerPush, IndieKit, Betide Studio,
Healthify, Parakeet AI, MATIKS, GPAI, Cardboard, SurgeGrowth, Vaya**. Product
descriptions are factual; volumes and dispute figures are illustrative and the UI
says so.

**A real merchant never appears next to an adverse finding.** Not flagged, not declined,
not in a fraud ring, not graph-linked to a terminated merchant, never cited as adverse
precedent. This is six tests plus an assertion in `build()`, not a convention — the
corpus is randomised, so a reseed could otherwise sweep a real name into the bad sample
silently. They are seeded as what they are: healthy approved merchants, which also gives
the system a genuine population to correctly leave alone.

That control population is a test as much as a feature, and it earned its keep: two
customers tripped the guard during the build, both from prose similarity being mistaken
for evidence. Both are fixed with regression tests — see the next section.

## Design decisions worth knowing

**No hardcoded "catalogue implies piracy" rule.** That insight is not policy —
it is learned from the Vellum Reader incident, arrives as a distilled memory,
and only takes effect after passing the replay gate. Hardcoding it would
pre-empt the loop the system exists to demonstrate.

**Memories carry both a text trigger and an optional structured predicate.**
Text catches *content* patterns; predicates catch *behavioural* ones. A
refund-rate pattern keyed on pitch text would never generalise, because a
deceptive-billing merchant's pitch reads like any other SaaS. This is §2.1's
content-versus-behavioural split showing up in the code.

**Victim outcomes are excluded from precedent.** Card testing and account
takeover are not properties of a merchant's business, so they must not
poison the inference for merchants selling similar products.

**Contradictions must be better evidenced to win.** A lower-confidence
contradiction is recorded as `DISPUTED` rather than silently overwriting a
well-evidenced fact — the memory-poisoning failure of §9.6. Nothing is ever
deleted; facts are superseded, so any past decision can be replayed against
the memory as it stood.

**Retrieval stems conservatively.** Without it "libraries" never matches
"library" and "ebooks" never matches "ebook", which breaks pattern matching in a
way that looks like memory simply holding nothing.

**Hub nodes are not traversed.** A nameserver shared by 900 merchants explains
nothing. A payout holder name shared by three explains a great deal.

**A memory that names a number is gated on that number.** A pattern reading
"refund rates above 15 percent" with no predicate matches on *text*, so it fires
on any pitch containing "subscription" and "free trial" — which is most of the
portfolio. Behavioural lessons gate on the observable, never on the wording.

**Precedent has a measured similarity floor of 0.20.** Below it, neighbours match
only on `subscription`, `saas`, `github`, `email` — vocabulary the whole corpus
shares. Left in, one unlucky neighbour at cosine 0.13 moves a clean merchant's
odds by 3x. Genuine precedent here sits at 0.24 and above.

**The predicate evaluator is a whitelisted interpreter,** not `eval`. Memories
are written by an automated distiller; one that could execute arbitrary code
would be a remote-code-execution hole dressed up as a learning loop.

## Layout

```
riskmemory/
  config.py        assumed constants — every §6 number lives here and nowhere else
  applications.py  inbound Acme signup integration (demo inbox)
  corpus.py        deterministic synthetic population (seed 20260820)
  graph.py         context graph, entity resolution, corroborating-path search
  retrieval.py     hand-rolled TF-IDF + cosine, no numpy
  memory.py        add/update/invalidate/no-op lifecycle, provenance, predicates
  signals.py       detectors, one family per posture
  decision.py      likelihood ratios in odds space against the 13.8% threshold
  monitor.py       lifecycle alerts and drift reconciliation
  replay.py        distillation and the replay gate
  app.py           application state
  server.py        stdlib HTTP server
web/               vanilla JS console, no framework
tests/             82 tests
docs/              the three source documents + the merged artifact
```

## Every number here is assumed

The corpus is sized to the assumed baseline in §6.1 — 4,000 applications,
65% approval, 45 confirmed-bad, $150M annualised, VAMP under the 0.50%
acquirer line. The decline threshold of 13.8% is derived from the assumed
6:1 cost ratio in §6.2. **None of it is measured.** Replace any figure in
`config.py` and everything downstream re-derives.
