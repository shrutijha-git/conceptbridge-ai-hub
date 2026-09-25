import pytest
from app.ai.router import generate_with_routing,RoutingError,provider_candidates
from app.ai.providers.base import ProviderResult,ProviderError,ProviderUnavailable
from app.core.config import Settings

CONTEXT=[{'role':'user','content':'What is 3NF?'},{'role':'assistant','content':'Consider A → B → C.'},{'role':'user','content':'How should I decompose it?'}]

def config(**kw): return Settings(_env_file=None,default_provider='auto',**kw)

def test_transient_failure_passes_identical_context_to_next_provider():
    seen=[]
    class Limited:
        def generate(self,system,messages):
            seen.append((system,messages));raise ProviderError('rate_or_quota_limit','Limited',True)
    class Success:
        def generate(self,system,messages):
            seen.append((system,messages));return ProviderResult('Continue with decomposition.','openai')
    r=generate_with_routing('auto','Shared learning state',CONTEXT,settings=config(),providers={'gemini':Limited,'openai':Success})
    assert r.fallback_used and r.result.provider=='openai'
    assert seen[0]==seen[1]
    assert seen[0][1] is not seen[1][1]

@pytest.mark.parametrize('code',['invalid_request','refusal','authentication_or_access','unexpected_error','incomplete_response'])
def test_nonrecoverable_errors_never_switch_providers(code):
    class Bad:
        def generate(self,*args): raise ProviderError(code,'Stop here')
    class Unreachable:
        def generate(self,*args): pytest.fail('Must not call a fallback')
    with pytest.raises(RoutingError) as exc:
        generate_with_routing('auto','',CONTEXT,settings=config(),providers={'gemini':Bad,'openai':Unreachable})
    assert exc.value.code==code

def test_missing_config_is_skipped_without_claiming_a_failed_api_call():
    class Missing:
        def generate(self,*a): raise ProviderUnavailable()
    class Ready:
        def generate(self,*a): return ProviderResult('Response','openai')
    r=generate_with_routing('auto','',CONTEXT,settings=config(),providers={'gemini':Missing,'openai':Ready})
    assert not r.fallback_used
    assert r.route_events[0]['status']=='skipped'

def test_mock_is_never_a_live_fallback():
    class Missing:
        def generate(self,*a): raise ProviderUnavailable()
    with pytest.raises(RoutingError):
        generate_with_routing('auto','',CONTEXT,settings=config(),providers={p:Missing for p in ['gemini','openai','anthropic']})
    assert 'mock' not in provider_candidates('auto',True,config())

def test_explicit_selection_and_opt_in_fallback():
    s=config()
    assert provider_candidates('anthropic',False,s)==['anthropic']
    assert provider_candidates('anthropic',True,s)==['anthropic','gemini','openai']

def test_default_mock_really_controls_auto():
    s=Settings(_env_file=None,default_provider='mock')
    assert provider_candidates('auto',False,s)==['mock']

def test_passwords_are_not_interpolated_into_url_strings():
    s=Settings(_env_file=None,mysql_password='abc:@/#?[]')
    assert s.database_url.drivername=='mysql+pymysql'
    assert s.database_url.password=='abc:@/#?[]'
