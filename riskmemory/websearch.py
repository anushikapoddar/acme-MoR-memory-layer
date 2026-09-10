"""Public-web lookup for an applicant, stdlib only.

Wikipedia and DuckDuckGo expose JSON with no API key. The engine still decides
from likelihood ratios — this module only gathers text a reviewer could Google.
Set RISKMEMORY_WEB=0 to skip the network (tests do this).
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Optional

UA = "AcmeMerchantRiskMemory/1.0 (underwriting-demo; local)"
TIMEOUT = 5

#: Phrases a reviewer would treat as elevated risk if they appear in the
#: application or in public pages about the company.
RISK_THEMES: list[tuple[str, float, tuple[str, ...]]] = [
    ("gambling", 8.5, ("online casino", "sportsbook", "gambling", "sports betting",
                       "slot machine", "poker site", "betting shop")),
    ("adult", 10.0, ("porn", "xxx video", "adult webcam", "onlyfans", "escort")),
    ("binary_options", 9.0, ("binary option", "cfd broker", "forex robot")),
    ("crypto_high_risk", 5.5, ("crypto mixer", "tumbler", "unhosted wallet",
                               "token sale", "initial coin offering")),
    ("gift_cards", 4.5, ("gift card mall", "stored value card", "money service")),
    ("crypto", 2.3, ("cryptocurrency", "crypto exchange", "bitcoin")),
    ("nutra_spam", 2.1, ("nutraceutical", "male enhancement", "miracle diet")),
]


class _Strip(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []

    def handle_data(self, data: str) -> None:
        self._buf.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._buf)).strip()


def _plain(html: str) -> str:
    p = _Strip()
    try:
        p.feed(html or "")
        p.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html or "")
    return p.text()


def enabled(payload: Optional[dict] = None) -> bool:
    if payload and str(payload.get("web", "1")).lower() in ("0", "false", "no", "off"):
        return False
    return os.environ.get("RISKMEMORY_WEB", "1").lower() not in ("0", "false", "off", "no")


def skipped(reason: str = "disabled") -> dict:
    return {"status": "skipped", "reason": reason, "query": "", "hits": [], "themes": []}


def lookup(name: str, country: str = "", purpose: str = "",
           website: str = "") -> dict:
    """Fetch public pages about this company. Never raises."""
    name = (name or "").strip()
    if not name:
        return skipped("no name")
    query = " ".join(p for p in (name, website or "", "company", country) if p)
    hits: list[dict] = []
    errors: list[str] = []
    for fn in (_wikipedia, _duckduckgo):
        try:
            hits.extend(fn(query))
        except Exception as exc:
            errors.append(f"{fn.__name__}: {exc}")
        if len(hits) >= 5:
            break
    # de-dupe by URL / title
    seen: set[str] = set()
    uniq: list[dict] = []
    for h in hits:
        key = (h.get("url") or h.get("title") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(h)
        if len(uniq) == 6:
            break
    blob = " ".join(
        [name, purpose or "", website or ""]
        + [f"{h.get('title','')} {h.get('snippet','')}" for h in uniq]
    )
    themes = match_themes(blob)
    status = "found" if uniq else ("error" if errors else "empty")
    return {
        "status": status,
        "reason": "; ".join(errors) if errors and not uniq else "",
        "query": query,
        "hits": uniq,
        "themes": themes,
    }


def match_themes(text: str) -> list[dict]:
    blob = f" {re.sub(r'[^a-z0-9]+', ' ', (text or '').lower())} "
    out = []
    for theme, lr, phrases in RISK_THEMES:
        hit = next((p for p in phrases if p in blob), None)
        if hit:
            out.append({"theme": theme, "lr": lr, "matched": hit})
    return out


def _get_json(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _wikipedia(query: str) -> list[dict]:
    q = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": query,
        "utf8": "1", "format": "json", "srlimit": "5", "srprop": "snippet",
    })
    data = _get_json(f"https://en.wikipedia.org/w/api.php?{q}")
    hits = []
    for row in (data.get("query") or {}).get("search") or []:
        title = row.get("title") or ""
        slug = urllib.parse.quote(title.replace(" ", "_"))
        hits.append({
            "title": title,
            "snippet": _plain(row.get("snippet") or ""),
            "url": f"https://en.wikipedia.org/wiki/{slug}",
            "source": "wikipedia",
        })
    return hits


def _duckduckgo(query: str) -> list[dict]:
    q = urllib.parse.urlencode({
        "q": query, "format": "json", "no_html": "1", "skip_disambig": "1",
    })
    data = _get_json(f"https://api.duckduckgo.com/?{q}")
    hits = []
    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        hits.append({
            "title": data.get("Heading") or query,
            "snippet": abstract[:400],
            "url": data.get("AbstractURL") or "",
            "source": "duckduckgo",
        })
    for item in (data.get("RelatedTopics") or [])[:4]:
        if not isinstance(item, dict) or not item.get("Text"):
            continue
        hits.append({
            "title": item["Text"][:90],
            "snippet": item["Text"][:400],
            "url": item.get("FirstURL") or "",
            "source": "duckduckgo",
        })
    return hits
