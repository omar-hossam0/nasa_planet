# Application audit — 15 November 2026

Direct Computer Use tools were unavailable in this session. Tests used a real
Chromium browser through Playwright, including clicks, typing, downloads and
desktop/mobile screenshots. An isolated FastAPI and Vite instance were started
on ports 18081/15173. Browser requests were forwarded to that isolated API;
analysis and retrieval response bodies were not mocked.

## Findings and fixes

| Area | Finding | Result |
| --- | --- | --- |
| Analysis source | Active adapter is `MockStatisticsAdapter`, not `packages/science` | Explicit synthetic-data notice and method disclosure; no scientific certification claimed |
| UI numeric values | Checked all 4 variables across 3 configured regions | Displayed slopes match API values to displayed precision |
| Chart | Missing values were connected by a single polyline | Paths now break at missing values; all returned plotted coordinates checked against monthly API values |
| Confidence intervals and p-values | Not computed by current adapter | Displayed as “Not computed”, not as evidence of significance |
| Receipt | Downloaded through the UI | Job and result IDs match the displayed result |
| RAG access | Backend question endpoint existed but had no frontend input | Added bilingual question form below chart, examples, loading/errors, source links, evidence excerpts and clear history |
| RAG local fallback | Returns excerpts without an `answer` field | Explicit null answer and capability note; UI identifies retrieved excerpts separately from generated answers |
| Arabic question | “الهطول” was absent from variable aliases | Added curated aliases; Arabic precipitation retrieval now passes |
| Source grounding | Verified returned passages, URLs and source hashes against the actual corpus | Relevant bilingual queries resolve to the expected variables and original evidence |
| Unsupported query | Football question | Classified unsupported with no invented answer or citations |
| Region access | An unregistered region could reach question endpoint | Server now rejects it before retrieval |
| Mobile UI | Floating synthetic notice obscured content | Notice moved inline; mobile and Arabic RTL form checked |

## How to use the assistant

Open the investigation workspace and scroll below the time-series chart to
**Ask the RAG assistant / اسأل مساعد المعرفة**. Enter a question or choose an example,
then press **Ask / اسأل**. Expand a document row to read the original passage and
use its **Open source** link. Each question is independent; earlier messages are
display history, not model conversation memory. Changing study region clears it.

The documentation endpoint is enabled by default; administrators can explicitly
disable it using `RAG_ENABLED=false`. It works without an API key using local
BM25 retrieval. For optional generated explanations, configure the server process's
`GEMINI_API_KEY` environment variable or ignored `backend/.env` file. No key is
exposed in frontend code. Settings load repository `.env` first, then `backend/.env`;
process environment variables override both. Restart the backend after changing
provider settings because the pipeline and settings are cached per process.

## Practical limits

- UI/API agreement establishes display consistency, not scientific correctness.
  The active numeric endpoints still synthesize values. The real science adapter,
  scientific-release gate and final result-to-Role04 conclusion integration remain
  unfinished. Result explanations currently come from mock templates.
- RAG retrieves documentation; it does not fetch a user's stored result or calculate
  a regional value. Such questions must use an explicit server-owned result context
  in a later integration, not ask the LLM to infer numbers from documentation.
- The reproducible browser audit deliberately runs without a provider key.
  A subsequent bounded live Gemini configuration check returned `mode=llm`, an
  answer and five validated citations using `gemini-2.5-flash`. This establishes
  connectivity and one grounded-response success, not general answer accuracy.
- Retrieval checks cover sample queries and exact citation provenance, not a broad
  relevance benchmark or a guarantee that every question retrieves the ideal passage.
- Spin It currently has a backend endpoint but the frontend does not request new
  sensitivity windows; it reports absence of returned windows. Production release
  still requires the work listed in `PRODUCTION_IMPLEMENTATION.md`.

## Reproduce

Install backend/frontend requirements and Python `playwright`, with an installed
Chromium browser. From repository root:

```powershell
python tools/audit_application_browser.py
```

Artifacts: `backend/var/browser-audit/report.json`, downloaded receipt and desktop,
mobile and Arabic screenshots. Runtime artifacts are ignored by Git.

Active backend suite: 142 passing tests with
`python -m pytest tests --ignore=tests/test_api.py -q` from `backend/`.
The excluded file targets the pre-existing legacy API contract; that incompatibility
was established before these changes and is documented in the production checkpoint.
