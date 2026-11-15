"""Build the versioned RAG corpus.

Sources, in order of authority:
1. NASA official product documentation already shipped in data/nasa/rag
   (metadata + GLDAS/ MERRA-2 guides + software method docs).
2. NASA GPM IMERG ATBD and MODIS MOD13 user guide (PDF, page-tagged).
3. NASA CMR collection metadata for GPM and MODIS.
4. Team-authored policy notes (QA rules, interpretation wording) — labelled
   `team_authored_policy` and `citable_for_facts: false`, never mixed with
   official evidence.

Every chunk carries: product, version, source URL, source sha256, page where
applicable, and an injection flag when the text contains instruction-like
content (retrieved text is data, never instructions).

Run:  python ai/corpus_build.py
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "nasa"
OUT_DIR = Path(__file__).resolve().parent / "corpus"
CHUNK_CHARS = 1400

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (the )?(system|previous) prompt",
    r"you (must|should) (now )?(output|print|reveal)",
    r"reveal (your )?(system )?prompt",
    r"^\s*system\s*:",
    r"new instructions?\s*:",
    r"act as (a|an) ",
    r"override (the )?(rules|policy)",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flag_injection(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low, re.MULTILINE) for p in INJECTION_PATTERNS)


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, size: int = CHUNK_CHARS) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts, buf = [], ""
    for para in re.split(r"\n\n+", text):
        if len(buf) + len(para) + 2 <= size:
            buf = f"{buf}\n\n{para}".strip()
        else:
            if buf:
                parts.append(buf)
            while len(para) > size:
                parts.append(para[:size])
                para = para[size:]
            buf = para
    if buf:
        parts.append(buf)
    return [p for p in parts if len(p.strip()) > 80]


def load_existing() -> list[dict]:
    path = DATA / "rag" / "corpus.jsonl"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            r["authority"] = "official_nasa"
            r["citable_for_facts"] = True
            rows.append(r)
    return rows


def pdf_chunks(path: Path, product: str, version: str, title: str,
               url: str) -> list[dict]:
    digest = sha256_file(path)
    reader = PdfReader(str(path))
    out = []
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        for i, part in enumerate(chunk_text(text)):
            out.append({
                "chunk_id": f"{product}:guide:p{page_no}:{i}",
                "product_id": product,
                "version": version,
                "title": title,
                "text": part,
                "source_url": url,
                "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": digest,
                "page": page_no,
                "content_role": "official_documentation_not_measurements",
                "authority": "official_nasa",
                "citable_for_facts": True,
                "retrieved_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"),
            })
    return out


def collection_chunks(path: Path, product: str, version: str) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    item = data["items"][0]
    umm = item["umm"]
    cid = item["meta"]["concept-id"]
    url = (f"https://cmr.earthdata.nasa.gov/search/collections.umm_json"
           f"?concept_id={cid}")
    digest = sha256_file(path)
    title = umm.get("EntryTitle", product)
    out = []
    bodies = [("abstract", umm.get("Abstract", "")),
              ("coverage", json.dumps({
                  "TemporalExtents": umm.get("TemporalExtents"),
                  "SpatialExtent": umm.get("SpatialExtent"),
                  "ArchiveAndDistributionInformation":
                      umm.get("ArchiveAndDistributionInformation"),
              }, ensure_ascii=False))]
    for label, body in bodies:
        for i, part in enumerate(chunk_text(body)):
            out.append({
                "chunk_id": f"{product}:collection:{label}:{i}",
                "product_id": product,
                "version": version,
                "title": title,
                "text": part,
                "source_url": url,
                "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "source_sha256": digest,
                "concept_id": cid,
                "content_role": "official_metadata_not_measurements",
                "authority": "official_nasa",
                "citable_for_facts": True,
                "retrieved_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"),
            })
    return out


def team_policy_chunks() -> list[dict]:
    """Project-authored rules. Clearly not NASA evidence."""
    qa = json.loads((DATA / "qa_policy.json").read_text(encoding="utf-8"))
    method = json.loads((DATA / "analysis" / "method_config.json")
                        .read_text(encoding="utf-8"))
    texts = [
        ("qa_policy",
         "Quality policy used by this project: "
         f"{json.dumps(qa['products']['MOD13C2']['default_mask'])}. "
         "Strict mode: "
         f"{json.dumps(qa['products']['MOD13C2']['strict_mask'])}. "
         "IMERG quality index is reported but never used to exclude cells "
         "because observed values in this study area are far below any "
         "0-100 style threshold."),
        ("method",
         "Trend method used by this project: seasonal Mann-Kendall with "
         "Hamed-Rao variance correction, Theil-Sen slope on seasonal "
         "anomalies, percentile block-residual bootstrap interval "
         f"({method['bootstrap']['replicates']} replicates, block "
         f"{method['bootstrap']['block_length_months']} months, seed "
         f"{method['bootstrap']['seed']}), Benjamini-Hochberg FDR at q="
         f"{method['multiplicity']['q']} for maps. Method revision "
         f"{method['method_revision']}."),
        ("interpretation",
         "A p-value is the probability of data at least as extreme as "
         "observed if the no-trend null were true. It is not the probability "
         "that a trend exists. Effect size is shown even when the result is "
         "inconclusive."),
    ]
    out = []
    for name, text in texts:
        out.append({
            "chunk_id": f"team:policy:{name}",
            "product_id": None,
            "version": "project",
            "title": f"Project policy note: {name}",
            "text": text,
            "source_url": "project://data/nasa/qa_policy.json",
            "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "content_role": "team_authored_policy",
            "authority": "project_authored",
            "citable_for_facts": False,
            "retrieved_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"),
        })
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    chunks = load_existing()
    sources = {}

    docs = DATA / "expanded_v2" / "docs"
    specs = [
        ("GPM_3IMERGM", "07", "IMERG_V07_ATBD.pdf",
         "IMERG V07 Algorithm Theoretical Basis Document",
         "https://gpm.nasa.gov/sites/default/files/document_files/IMERG_ATBD_V07.pdf"),
        ("MOD13C2", "061", "MOD13_User_Guide_V61.pdf",
         "MODIS Vegetation Index Products (MOD13) User Guide V6.1",
         "https://modis-land.gsfc.nasa.gov/pdf/MOD13_User_Guide_V6.1.pdf"),
    ]
    for product, version, fname, title, url in specs:
        p = docs / fname
        if not p.exists():
            print(f"missing {fname}, skipped")
            continue
        new = pdf_chunks(p, product, version, title, url)
        chunks.extend(new)
        sources[fname] = {"chunks": len(new), "sha256": sha256_file(p)}

    for product, version, fname in (
            ("GPM_3IMERGM", "07", "GPM_3IMERGM_collection.json"),
            ("MOD13C2", "061", "MOD13C2_collection.json")):
        p = docs / fname
        if p.exists():
            new = collection_chunks(p, product, version)
            chunks.extend(new)
            sources[fname] = {"chunks": len(new), "sha256": sha256_file(p)}

    team = team_policy_chunks()
    chunks.extend(team)
    sources["team_policy"] = {"chunks": len(team), "sha256": None}

    # de-duplicate by chunk_id, keep first
    seen, unique = set(), []
    for c in chunks:
        if c["chunk_id"] in seen:
            continue
        seen.add(c["chunk_id"])
        c["injection_flag"] = flag_injection(c["text"])
        unique.append(c)

    version_hash = hashlib.sha256()
    for c in sorted(unique, key=lambda x: x["chunk_id"]):
        version_hash.update(c["chunk_id"].encode())
        version_hash.update(c["text"].encode("utf-8"))
    corpus_version = version_hash.hexdigest()

    out = OUT_DIR / "corpus.v1.jsonl"
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for c in unique:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    by_product, by_role, by_auth = {}, {}, {}
    for c in unique:
        by_product[str(c.get("product_id"))] = \
            by_product.get(str(c.get("product_id")), 0) + 1
        by_role[c["content_role"]] = by_role.get(c["content_role"], 0) + 1
        by_auth[c["authority"]] = by_auth.get(c["authority"], 0) + 1

    manifest = {
        "corpus_version": corpus_version,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunks": len(unique),
        "chunk_chars": CHUNK_CHARS,
        "by_product": by_product,
        "by_content_role": by_role,
        "by_authority": by_auth,
        "injection_flagged": sum(1 for c in unique if c["injection_flag"]),
        "sources": sources,
        "rules": {
            "official_nasa": "may be cited for product definitions, units, "
                             "limitations",
            "project_authored": "may be cited only as project policy, never "
                                "as NASA evidence",
            "numeric_claims": "must come from the analysis result, never from "
                              "retrieved text",
        },
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
