"""Tests for the merchant risk memory pipeline."""
import os, sys, unittest
from pathlib import Path

os.environ["RISKMEMORY_WEB"] = "0"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from riskmemory import config
from riskmemory.app import App
from riskmemory.corpus import build, summary
from riskmemory.decision import decide, precedent_likelihood
from riskmemory.graph import ContextGraph
from riskmemory.memory import MemoryStore, evaluate_predicate
from riskmemory.replay import distil, run_gate
from riskmemory.signals import detect_all

APP = App()          # built once: the corpus is deterministic


class TestConfig(unittest.TestCase):
    def test_threshold_matches_assumed_cost_ratio(self):
        self.assertAlmostEqual(config.DECLINE_THRESHOLD, 4000 / 29000, places=6)
        self.assertAlmostEqual(config.DECLINE_THRESHOLD, 0.1379, places=3)

    def test_loss_distribution_is_a_distribution(self):
        self.assertAlmostEqual(sum(config.LOSS_DISTRIBUTION.values()), 1.0, places=6)

    def test_every_category_has_a_posture(self):
        for cat in config.LOSS_DISTRIBUTION:
            self.assertIn(cat, config.CATEGORY_POSTURE)


class TestCorpus(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual([m.id for m in build()][:50], [m.id for m in build()][:50])

    def test_sized_to_assumed_baseline(self):
        s = summary(APP.merchants)
        self.assertAlmostEqual(s["approval_rate"], config.APPROVAL_RATE, delta=0.03)
        self.assertAlmostEqual(s["monthly_volume"] * 12, config.ANNUAL_VOLUME_USD,
                               delta=config.ANNUAL_VOLUME_USD * 0.15)
        self.assertLess(s["portfolio_vamp"], config.VAMP_ACQUIRER_ABOVE_STANDARD)
        self.assertGreater(s["confirmed_bad"], 30)

    def test_scenarios_present(self):
        names = {m.name for m in APP.merchants}
        for n in ("Lumen Labs", "Kindle Grove", "Northwind Notes", "Vellum Reader"):
            self.assertIn(n, names)

    def test_bad_merchants_are_observably_consistent(self):
        """A merchant labelled an ebook rights case must actually look like one."""
        for m in APP.merchants:
            if m.truth_category == "undisclosed_illegality":
                self.assertEqual(m.category_claimed, "ebooks_publications")
            if m.truth_category == "transaction_laundering" and m.forecast_monthly:
                self.assertGreater(m.monthly_volume / m.forecast_monthly, 3)


class TestRealCustomers(unittest.TestCase):
    """Real, publicly-named Acme merchants must never sit next to an adverse finding."""

    def real(self):
        return [m for m in APP.merchants if m.real]

    def test_all_named_customers_are_seeded(self):
        from riskmemory.corpus import REAL_CUSTOMER_NAMES
        self.assertEqual(len(self.real()), len(REAL_CUSTOMER_NAMES))
        self.assertEqual({m.name for m in self.real()}, set(REAL_CUSTOMER_NAMES))

    def test_never_carry_ground_truth_adverse(self):
        for m in self.real():
            self.assertFalse(m.truth_bad, m.name)
            self.assertIsNone(m.truth_category, m.name)
            self.assertEqual(m.status, "approved", m.name)

    def test_never_flagged_by_the_live_engine(self):
        """Ground truth is not enough — the running system must clear them too.

        The bar is "no adverse finding", which is what the rule actually says:
        no signal fires, nothing is near the decline threshold, and the outcome
        is an approval. It is deliberately not "approve unconditionally".
        Conditions are a routine commercial outcome — a reserve or a volume cap
        — that a real risk team applies to healthy merchants every week, and
        writing the stricter assertion would only tempt us to tune a real
        company's numbers until the engine flattered it.
        """
        for m in self.real():
            sigs = detect_all(m, APP.graph, APP.by_id, APP.portfolio_volume, APP.store)
            self.assertEqual(sigs, [], f"{m.name} raised {[s.title for s in sigs]}")
            d = decide(sigs, APP._precedent(m))
            self.assertIn(d.recommendation, ("approve", "conditions"), m.name)
            # comfortably clear, not marginally clear
            self.assertLess(d.p_bad, config.DECLINE_THRESHOLD / 2, m.name)

    def test_never_appear_in_alerts(self):
        names = {m.name for m in self.real()}
        for a in APP.alerts():
            self.assertNotIn(a.merchant, names)

    def test_never_graph_linked_to_a_bad_merchant(self):
        for m in self.real():
            for rel in APP.graph.related_merchants(m.id):
                other = APP.by_id.get(rel.target)
                if other:
                    self.assertFalse(other.truth_bad, f"{m.name} -> {other.name}")

    def test_never_cited_as_adverse_precedent(self):
        for m in APP.merchants[:200]:
            for other, _sim in APP._precedent(m):
                if other.real:
                    self.assertFalse(other.truth_bad, other.name)


class TestEvidenceQuality(unittest.TestCase):
    """Guards against prose similarity being mistaken for evidence.

    Both of these started as real false positives against named Acme
    customers: a memory about refund rates fired on any pitch containing
    "subscription" and "free trial", and a precedent search returned
    neighbours matching only on corpus-wide boilerplate.
    """

    def test_behavioural_memories_carry_a_predicate(self):
        """A memory naming a numeric threshold must be gated on that number."""
        for mem in APP.store.active("semantic", promoted_only=True):
            if mem.polarity != "adverse":
                continue
            if any(w in mem.text.lower() for w in ("rate", "percent", "volume", "times")):
                self.assertIsNotNone(
                    mem.predicate,
                    f"{mem.id} states a threshold in prose but matches on text: "
                    f"{mem.text[:70]}")

    def test_precedent_respects_the_similarity_floor(self):
        for m in APP.merchants[:150]:
            for other, sim in APP._precedent(m):
                self.assertGreaterEqual(sim, config.PRECEDENT_MIN_SIMILARITY,
                                        f"{m.name} -> {other.name}")

    def test_refund_memory_ignores_a_low_refund_merchant(self):
        """The exact false positive: a clean subscription pitch, low refunds."""
        from riskmemory.signals import detect_memory
        m = next(x for x in APP.merchants if x.name == "Cardboard")
        self.assertLess(m.refund_rate, 0.15)
        titles = [s.title for s in detect_memory(m, APP.store)]
        self.assertEqual(titles, [], f"clean merchant matched: {titles}")


class TestPlatformData(unittest.TestCase):
    def test_acme_brand_palette_present(self):
        for key in ("lime", "forest", "blue", "ink"):
            self.assertRegex(config.BRAND[key], r"^#[0-9A-F]{6}$")

    def test_stylesheet_uses_the_brand_palette(self):
        css = (Path(__file__).parent.parent / "web" / "styles.css").read_text()
        for key in ("lime", "forest", "ink"):
            self.assertIn(config.BRAND[key], css,
                          f"brand {key} missing from stylesheet")


class TestStylesheetContrast(unittest.TestCase):
    """An element painted on a fixed brand colour must fix its text colour too.

    Regression: the digest pill used `color: var(--ink)` on `background: var(--lime)`.
    In dark mode --ink flips to near-white, so the label vanished against the lime.
    """

    def test_no_theme_dependent_text_on_a_fixed_background(self):
        import re
        css = (Path(__file__).parent.parent / "web" / "styles.css").read_text()
        offenders = []
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            bg = re.search(r"background(?:-color)?\s*:\s*([^;]+)", body)
            fg = re.search(r"(?<!-)color\s*:\s*([^;]+)", body)
            if not (bg and fg):
                continue
            bgv, fgv = bg.group(1).strip(), fg.group(1).strip()
            fixed_bg = bgv.startswith("#") or any(
                t in bgv for t in ("var(--lime", "var(--forest", "var(--brand"))
            theme_fg = any(t in fgv for t in
                           ("var(--ink", "var(--paper", "var(--muted", "var(--surface"))
            if fixed_bg and theme_fg:
                offenders.append(f"{sel.strip()} -> bg {bgv} / color {fgv}")
        self.assertEqual(offenders, [], "text colour flips with theme on a fixed background")


class TestDashboard(unittest.TestCase):
    def test_dashboard_is_json_safe_and_complete(self):
        import json
        d = APP.dashboard()
        json.dumps(d)
        for key in ("portfolio", "postures", "categories", "real_customers",
                    "operating", "platform"):
            self.assertIn(key, d)

    def test_all_four_postures_can_appear(self):
        names = {p["name"] for p in APP.dashboard()["postures"]}
        self.assertTrue(names <= set(config.POSTURES.values()), names)

    def test_dashboard_lists_every_real_customer_as_clean(self):
        for r in APP.dashboard()["real_customers"]:
            self.assertLess(r["p_bad"], config.DECLINE_THRESHOLD, r["name"])

    def test_activity_rides_on_the_dashboard(self):
        d = APP.dashboard()
        self.assertIn("activity", d)
        self.assertIn("activity_total", d)

    def test_no_persistent_summary_bar_anywhere(self):
        """The bar was removed: it duplicated the Dashboard."""
        web = Path(__file__).parent.parent / "web"
        for f in ("index.html", "app.js", "styles.css"):
            text = (web / f).read_text()
            for token in ("renderSummary", 'id="summary"', 'class="summary"', "digestBtn"):
                self.assertNotIn(token, text, f"{token} still in {f}")

    def test_brand_assets_present(self):
        assets = Path(__file__).parent.parent / "web" / "assets"
        self.assertTrue((assets / "acme-mark.svg").is_file())


class TestGraph(unittest.TestCase):
    def test_case_c_reaches_the_terminated_original(self):
        rel = APP.graph.related_merchants("m90003")
        targets = {APP.by_id[r.target].name for r in rel}
        self.assertIn("Vellum Reader", targets)
        self.assertIn("Bookly Cloud", targets)

    def test_corroborating_routes_are_kept(self):
        rel = APP.graph.related_merchants("m90003")
        vellum = next(r for r in rel if APP.by_id[r.target].name == "Vellum Reader")
        self.assertGreaterEqual(vellum.corroboration, 2)

    def test_hub_nodes_do_not_connect_everything(self):
        """A registrar shared by 900 merchants must not create relationships."""
        rel = APP.graph.related_merchants("m90011")
        self.assertLess(len(rel), 20)

    def test_subgraph_is_renderable(self):
        sg = APP.graph.subgraph("m90003", APP.graph.related_merchants("m90003")[:4])
        self.assertTrue(sg["nodes"] and sg["edges"])
        ids = {n["id"] for n in sg["nodes"]}
        for e in sg["edges"]:
            self.assertIn(e["src"], ids)
            self.assertIn(e["dst"], ids)


class TestMemory(unittest.TestCase):
    def store(self):
        return MemoryStore(prime_corpus=[m.pitch for m in APP.merchants])

    def test_add_update_invalidate_noop(self):
        s = self.store()
        a = "Merchants selling pirated ebook catalogues terminate frequently."
        self.assertEqual(s.reconcile(a, category="x", polarity="adverse",
                                     confidence=0.5).action, "ADD")
        self.assertEqual(s.reconcile(a, category="x", polarity="adverse",
                                     confidence=0.8).action, "UPDATE")
        self.assertEqual(s.reconcile(a, category="x", polarity="adverse",
                                     confidence=0.6).action, "NO-OP")

    def test_weak_contradiction_is_disputed_not_destructive(self):
        s = self.store()
        s.reconcile("Ebook catalogue merchants without licences go bad.",
                    category="x", polarity="adverse", confidence=0.9)
        r = s.reconcile("Ebook catalogue merchants without licences are fine.",
                        category="x", polarity="clearing", confidence=0.4)
        self.assertEqual(r.action, "DISPUTED")
        self.assertEqual(s.counts()["invalidated"], 0)

    def test_strong_contradiction_supersedes_rather_than_deletes(self):
        s = self.store()
        s.reconcile("Ebook catalogue merchants without licences go bad.",
                    category="x", polarity="adverse", confidence=0.4)
        r = s.reconcile("Ebook catalogue merchants without licences are fine.",
                        category="x", polarity="clearing", confidence=0.95)
        self.assertEqual(r.action, "INVALIDATE")
        self.assertEqual(r.against.status, "invalidated")
        self.assertIsNotNone(r.against.superseded_by)   # kept for audit

    def test_predicate_evaluator_rejects_unsafe_fields(self):
        m = APP.by_id["m90006"]
        self.assertTrue(evaluate_predicate(
            {"all": [{"field": "refund_rate", "op": ">=", "value": 0.12}]}, m))
        self.assertFalse(evaluate_predicate(
            {"all": [{"field": "__class__", "op": "==", "value": 1}]}, m))
        self.assertFalse(evaluate_predicate({"all": []}, m))
        self.assertFalse(evaluate_predicate(None, m))


class TestSignals(unittest.TestCase):
    def _sig_ids(self, mid):
        m = APP.by_id[mid]
        return {s.id.split(":")[0] for s in
                detect_all(m, APP.graph, APP.by_id, APP.portfolio_volume, APP.store)}

    def test_each_posture_fires_on_its_planted_case(self):
        self.assertIn("graph_link", self._sig_ids("m90003"))       # deceiving
        self.assertIn("category_drift", self._sig_ids("m90005"))   # drifting
        self.assertIn("prepaid_exposure", self._sig_ids("m90007")) # failing
        self.assertIn("payout_change", self._sig_ids("m90008"))    # attacked
        self.assertIn("card_testing", self._sig_ids("m90009"))     # attacked
        self.assertIn("volume_vs_forecast", self._sig_ids("m90010"))

    def test_clean_applicants_fire_nothing(self):
        for mid in ("m90011", "m90012"):
            self.assertEqual(self._sig_ids(mid), set())

    def test_detectors_never_read_ground_truth(self):
        """Detectors may only see what a human reviewer could see."""
        import ast
        src = (Path(__file__).parent.parent / "riskmemory" / "signals.py").read_text()
        reads = {n.attr for n in ast.walk(ast.parse(src))
                 if isinstance(n, ast.Attribute)}
        self.assertNotIn("truth_bad", reads)
        self.assertNotIn("truth_category", reads)
        self.assertNotIn("truth_note", reads)


class TestDecision(unittest.TestCase):
    def test_clean_applicants_are_approved(self):
        for mid in ("m90011", "m90012"):
            d = APP.brief(mid)["decision"]
            self.assertLess(d["p_bad"], config.DECLINE_THRESHOLD)
            self.assertEqual(d["recommendation"], "approve")

    def test_planted_cases_are_flagged(self):
        for mid in ("m90003", "m90004"):
            d = APP.brief(mid)["decision"]
            self.assertGreaterEqual(d["p_bad"], config.DECLINE_THRESHOLD)

    def test_victim_outcomes_excluded_from_precedent(self):
        """Card testing and ATO are not properties of the merchant's business."""
        class M:
            truth_bad = True
            truth_category = "card_testing"
            learned_bad = False
        lr, note = precedent_likelihood([(M(), 0.9)])
        self.assertLessEqual(lr, 1.0)
        self.assertIn("did not cause", note)

    def test_analyst_decline_counts_as_precedent(self):
        class M:
            truth_bad = False
            learned_bad = True
        lr, _note = precedent_likelihood([(M(), 0.5)])
        self.assertGreater(lr, 1.0)

    def test_expected_costs_bracket_the_threshold(self):
        d = decide([])
        self.assertLess(d.expected_cost_approve, d.expected_cost_decline)


class TestReplayGate(unittest.TestCase):
    def test_gate_promotes_a_pattern_that_helps(self):
        app = App()
        out = app.ingest_incident("m90006")           # deceptive billing
        self.assertGreater(out["caught_delta"], 0)
        self.assertLessEqual(out["false_flag_delta"], 0)
        self.assertTrue(out["promoted"])

    def test_gate_refuses_a_pattern_that_does_not_help(self):
        app = App()
        app.ingest_incident("m90006")
        again = app.ingest_incident("m90006")          # nothing new to learn
        self.assertFalse(again["promoted"])

    def test_candidate_is_inert_until_promoted(self):
        app = App()
        cand = distil(app.by_id["m90006"], app.store)
        self.assertFalse(cand.promoted)
        self.assertNotIn(cand.id, {m.id for m in app.store.active("semantic", True)})


class TestRetrievalStemming(unittest.TestCase):
    def test_plural_and_participle_forms_unify(self):
        from riskmemory.retrieval import stem
        self.assertEqual(stem("libraries"), stem("library"))
        self.assertEqual(stem("ebooks"), stem("ebook"))
        self.assertEqual(stem("subscriptions"), stem("subscription"))

    def test_stemmer_does_not_mangle_ordinary_words(self):
        from riskmemory.retrieval import stem
        for w in ("business", "analysis", "class", "seed", "status"):
            self.assertEqual(stem(w), w)


class TestAssess(unittest.TestCase):
    """POST /api/assess reuses the live engine and does not record a decision."""

    def test_existing_merchant_by_id(self):
        import json
        out = APP.assess({"merchant_id": "m90003"})
        json.dumps(out)
        self.assertEqual(out["merchant_id"], "m90003")
        self.assertFalse(out["created"])
        self.assertEqual(out["merchant"]["name"], "Lumen Labs")
        self.assertIn(out["decision"]["recommendation"],
                      ("approve", "conditions", "escalate", "decline"))
        self.assertTrue(out["risk_band"])
        self.assertTrue(out["why"])
        self.assertTrue(out["signals"])          # Case C is graph-linked
        self.assertTrue(out["graph"]["nodes"])
        self.assertTrue(out["memories"] or out["precedent"])

    def test_existing_merchant_by_name(self):
        out = APP.assess({"name": "kindle grove"})
        self.assertEqual(out["merchant_id"], "m90004")
        self.assertFalse(out["created"])
        self.assertEqual(APP.by_id["m90004"].status, "pending")

    def test_does_not_record_a_human_decision(self):
        app = App()
        before_status = app.by_id["m90003"].status
        before_rationale = app.by_id["m90003"].rationale
        before_mem = app.store.counts()["total"]
        app.assess({"merchant_id": "m90003"})
        m = app.by_id["m90003"]
        self.assertEqual(m.status, before_status)
        self.assertEqual(m.rationale, before_rationale)
        self.assertEqual(app.store.counts()["total"], before_mem)

    def test_missing_name_is_an_error(self):
        self.assertEqual(APP.assess({})["error"], "merchant name is required")
        self.assertEqual(APP.assess({"merchant_id": "nope"})["error"], "unknown merchant")
        self.assertEqual(
            APP.assess({"name": "Brand New Co"})["error"],
            "purpose is required for a new merchant")

    def test_new_merchant_then_decide(self):
        app = App()
        n_queue = len(app.queue())
        out = app.assess({
            "name": "Zed Analytics",
            "category": "saas",
            "country": "US",
            "purpose": "Team analytics dashboard for small product teams",
            "volume": 8000,
        })
        self.assertTrue(out["created"])
        mid = out["merchant_id"]
        self.assertTrue(mid.startswith("ma"))
        self.assertEqual(app.by_id[mid].status, "pending")
        self.assertEqual(len(app.queue()), n_queue + 1)
        # same engine the brief uses
        self.assertEqual(out["decision"]["recommendation"],
                         app.brief(mid)["decision"]["recommendation"])
        r = app.record_decision(mid, "approve",
                                "Clean analytics product, no adverse memory.")
        self.assertTrue(r["ok"])
        self.assertEqual(app.by_id[mid].status, "approved")
        self.assertEqual(len(app.queue()), n_queue)
        self.assertIn("action", r["reconciliation"])
        hist = app.assessments()
        self.assertEqual(hist[0]["decision_action"], "approve")
        self.assertIn("Clean analytics", hist[0]["decision_rationale"])
        self.assertEqual(hist[0]["brief"]["decisionRecorded"]["action"], "approve")
        self.assertEqual(hist[0]["brief"]["merchant"]["status"], "approved")

    def test_brief_and_queue_still_work(self):
        import json
        json.dumps(APP.brief("m90003"))
        json.dumps(APP.queue())
        self.assertEqual(
            APP.assess({"merchant_id": "m90003"})["decision"]["recommendation"],
            APP.brief("m90003")["decision"]["recommendation"])


class TestExplainEnv(unittest.TestCase):
    def test_explain_is_silent_without_a_key(self):
        import os
        from riskmemory.explain import explain_assessment
        prev = {k: os.environ.pop(k) for k in (
            "AWS_BEARER_TOKEN_BEDROCK", "ANTHROPIC_API_KEY") if k in os.environ}
        try:
            self.assertIsNone(explain_assessment({
                "merchant": {"name": "x"},
                "decision": {"headline": "Approve"},
            }))
        finally:
            os.environ.update(prev)

    def test_dotenv_does_not_override_live_env(self):
        import os, tempfile
        from pathlib import Path
        from riskmemory.explain import load_dotenv
        had_region = "AWS_REGION" in os.environ
        old_region = os.environ.get("AWS_REGION")
        os.environ["AWS_REGION"] = "eu-west-1"
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("AWS_REGION=us-east-1\nFAKE_DOTENV_FLAG=1\n")
            path = Path(f.name)
        try:
            load_dotenv(path)
            self.assertEqual(os.environ["AWS_REGION"], "eu-west-1")
            self.assertEqual(os.environ.get("FAKE_DOTENV_FLAG"), "1")
        finally:
            path.unlink(missing_ok=True)
            os.environ.pop("FAKE_DOTENV_FLAG", None)
            if had_region:
                os.environ["AWS_REGION"] = old_region
            else:
                os.environ.pop("AWS_REGION", None)


class TestApp(unittest.TestCase):
    def test_portfolio_is_json_safe(self):
        import json
        json.dumps(APP.portfolio())
        json.dumps(APP.queue())
        json.dumps(APP.brief("m90003"))

    def test_decision_writes_memory(self):
        app = App()
        before = app.store.counts()["total"]
        app.record_decision("m90011", "approve", "Clean CI analytics product.")
        self.assertGreater(app.store.counts()["total"], before)
        self.assertEqual(app.by_id["m90011"].status, "approved")

    def test_reset_restores_initial_state(self):
        app = App()
        n = len(app.queue())
        app.record_decision("m90011", "approve", "x")
        self.assertEqual(len(app.queue()), n - 1)
        app.reset()
        self.assertEqual(len(app.queue()), n)

    def test_assessments_persist_to_disk(self):
        import os
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "assessments.json"
            os.environ["RISKMEMORY_ASSESSMENTS_FILE"] = str(store)
            try:
                app = App()
                app.assess({"name": "Zed Tools", "purpose": "B2B invoicing", "web": False})
                self.assertTrue(store.is_file())
                app.record_decision(
                    app.assessments()[0]["merchant_id"], "decline", "Not a fit.")
                app.reset()
                self.assertEqual(len(app.assessments()), 1)
                self.assertEqual(app.assessments()[0]["decision_action"], "decline")
                app2 = App()
                self.assertEqual(len(app2.assessments()), 1)
                self.assertEqual(app2.assessments()[0]["name"], "Zed Tools")
            finally:
                os.environ.pop("RISKMEMORY_ASSESSMENTS_FILE", None)


class TestAssessDifferentiation(unittest.TestCase):
    """Dummy merchants must not all collapse to the 1.7% base rate."""

    def setUp(self) -> None:
        import os
        import tempfile
        self._assess_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self._assess_tmp.close()
        os.environ["RISKMEMORY_ASSESSMENTS_FILE"] = self._assess_tmp.name

    def tearDown(self) -> None:
        import os
        os.environ.pop("RISKMEMORY_ASSESSMENTS_FILE", None)
        os.unlink(self._assess_tmp.name)

    def test_generic_saas_stays_near_the_base_rate(self):
        app = App()
        out = app.assess({
            "name": "Cedar Home SaaS", "category": "saas", "country": "GB",
            "purpose": "Inventory software for independent furniture retailers",
            "web": False,
        })
        self.assertAlmostEqual(out["decision"]["p_bad"], config.CONFIRMED_BAD_RATE, delta=0.02)
        self.assertEqual(out["web"]["status"], "skipped")
        self.assertTrue(app.assessments())

    def test_gambling_copy_scores_higher_than_generic_saas(self):
        app = App()
        clean = app.assess({
            "name": "Cedar Home SaaS", "purpose": "Inventory software for retailers",
            "web": False,
        })
        risky = app.assess({
            "name": "Nightline Casino",
            "purpose": "Online casino and sportsbook with crypto deposits",
            "web": False,
        })
        self.assertGreater(risky["decision"]["p_bad"], clean["decision"]["p_bad"] + 0.03)
        self.assertTrue(risky["signals"])
        self.assertEqual(len(app.assessments()), 2)

    def test_lumen_still_comes_back_hot(self):
        out = APP.assess({"merchant_id": "m90003", "web": False})
        self.assertGreater(out["decision"]["p_bad"], 0.5)
        self.assertEqual(out["decision"]["recommendation"], "decline")

    def test_history_is_session_assessments(self):
        app = App()
        app.assess({"name": "Zed Tools", "purpose": "B2B invoicing", "web": False})
        self.assertEqual(len(app.assessments()), 1)
        self.assertEqual(app.assessments()[0]["name"], "Zed Tools")

    def test_decision_stamps_every_history_row_for_that_merchant(self):
        app = App()
        app.assess({"name": "Zed Tools", "purpose": "B2B invoicing", "web": False})
        app.assess({"name": "Zed Tools", "purpose": "B2B invoicing", "web": False})
        mid = app.assessments()[0]["merchant_id"]
        app.record_decision(mid, "decline", "Not a fit.")
        rows = [r for r in app.assessments() if r["merchant_id"] == mid]
        self.assertEqual([r["decision_action"] for r in rows], ["decline", "decline"])
        self.assertTrue(all(r["brief"]["decisionRecorded"]["action"] == "decline" for r in rows))

    def test_theme_matcher_catches_casino_language(self):
        from riskmemory.websearch import match_themes
        themes = {t["theme"] for t in match_themes("an online casino and sportsbook")}
        self.assertIn("gambling", themes)

    def test_analyst_decline_heats_a_similar_later_applicant(self):
        """A recorded decline must move P(bad) for the next similar merchant."""
        app = App()
        first = app.assess({
            "name": "Nightline Casino",
            "purpose": "Online casino and sportsbook with crypto deposits",
            "web": False,
        })
        p_before = first["decision"]["p_bad"]
        rec = app.record_decision(
            first["merchant_id"], "decline",
            "Gambling is not a vertical we will underwrite.")
        self.assertTrue(rec["ok"])
        self.assertTrue(app.by_id[first["merchant_id"]].learned_bad)
        later = app.assess({
            "name": "Harbor Sportsbook",
            "purpose": "Online casino and sportsbook with crypto deposits",
            "web": False,
        })
        self.assertGreater(later["decision"]["p_bad"], p_before)
        self.assertTrue(any(
            (s.get("id") or "").startswith("memory:")
            or s.get("category") == "precedent"
            for s in later["signals"]))
        self.assertTrue(any(p.get("went_bad") for p in later.get("precedent") or []))

    def test_analyst_decline_heats_different_wording_same_vertical(self):
        """Decline memory must match on vertical themes, not identical copy."""
        app = App()
        first = app.assess({
            "name": "casino king",
            "purpose": "casino sportsbook crypto",
            "web": False,
        })
        mid = first["merchant_id"]
        app.by_id[mid].web_report = {
            "status": "found",
            "themes": [{"theme": "gambling", "matched": "casino", "lr": 8.5}],
            "hits": [],
        }
        app.record_decision(mid, "decline", "Gambling MoR.")
        later = app.assess({
            "name": "gambler ninjas",
            "purpose": "gambling ninjas betting app",
            "web": False,
        })
        lm = app.by_id[later["merchant_id"]]
        lm.web_report = {
            "status": "found",
            "themes": [{"theme": "gambling", "matched": "gambling", "lr": 8.5}],
            "hits": [],
        }
        from riskmemory.signals import detect_all
        from riskmemory.decision import decide
        sigs = detect_all(lm, app.graph, app.by_id, app.portfolio_volume, app.store)
        dec = decide(sigs, app._precedent(lm))
        self.assertGreater(dec.p_bad, first["decision"]["p_bad"] + 0.05)
        self.assertTrue(any(s.posture == "memory" for s in sigs))

    def test_analyst_decline_does_not_heat_an_unrelated_saas(self):
        app = App()
        first = app.assess({
            "name": "Nightline Casino",
            "purpose": "Online casino and sportsbook with crypto deposits",
            "web": False,
        })
        app.record_decision(first["merchant_id"], "decline", "Prohibited vertical.")
        saas = app.assess({
            "name": "Cedar Ledger",
            "purpose": "Inventory software for independent furniture retailers",
            "web": False,
        })
        self.assertAlmostEqual(
            saas["decision"]["p_bad"], config.CONFIRMED_BAD_RATE, delta=0.03)

    def test_services_signup_is_a_hard_decline(self):
        app = App()
        out = app.assess({
            "name": "Quill Harbor Freelance Co",
            "signup_category": "services",
            "country": "US",
            "purpose": "Custom design and freelance coaching for founders",
            "web": False,
        })
        self.assertEqual(out["decision"]["recommendation"], "decline")
        self.assertTrue(any(s["id"].startswith("policy:") for s in out["signals"]))

    def test_restricted_country_blocks_onboarding(self):
        app = App()
        out = app.assess({
            "name": "Cedar PK Ledger Co",
            "signup_category": "saas_ai_digital",
            "country": "PK",
            "purpose": "Inventory software for independent furniture retailers",
            "web": False,
        })
        self.assertIn(out["decision"]["recommendation"], ("decline", "escalate"))
        self.assertTrue(any(s["id"] == "geo:restricted" for s in out["signals"]))

    def test_nightwell_hours_mismatch_fires(self):
        app = App()
        out = app.assess({"merchant_id": "m90020", "web": False})
        ids = [s["id"] for s in out["signals"]]
        self.assertIn("hours_mismatch", ids)
        self.assertGreater(out["decision"]["p_bad"], 0.10)
        hours = next(s for s in out["signals"] if s["id"] == "hours_mismatch")
        blob = hours["title"] + " " + hours["detail"] + " " + " ".join(hours["evidence"])
        self.assertIn("IST", blob)
        self.assertIn("Asia/Kolkata", blob)
        self.assertIn("not UTC", hours["detail"])

    def test_night_window_is_country_local_not_utc(self):
        in_lbl = config.local_night_label("IN")
        us_lbl = config.local_night_label("US")
        self.assertIn("IST", in_lbl)
        self.assertIn("ET", us_lbl)
        self.assertNotEqual(in_lbl, us_lbl)
        self.assertIn("22:00", in_lbl)
        self.assertIn("22:00", us_lbl)

    def test_accepted_category_with_service_copy_is_a_mismatch(self):
        app = App()
        out = app.assess({
            "name": "Northline Consulting Pack",
            "signup_category": "saas_ai_digital",
            "country": "US",
            "purpose": "Done for you consulting and freelance coaching packaged as a dashboard",
            "web": False,
        })
        self.assertTrue(any(s["id"] == "mismatch:services" for s in out["signals"]))
        self.assertGreater(out["decision"]["p_bad"], config.CONFIRMED_BAD_RATE + 0.05)

    def test_legacy_saas_category_still_maps(self):
        app = App()
        out = app.assess({
            "name": "Zed Pipeline",
            "category": "saas",
            "purpose": "Team analytics dashboard for small product teams",
            "web": False,
        })
        self.assertEqual(app.by_id[out["merchant_id"]].category_claimed, "saas")


class TestInboundApplications(unittest.TestCase):
    """Merchant-submitted Acme packets can be imported instead of retyped."""

    def test_inbox_lists_seeded_packets(self):
        from riskmemory.applications import list_applications
        ids = {row["id"] for row in list_applications()}
        self.assertTrue({"app_lumen", "app_services", "app_geo", "app_nightwell"} <= ids)

    def test_unknown_application_id_errors(self):
        out = App().assess({"application_id": "app_missing", "web": False})
        self.assertEqual(out.get("error"), "unknown application")

    def test_import_alone_is_enough_to_assess(self):
        app = App()
        out = app.assess({"application_id": "app_services", "web": False})
        self.assertNotIn("error", out)
        self.assertEqual(out["merchant"]["name"], "Quill Harbor Freelance Co")
        self.assertEqual(out["decision"]["recommendation"], "decline")
        self.assertTrue(any(s["id"].startswith("policy:") for s in out["signals"]))

    def test_imported_restricted_country_still_blocks(self):
        out = App().assess({"application_id": "app_geo", "web": False})
        self.assertTrue(any(s["id"] == "geo:restricted" for s in out["signals"]))

    def test_form_overrides_win_over_the_packet(self):
        out = App().assess({
            "application_id": "app_geo",
            "country": "US",
            "web": False,
        })
        self.assertFalse(any(s["id"] == "geo:restricted" for s in out["signals"]))

    def test_audience_timezone_mismatch_fires_at_signup(self):
        """IN edtech selling live EST classes — Nightwell, before any volume."""
        app = App()
        out = app.assess({"application_id": "app_audience", "web": False})
        ids = [s["id"] for s in out["signals"]]
        self.assertIn("audience:tz", ids)
        self.assertNotIn("hours_mismatch", ids)
        self.assertGreater(out["decision"]["p_bad"], config.CONFIRMED_BAD_RATE + 0.05)
        m = app.by_id[out["merchant_id"]]
        self.assertEqual(m.settled_txns, 0)

    def test_low_value_digital_pack_is_flagged(self):
        out = App().assess({"application_id": "app_lowvalue", "web": False})
        self.assertTrue(any(s["id"] == "price:low_value" for s in out["signals"]))

    def test_individual_claiming_university_is_flagged(self):
        out = App().assess({"application_id": "app_solo_uni", "web": False})
        self.assertTrue(any(s["id"] == "entity:solo_institution" for s in out["signals"]))

    def test_stylesheet_is_light(self):
        css = (Path(__file__).parent.parent / "web" / "styles.css").read_text()
        self.assertIn("color-scheme:light", css.replace(" ", ""))
        self.assertNotIn("#C6FE1E", css)
        js = (Path(__file__).parent.parent / "web" / "app.js").read_text()
        self.assertIn("flagEmoji", js)
        self.assertIn("/api/applications", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
