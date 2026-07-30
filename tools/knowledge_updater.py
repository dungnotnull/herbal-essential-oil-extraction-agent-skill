"""
knowledge_updater.py — Skill 289: herbal-essential-oil-extraction
Crawl pipeline: fetches latest papers + news -> scores -> appends to
SECOND-KNOWLEDGE-BRAIN.md.

Dependencies: pip install requests feedparser python-dateutil
Usage:
    python tools/knowledge_updater.py [--dry-run] [--news-only] [--keywords ...]
"""
import argparse, hashlib, math, re, time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None
try:
    import feedparser
except ImportError:
    feedparser = None

# ---------------- KNOWLEDGE_CONFIG (per-project) ----------------
KNOWLEDGE_CONFIG = {
    "domain": "Essential Oil Extraction & Aromatic Chemistry",
    "keywords": [
        "essential oil extraction",
        "steam hydrodistillation SFE CO2",
        "GC-MS essential oil profile",
        "extraction yield parameters",
        "essential oil aroma degradation",
        "ISO 4720 essential oil standard"
    ],
    "arxiv_categories": [],
    "arxiv_base": "https://export.arxiv.org/api/query",
    "semantic_scholar_base": "https://api.semanticscholar.org/graph/v1/paper/search",
    "rss_feeds": [],
    "authoritative_docs": [
        "Industrial Crops and Products — Elsevier",
        "Journal of Agricultural and Food Chemistry — ACS",
        "Food Chemistry — Elsevier",
        "Journal of Essential Oil Research — Taylor & Francis",
        "Molecules (MDPI)",
        "Separation and Purification Technology — Elsevier"
    ],
    "scoring_weights": {
        "recency": 0.4,
        "keyword_relevance": 0.4,
        "citation_count": 0.2
    },
    "max_results_per_source": 10,
    "max_new_entries_per_run": 20
}
# ---------------------------------------------------------------

BRAIN_PATH = Path(__file__).parent.parent / "SECOND-KNOWLEDGE-BRAIN.md"


def fetch_with_retry(url, params=None, max_retries=3, base_delay=2.0):
    if requests is None:
        return None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(base_delay * (2 ** attempt))
            resp = requests.get(url, params=params or {}, timeout=30)
            if resp.status_code == 429:
                print("[WARN] 429 on attempt " + str(attempt + 1))
                if attempt < max_retries - 1:
                    continue
                return None
            if resp.status_code >= 500:
                if attempt < max_retries - 1:
                    continue
                return None
            resp.raise_for_status()
            return resp
        except Exception as ex:
            print("[WARN] request failed attempt " + str(attempt + 1) + ": " + str(ex))
            if attempt < max_retries - 1:
                time.sleep(base_delay)
            else:
                return None
    return None


def compute_hash(identifier):
    return hashlib.sha256(identifier.strip().lower().encode()).hexdigest()


def load_existing_hashes():
    if not BRAIN_PATH.exists():
        return set()
    hashes = set()
    for m in re.finditer(r"\*\*DOI/URL:\*\*\s*(\S+)", BRAIN_PATH.read_text(encoding="utf-8")):
        hashes.add(compute_hash(m.group(1)))
    return hashes


def score_entry(entry, keywords, now):
    pub = entry.get("published_date")
    recency = 0.0
    if pub:
        try:
            recency = max(0.0, 1.0 - (now - pub).days / 730.0)
        except Exception:
            recency = 0.0
    text = ((entry.get("title") or "") + " " + (entry.get("abstract") or "")).lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    relevance = min(hits / max(len(keywords), 1), 1.0)
    cit = entry.get("citation_count", 0) or 0
    cit_score = min(math.log1p(cit) / math.log1p(1000), 1.0)
    w = KNOWLEDGE_CONFIG["scoring_weights"]
    return round((recency * w["recency"] + relevance * w["keyword_relevance"]
                  + cit_score * w["citation_count"]) * 10.0, 2)


def fetch_arxiv(keywords):
    if requests is None or not KNOWLEDGE_CONFIG["arxiv_categories"]:
        return []
    cats = KNOWLEDGE_CONFIG["arxiv_categories"]
    q = "(" + " OR ".join("cat:" + c for c in cats) + ") AND (" + " OR ".join('"' + k + '"' for k in keywords[:5]) + ")"
    resp = fetch_with_retry(KNOWLEDGE_CONFIG["arxiv_base"], {
        "search_query": q, "sortBy": "submittedDate", "sortOrder": "descending",
        "max_results": KNOWLEDGE_CONFIG["max_results_per_source"]})
    if resp is None:
        return []
    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(resp.content)
    except Exception:
        return []
    out = []
    for entry in root.findall("atom:entry", ns):
        t = entry.find("atom:title", ns); s = entry.find("atom:summary", ns)
        i = entry.find("atom:id", ns); p = entry.find("atom:published", ns)
        title = (t.text or "").strip().replace("\n", " ") if t is not None else ""
        url = (i.text or "").strip() if i is not None else ""
        if not title or not url:
            continue
        pub = None
        if p is not None:
            try:
                from dateutil import parser as dp
                pub = dp.parse(p.text).replace(tzinfo=None)
            except Exception:
                pass
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns) if a.find("atom:name", ns) is not None][:3]
        out.append({"title": title, "authors": authors, "year": pub.year if pub else datetime.now().year,
                    "venue": "ArXiv", "doi_or_url": url, "abstract": (s.text or "")[:300] if s is not None else "",
                    "published_date": pub, "citation_count": 0, "source": "arxiv"})
    print("[INFO] ArXiv: " + str(len(out)))
    return out


