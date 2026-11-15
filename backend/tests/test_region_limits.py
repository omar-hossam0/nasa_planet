"""Region limits must hold even when clients bypass the map."""
import pytest


@pytest.mark.parametrize('edge', range(4))
def test_even_small_region_boundary_escape_is_rejected(client, analysis_payload, container, edge):
    region = container.data.get_region('nile_corridor')
    bbox = list(region.bbox)
    bbox[edge] += -0.001 if edge < 2 else 0.001
    payload = {**analysis_payload, 'aoi': {'type': 'bbox', 'coordinates': bbox}}
    result = client.post('/v1/analyses', json=payload)
    assert result.status_code == 409
    assert result.json()['error']['code'] == 'DATA_NOT_AVAILABLE'
    availability = client.get('/v1/catalog/availability', params={
        'variable_id': 'air_temperature', 'region_id': 'nile_corridor',
        'start_month': analysis_payload['start_month'], 'end_month': analysis_payload['end_month'],
        'bbox': ','.join(map(str, bbox))})
    assert availability.status_code == 200
    assert availability.json()['usable'] is False
    assert container.jobs_repo.list_all() == []


@pytest.mark.parametrize('region_id', ['nile_corridor', 'morocco_comparison', 'sahel_comparison'])
def test_exact_region_boundary_is_allowed(client, analysis_payload, container, region_id):
    bbox = list(container.data.get_region(region_id).bbox)
    result = client.post('/v1/analyses', json={**analysis_payload, 'region_id': region_id,
        'aoi': {'type': 'bbox', 'coordinates': bbox}})
    assert result.status_code == 202


def test_aoi_from_another_region_cannot_be_used(client, analysis_payload, container):
    bbox = list(container.data.get_region('morocco_comparison').bbox)
    result = client.post('/v1/analyses', json={**analysis_payload,
        'aoi': {'type': 'bbox', 'coordinates': bbox}})
    assert result.status_code == 409
    assert container.jobs_repo.list_all() == []
