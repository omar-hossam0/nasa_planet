from fastapi.testclient import TestClient
from app.main import create_app
from tests.conftest import make_settings
from app.api.v1 import questions
import pytest
from packages.rag.explanation import ExplanationPipeline
from packages.rag.provider import GeminiClient
from packages.rag.judge import InferenceEvidence, judge_inference

@pytest.fixture
def client(monkeypatch):
    pipeline=ExplanationPipeline(provider=GeminiClient(api_key=''))
    monkeypatch.setattr(questions,'get_pipeline',lambda:pipeline)
    with TestClient(create_app(make_settings(mock_mode=False,rag_enabled=True))) as value: yield value

def test_question_to_analysis_to_judgment_and_templates(client):
    reply=client.post('/v1/explanations/ask',json={'query':'Is the Nile Delta getting warmer between 2001 and 2005?'}).json()
    assert reply['workflow']['state']=='ready',reply
    proposal=reply['workflow']['analysis_request']
    assert proposal['region_id']=='nile_corridor' and proposal['end_month']=='2005-12'
    assert proposal['variable_ids']==['air_temperature'] and reply['citations']
    accepted=client.post('/v1/analyses',json=proposal)
    assert accepted.status_code in (200,202),accepted.text
    rid=accepted.json()['result_id']
    explanation=client.post('/v1/explanations',json={'result_id':rid,'language':'ar'}).json()
    a=explanation['assessments'][0]
    assert a['inference']['status']=='not_computed' and a['judgment']['state']=='unavailable'
    assert a['facts']['complete_years']==5
    assert any(s['section_id'].endswith('_inference_judgment') for s in explanation['sections'])

@pytest.mark.parametrize('query,state',[
 ('air temperature in Sinai','unsupported'),('الجفاف في سينا','clarification_required'),
 ('rainfall in 2030','unavailable'),('temperature in Morocco and Sahel','clarification_required'),
 ('soil moisture and rainfall in Morocco','clarification_required')])
def test_no_executable_proposal_for_unsafe_or_ambiguous_question(client,query,state):
    result=client.post('/v1/explanations/ask',json={'query':query,'region_id':'nile_corridor'}).json()
    assert result['workflow']['state']==state,result
    assert result['workflow']['analysis_request'] is None

def test_unknown_place_does_not_silently_use_current_region(client):
    body=client.post('/v1/explanations/ask',json={'query':'air temperature in Antarctica','region_id':'nile_corridor'}).json()
    assert body['workflow']['state']=='clarification_required'
    assert body['workflow']['analysis_request'] is None

@pytest.mark.parametrize('p,state',[(0.,'evidence_against_zero'),(.01,'evidence_against_zero'),(.05,'insufficient_evidence'),(1.,'insufficient_evidence')])
def test_judge_requires_explicit_released_registry(p,state):
    e=InferenceEvidence(status='computed',method_id='synthetic_test_only',method_revision='1',validation_id='fixture',estimand='linear_mean_trend',p_value=p)
    assert judge_inference(e)['state']=='unreleased_method'
    registry={('synthetic_test_only','1','fixture','linear_mean_trend'):True}
    assert judge_inference(e,released_methods=registry)['state']==state
    assert judge_inference(e,'ar',registry)['message']

@pytest.mark.parametrize('payload',[{'status':'computed','p_value':.1},{'status':'not_computed','p_value':.01},{'status':'computed','method_id':'x','method_revision':'1','validation_id':'v','estimand':'b','p_value':2.}])
def test_contract_rejects_invalid_inference(payload):
    with pytest.raises(ValueError): InferenceEvidence(**payload)

def test_confidence_interval_metadata_must_be_coherent():
    base=dict(status='computed',method_id='synthetic',method_revision='1',validation_id='test',estimand='linear_mean_trend',p_value=.2)
    for extra in [dict(interval=(2.,1.),confidence_level=.95), dict(interval=(0.,1.)), dict(p_value=float('nan'))]:
        with pytest.raises(ValueError): InferenceEvidence(**(base|extra))