def fetch_semantic_scholar(keywords):
    if requests is None:
        return []
    resp = fetch_with_retry(KNOWLEDGE_CONFIG["semantic_scholar_base"], {
        "query": " ".join(keywords[:4]),
        "fields": "title,authors,year,venue,externalIds,abstract,citationCount",
        "limit": KNOWLEDGE_CONFIG["max_results_per_source"]})
    if resp is None:
        return []
    try:
        data = resp.json()
    except Exception:
        return []
    out = []
    for p in data.get("data", []):
        title = p.get("title", "")
        if not title:
            continue
        year = p.get("year") or datetime.now().year
        ext = p.get("externalIds", {})
        doi = ext.get("DOI") or (f"https://arxiv.org/abs/{ext['ArXiv']}" if ext.get("ArXiv") else "")
        if not doi:
            doi = "https://www.semanticscholar.org/paper/" + str(p.get("paperId", ""))
        out.append({"title": title, "authors": [a.get("name", "") for a in p.get("authors", [])[:3]],
                    "year": year, "venue": p.get("venue") or "Unknown", "doi_or_url": doi,
                    "abstract": (p.get("abstract") or "")[:300], "published_date": datetime(year, 1, 1),
                    "citation_count": p.get("citationCount", 0), "source": "semantic_scholar"})
    print("[INFO] Semantic Scholar: " + str(len(out)))
    return out


def fetch_rss():
    if feedparser is None or not KNOWLEDGE_CONFIG["rss_feeds"]:
        return []
    out = []
    for url in KNOWLEDGE_CONFIG["rss_feeds"]:
        try:
            feed = feedparser.parse(url)
        except Exception as ex:
            print("[WARN] RSS " + url + " failed: " + str(ex)); continue
        for item in feed.entries[:10]:
            title = item.get("title", ""); link = item.get("link", "")
            if not title or not link:
                continue
            pp = item.get("published_parsed")
            pub = datetime(*pp[:6]) if pp else datetime.now()
            out.append({"title": title, "authors": ["Editorial"], "year": pub.year, "venue": "RSS",
                        "doi_or_url": link, "abstract": (item.get("summary", ""))[:200],
                        "published_date": pub, "citation_count": 0, "source": "rss"})
    print("[INFO] RSS: " + str(len(out)))
    return out


def format_entry(entry, score):
    d = datetime.now().strftime("%Y-%m-%d")
    authors = ", ".join(entry.get("authors", [])) or "Unknown"
    return (
        "\n### " + d + " — " + entry.get("title", "Untitled") + "\n"
        "- **Authors:** " + authors + "\n"
        "- **Year:** " + str(entry.get("year", "")) + "\n"
        "- **Venue:** " + entry.get("venue", "Unknown") + "\n"
        "- **DOI/URL:** " + entry.get("doi_or_url", "") + "\n"
        "- **Relevance Score:** " + str(score) + "/10\n"
        "- **Key Finding:** " + entry.get("abstract", "No abstract available.") + "\n"
    )


def append_to_brain(entries, dry_run=False):
    if not BRAIN_PATH.exists():
        print("[ERROR] brain not found: " + str(BRAIN_PATH)); return 0
    existing = load_existing_hashes()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new = []
    for e in entries:
        doi = e.get("doi_or_url", "")
        if not doi:
            continue
        h = compute_hash(doi)
        if h in existing:
            continue
        existing.add(h); new.append(e)
    if not new:
        print("[INFO] no new entries"); return 0
    for e in new:
        e["_score"] = score_entry(e, KNOWLEDGE_CONFIG["keywords"], now)
    new.sort(key=lambda x: x["_score"], reverse=True)
    new = new[:KNOWLEDGE_CONFIG["max_new_entries_per_run"]]
    text = "".join(format_entry(e, e["_score"]) for e in new)
    if dry_run:
        print("[DRY] would append " + str(len(new))); return len(new)
    content = BRAIN_PATH.read_text(encoding="utf-8")
    if "## 7. Knowledge Update Log" in content:
        content += text
    else:
        content += "\n## 7. Knowledge Update Log\n" + text
    BRAIN_PATH.write_text(content, encoding="utf-8")
    print("[INFO] appended " + str(len(new)))
    return len(new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--news-only", action="store_true")
    ap.add_argument("--keywords", nargs="+", default=KNOWLEDGE_CONFIG["keywords"])
    args = ap.parse_args()
    print("[START] " + datetime.now().isoformat() + " dry=" + str(args.dry_run) + " news=" + str(args.news_only))
    all_entries = []
    if not args.news_only:
        all_entries += fetch_arxiv(args.keywords); time.sleep(1)
        all_entries += fetch_semantic_scholar(args.keywords); time.sleep(1)
    all_entries += fetch_rss()
    print("[INFO] candidates: " + str(len(all_entries)))
    n = append_to_brain(all_entries, args.dry_run)
    print("[DONE] appended " + str(n))


if __name__ == "__main__":
    main()