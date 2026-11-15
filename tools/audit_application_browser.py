"""Browser integration audit. Requires Python playwright and an installed Chromium.

Starts isolated API/Vite processes, uses the actual frontend controls and real
HTTP responses, and writes evidence under ignored backend/var/browser-audit/.
No production services or user sessions are changed.
"""
import json
import os
from pathlib import Path
import subprocess
import time
import re
import math
import urllib.request
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'backend/var/browser-audit'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, RAG_ENABLED='true', GEMINI_API_KEY='', APP_ENV='test',
                       MOCK_MODE='true', JOB_BACKEND='inline', DATABASE_URL='')
    processes = [
        subprocess.Popen(['python', '-m', 'uvicorn', 'app.main:app', '--port', '18081'],
            cwd=ROOT/'backend', env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
        subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '15173'],
            cwd=ROOT/'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
    ]
    report = {'analyses': [], 'questions': [], 'browser_errors': [], 'scope': 'Synthetic API outputs and local RAG retrieval; no live Gemini or scientific-release certification.'}
    try:
        for url in ['http://127.0.0.1:18081/health', 'http://127.0.0.1:15173']:
            for _ in range(40):
                try:
                    urllib.request.urlopen(url, timeout=1)
                    break
                except Exception:
                    time.sleep(.25)
            else:
                raise RuntimeError(f'Server failed to start: {url}')
        with sync_playwright() as playwright:
            options = {'headless': True}
            if os.name == 'nt':
                installed = list((Path(os.environ['LOCALAPPDATA'])/'ms-playwright').glob('chromium-*/chrome-win64/chrome.exe'))
                if installed:
                    options['executable_path'] = str(max(installed, key=lambda p: int(p.parents[1].name.split('-')[1])))
            browser = playwright.chromium.launch(**options)
            page = browser.new_page(viewport={'width': 1440, 'height': 1100}, accept_downloads=True)
            page.set_default_timeout(15000)
            page.on('pageerror', lambda error: report['browser_errors'].append(str(error)))
            # Keep Vite's production API paths unchanged, forwarding only this
            # isolated audit's requests to its private backend port.
            page.route('**/v1/**', lambda route: route.fulfill(response=route.fetch(
                url=route.request.url.replace('http://127.0.0.1:15173', 'http://127.0.0.1:18081'))))
            page.goto('http://127.0.0.1:15173/#explore', wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.region-options button').length === 3")
            for region_index in range(3):
                for variable_index in range(4):
                    page.locator('.region-options button').nth(region_index).click()
                    page.locator('.variable-options button').nth(variable_index).click()
                    with page.expect_response(lambda response: '/v1/results/' in response.url and '/spatial' not in response.url) as pending:
                        page.get_by_role('button', name='Analyse this area').click()
                    raw = pending.value.json()
                    variable = raw['variables'][0]
                    slope = variable['trend']['slope_per_year']
                    expected = f'{slope:,.4f}' if slope is not None else '—'
                    page.wait_for_function('(value) => document.querySelector(".big-number span")?.textContent === value', arg=expected)
                    assert raw['data_mode'] == 'mock'
                    assert variable['trend']['p_value'] is None
                    assert 'Not computed' in page.locator('.result-body').inner_text()
                    assert page.locator('.monthly-line').get_attribute('d').startswith('M')
                    values = [point['value'] for point in variable['series']]
                    finite = [value for value in values if value is not None]
                    low, high = min(finite), max(finite)
                    expected_coordinates = []
                    for index, value in enumerate(values):
                        if value is not None:
                            expected_coordinates.extend([48 + index/max(1,len(values)-1)*830,
                                245 - ((value-low)/(high-low or 1))*190])
                    coordinates = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?(?:e[+-]?\d+)?',
                        page.locator('.monthly-line').get_attribute('d'))]
                    assert len(coordinates) == len(expected_coordinates)
                    assert all(math.isclose(a,b,abs_tol=1e-8) for a,b in zip(coordinates,expected_coordinates))
                    report['analyses'].append({'region': raw['analysis']['region_id'],
                        'variable': variable['variable_id'], 'api_slope': slope, 'ui_slope': expected,
                        'inference_status': variable['trend']['inference_status'], 'data_mode': raw['data_mode']})
            with page.expect_download() as download:
                page.get_by_role('button', name='Download receipt').click()
            download.value.save_as(OUT/'receipt.json')
            receipt = json.loads((OUT/'receipt.json').read_text())
            assert receipt['job_id'] == raw['job_id']
            assert receipt['result_id'] == raw['result_id']
            report['receipt_matches_result'] = True

            chunks = {chunk['chunk_id']: chunk for chunk in (
                json.loads(line) for line in (ROOT/'data/nasa/rag/corpus_semantic.jsonl').read_text(encoding='utf-8').splitlines() if line.strip())}
            for question in ['What is precipitation?', 'ما هو الهطول؟', 'ما هو NDVI؟', 'What is soil moisture?', 'Who won the football match?']:
                page.get_by_label('Your question', exact=True).fill(question)
                with page.expect_response(lambda response: response.url.endswith('/v1/explanations/ask')) as pending:
                    page.get_by_role('button', name='Ask', exact=True).click()
                reply = pending.value.json()
                page.wait_for_function('(count) => document.querySelectorAll(".rag-turn").length === count', arg=len(report['questions'])+1)
                assert reply['mode'] == 'local_retrieval'
                assert reply['answer'] is None
                for citation in reply['citations']:
                    chunk = chunks[citation['chunk_id']]
                    assert citation['text'] == chunk['text']
                    assert citation['source_url'] == chunk['source_url']
                if 'football' in question:
                    assert reply['status'] == 'unsupported'
                    assert not reply['citations']
                else:
                    assert reply['citations']
                report['questions'].append({'query': question, 'mode': reply['mode'], 'status': reply['status'],
                    'variables': reply['variable_ids'], 'verified_citation_count': len(reply['citations'])})
            page.locator('.rag-citation summary').first.click()
            assert page.locator('.rag-citation a').first.get_attribute('href').startswith('https://')
            page.locator('.rag-chat').screenshot(path=str(OUT/'rag-desktop.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('.rag-chat').scroll_into_view_if_needed()
            assert page.locator('#rag-question').bounding_box()['width'] > 150
            page.locator('.rag-chat').screenshot(path=str(OUT/'rag-mobile.png'))
            page.goto('http://127.0.0.1:15173/?lang=ar#explore', wait_until='domcontentloaded')
            page.wait_for_function("document.querySelectorAll('.region-options button').length === 3")
            page.get_by_label('سؤالك', exact=True).fill('ما هي رطوبة التربة؟')
            with page.expect_response(lambda response: response.url.endswith('/v1/explanations/ask')) as pending:
                page.get_by_role('button', name='اسأل', exact=True).click()
            assert 'soil_moisture' in pending.value.json()['variable_ids']
            page.locator('.rag-turn').wait_for()
            assert page.locator('html').get_attribute('dir') == 'rtl'
            page.locator('.rag-chat').screenshot(path=str(OUT/'rag-arabic.png'))
            report['arabic_interface_passed'] = True
            assert not report['browser_errors'], report['browser_errors']
            browser.close()
            report['passed'] = True
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=10)
        (OUT/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'PASS: {len(report["analyses"])} UI/API comparisons, receipt, {len(report["questions"])} RAG questions, source evidence, mobile layout. Artifacts: {OUT}')


if __name__ == '__main__':
    main()
