import json
import pytest
from fastapi.testclient import TestClient
from app.core.regions import DEFAULT_REGIONS, load_regions
from app.main import create_app
from tests.conftest import BASE_ANALYSIS, make_settings


def test_new_region_is_discovered_and_variable_coverage_is_enforced(tmp_path):
    raw = json.loads(DEFAULT_REGIONS.read_text(encoding='utf-8'))
    raw['regions'].append({
        'region_id': 'new_study_window', 'display_name': 'New study window',
        'bbox': [10, 10, 14, 14], 'period_start': '2010-01', 'period_end': '2024-12',
        'supported_variable_ids': ['air_temperature']})
    path = tmp_path / 'regions.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    app = create_app(make_settings(regions_file=str(path)))
    with TestClient(app) as client:
        regions = client.get('/v1/catalog/regions').json()['regions']
        assert len(regions) == 4
        assert regions[-1]['supported_variable_ids'] == ['air_temperature']
        request = {**BASE_ANALYSIS, 'region_id': 'new_study_window', 'aoi': None, 'start_month': '2010-01'}
        accepted = client.post('/v1/analyses', json=request)
        assert accepted.status_code == 202
        assert client.get('/v1/analyses/' + accepted.json()['job_id']).json()['status'] == 'completed'
        assert client.post('/v1/analyses', json={**request, 'variable_ids': ['soil_moisture']}).status_code == 409
        assert client.post('/v1/analyses', json={**request, 'start_month': '2005-01'}).status_code == 409
        assert client.post('/v1/analyses', json={**request, 'region_id': 'unconfigured_place'}).status_code == 404


def test_duplicate_aliases_fail_at_startup(tmp_path):
    raw = json.loads(DEFAULT_REGIONS.read_text(encoding='utf-8'))
    raw['regions'][1]['aliases'].append('egypt')
    path = tmp_path / 'regions.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(ValueError, match='unique'):
        load_regions(path)
