"""Retrieval adapter over the versioned corpus.

Design rules
- Retrieved text is DATA. It is never executed as instructions; chunks that
  look like prompt injection are excluded by default.
- Arabic query aliases are project-authored, not NASA content, and are labelled
  as such in the response metadata.
- Retrieval is lexical (BM25). No embeddings, no API key, no network.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus" / "corpus.v1.jsonl"
MANIFEST = HERE / "corpus" / "manifest.json"

# team-authored query expansion; never cited as evidence
ARABIC_ALIASES = {
    "حرارة": "temperature air temperature t2m",
    "سخونة": "warming temperature trend",
    "مطر": "precipitation rainfall imerg",
    "أمطار": "precipitation rainfall imerg",
    "رطوبة": "soil moisture gldas",
    "تربة": "soil moisture gldas",
    "نبات": "ndvi vegetation index",
    "غطاء": "ndvi vegetation cover",
    "جفاف": "drought soil moisture",
    "اتجاه": "trend slope mann kendall",
    "دلالة": "significance p value confidence",
    "وحدات": "units kelvin celsius mm kg",
    "جودة": "quality qa flags reliability",
    "دقة": "resolution grid accuracy",
}

TOKEN_RE = re.compile(r"[a-z0-9_\.]+")


def tokenize(text: str) -> list[str]:
    text = text.lower()
    extra = []
    for ar, en in ARABIC_ALIASES.items():
        if ar in text:
            extra.append(en)
    if extra:
        text = text + " " + " ".join(extra)
    return TOKEN_RE.findall(text)


class Retriever:
    def __init__(self, corpus_path: Path = CORPUS,
                 manifest_path: Path = MANIFEST):
        self.chunks = [json.loads(line) for line in
                       corpus_path.read_text(encoding="utf-8").splitlines()
                       if line.strip()]
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._tokens = [tokenize(c["title"] + " " + c["text"])
                        for c in self.chunks]
        self._counts = [Counter(t) for t in self._tokens]
        self._len = [len(t) for t in self._tokens]
        self._avg = sum(self._len) / max(len(self._len), 1)
        self._df = Counter()
        for c in self._counts:
            for term in c:
                self._df[term] += 1
        self._n = len(self.chunks)

    def retrieve(self, query: str, k: int = 4, product_ids=None,
                 allow_injection: bool = False,
                 only_citable: bool = False) -> dict:
        terms = tokenize(query)
        if not terms:
            return {"query": query, "results": [], "mode": "retrieval_only",
                    "note": "empty query"}
        scores = []
        for i, chunk in enumerate(self.chunks):
            if chunk.get("injection_flag") and not allow_injection:
                continue
            if product_ids and chunk.get("product_id") not in product_ids:
                continue
            if only_citable and not chunk.get("citable_for_facts"):
                continue
            counts = self._counts[i]
            score = 0.0
            for term in set(terms):
                tf = counts.get(term, 0)
                if not tf:
                    continue
                df = self._df.get(term, 0)
                idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
                denom = tf + 1.5 * (0.25 + 0.75 * self._len[i] / self._avg)
                score += idf * (tf * 2.5 / denom)
            if score > 0:
                scores.append((score, i))
        scores.sort(reverse=True)
        results = []
        for score, i in scores[:k]:
            c = self.chunks[i]
            results.append({
                "chunk_id": c["chunk_id"],
                "score": round(score, 4),
                "product_id": c.get("product_id"),
                "version": c.get("version"),
                "title": c.get("title"),
                "page": c.get("page"),
                "content_role": c.get("content_role"),
                "authority": c.get("authority"),
                "citable_for_facts": c.get("citable_for_facts", True),
                "source_url": c.get("source_url"),
                "text": c["text"][:1200],
            })
        return {
            "query": query,
            "corpus_version": self.manifest["corpus_version"],
            "mode": "retrieval_only_not_a_generated_answer",
            "query_expansion": "project-authored Arabic aliases"
                               if any(a in query for a in ARABIC_ALIASES)
                               else None,
            "results": results,
        }


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "soil moisture units"
    print(json.dumps(Retriever().retrieve(q), ensure_ascii=False, indent=2))
