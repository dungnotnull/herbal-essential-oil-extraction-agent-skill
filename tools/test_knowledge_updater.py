"""
test_knowledge_updater.py — Skill 289: herbal-essential-oil-extraction
Validation: hash dedup, scoring, entry formatting.
"""
import sys, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import knowledge_updater as ku

def test_hash():
    a = ku.compute_hash("https://x.com/1"); b = ku.compute_hash("https://x.com/1")
    assert a == b and ku.compute_hash("https://x.com/2") != a
    print("[OK] dedup hash")

def test_score():
    e = {"title": ku.KNOWLEDGE_CONFIG["domain"], "abstract": ku.KNOWLEDGE_CONFIG["domain"],
         "published_date": datetime.datetime.now(), "citation_count": 10}
    s = ku.score_entry(e, ku.KNOWLEDGE_CONFIG["keywords"], datetime.datetime.now())
    assert 0 <= s <= 10
    print("[OK] score=" + str(s))

def test_format():
    txt = ku.format_entry({"title": "T", "authors": ["A"], "year": 2026, "venue": "V",
                           "doi_or_url": "https://x", "abstract": "ab"}, 5.0)
    assert "DOI/URL:" in txt and "Relevance Score:" in txt
    print("[OK] format")

if __name__ == "__main__":
    test_hash(); test_score(); test_format()
    print("all knowledge_updater tests passed")