"""Real-browser check for visualizations and template-only result explanations."""

import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend/var/explanation-visuals"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    environment = dict(
        os.environ,
        MOCK_MODE="false",
        RAG_ENABLED="true",
        APP_ENV="test",
        DATABASE_URL="",
        JOB_BACKEND="inline",
    )
    environment["GEMINI_API_KEY"] = ""
    processes = [
        subprocess.Popen(
            ["python", "-m", "uvicorn", "app.main:app", "--port", "18082"],
            cwd=ROOT / "backend",
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        subprocess.Popen(
            [
                "node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                "15174",
            ],
            cwd=ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
    ]
    report = {"errors": []}
    try:
        for url in ["http://127.0.0.1:18082/health", "http://127.0.0.1:15174"]:
            for _ in range(50):
                try:
                    urllib.request.urlopen(url, timeout=1)
                    break
                except Exception:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Audit server failed to start")
        with sync_playwright() as p:
            options = {"headless": True}
            if os.name == "nt":
                installed = list(
                    (Path(os.environ["LOCALAPPDATA"]) / "ms-playwright").glob(
                        "chromium-*/chrome-win64/chrome.exe"
                    )
                )
                if installed:
                    options["executable_path"] = str(
                        max(
                            installed,
                            key=lambda f: int(f.parents[1].name.split("-")[1]),
                        )
                    )
            browser = p.chromium.launch(**options)
            page = browser.new_page(viewport={"width": 1500, "height": 1100})
            page.set_default_timeout(30000)
            page.on("pageerror", lambda e: report["errors"].append(str(e)))
            page.route(
                "**/v1/**",
                lambda r: r.fulfill(
                    response=r.fetch(
                        url=r.request.url.replace(
                            "http://127.0.0.1:15174", "http://127.0.0.1:18082"
                        )
                    )
                ),
            )
            page.goto("http://127.0.0.1:15174/#explore", wait_until="domcontentloaded")
            page.wait_for_function(
                "document.querySelectorAll('.region-options button').length===3"
            )
            page.locator(".region-options button").nth(1).click()
            page.get_by_role("button", name="Analyse this area").click()
            page.locator(".annual-observations").wait_for()
            assert page.locator(".annual-point").count() == 24
            assert page.locator(".slope-histogram rect").count() == 12
            page.locator("#annual-year").focus()
            page.locator("#annual-year").press("Home")
            assert page.locator(".annual-readout b").inner_text() == "2001"
            page.locator(".evidence-rail .inference-notice summary").click()
            assert (
                "not the probability that the trend is real"
                in page.locator(".evidence-rail .inference-notice").inner_text()
            )
            page.locator(".analysis-insights").screenshot(
                path=str(OUT / "insights-desktop.png")
            )

            assert page.locator('.llm-result').count() == 0
            assert page.get_by_role('button', name='Explain with Gemini', exact=True).count() == 0
            assert page.locator('.result-assessment').count() == 1
            assert page.locator('[data-reason-code="request_model_diagnostics_not_run"]').count() == 1
            page.locator('.result-explanation').screenshot(path=str(OUT / 'assessment-desktop.png'))
            # A QA-restricted case demonstrates why spatial coverage and monthly
            # completeness must be separate indicators.
            page.locator(".region-options button").nth(2).click()
            page.locator(".variable-options button").nth(3).click()
            page.get_by_role("button", name="Analyse this area").click()
            page.locator(".coverage-donut").wait_for()
            report["qa_coverage_readout"] = page.locator(".coverage-count").inner_text()
            assert "2961" in report["qa_coverage_readout"].replace(",", "")
            assert page.locator('[data-reason-code="limited_spatial_support"]').count() == 1
            page.locator(".analysis-insights").screenshot(
                path=str(OUT / "ndvi-qa-support.png")
            )
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".analysis-insights").scroll_into_view_if_needed()
            assert page.locator(".analysis-insights").bounding_box()["width"] <= 390
            page.locator(".analysis-insights").screenshot(
                path=str(OUT / "insights-mobile.png")
            )
            page.locator('.result-explanation').scroll_into_view_if_needed()
            assert page.locator('.result-explanation').bounding_box()['width'] <= 390
            page.locator('.result-explanation').screenshot(path=str(OUT/'assessment-mobile.png'))
            page.set_viewport_size({'width': 1500, 'height': 1100})
            page.goto('http://127.0.0.1:15174/?lang=ar#explore', wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.region-options button').length===3")
            page.locator('.date-row select').nth(1).select_option('2005-12')
            page.locator('.run-button').click()
            page.locator('[data-reason-code="short_annual_record"]').wait_for()
            assert '5' in page.locator('[data-reason-code="short_annual_record"]').inner_text()
            assert page.locator('.result-explanation').get_attribute('dir') == 'rtl'
            page.locator('.result-explanation').screenshot(path=str(OUT/'assessment-arabic-short.png'))
            report['assessment_short_window_arabic'] = True
            report['assessment_spatial_warning'] = True
            page.locator('#rag-question').fill('Is Morocco getting warmer between 2001 and 2010?')
            page.locator('.rag-chat form button[type="submit"]').click()
            page.locator('.rag-workflow button').wait_for()
            page.locator('.rag-workflow').screenshot(path=str(OUT/'question-analysis-proposal.png'))
            page.locator('.rag-workflow button').click()
            assert page.locator('.date-row select').nth(1).input_value() == '2010-12'
            with page.expect_response(lambda r: r.url.endswith('/v1/explanations') and r.request.method=='POST') as completed:
                page.locator('.run-button').click()
            assessment = completed.value.json()['assessments'][0]
            assert assessment['region_id']=='morocco_comparison'
            assert assessment['facts']['complete_years']==10
            assert assessment['judgment']['state']=='unavailable'
            report['question_to_analysis_to_judgment'] = True
            assert not report["errors"], report["errors"]
            report["passed"] = True
            browser.close()
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=10)
        (OUT / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
