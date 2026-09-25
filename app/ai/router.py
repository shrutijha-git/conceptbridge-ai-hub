from dataclasses import dataclass, field
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.base import ProviderResult, ProviderError, ProviderUnavailable, translate_error
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.mock_provider import MockProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.core.config import get_settings, Settings

PROVIDERS = {'mock': MockProvider, 'openai': OpenAIProvider, 'gemini': GeminiProvider, 'anthropic': AnthropicProvider}

@dataclass
class RoutedResult:
    result: ProviderResult
    fallback_used: bool
    route_events: list[dict] = field(default_factory=list)

class RoutingError(ProviderError):
    def __init__(self, error: ProviderError, events: list[dict]):
        super().__init__(error.code, str(error), error.retryable)
        self.route_events = events

def provider_candidates(requested: str, allow_fallback: bool, settings: Settings) -> list[str]:
    if requested == 'auto':
        if settings.default_provider == 'mock':
            if not settings.enable_mock or settings.app_env != 'development':
                raise ProviderError('mock_disabled', 'Mock is only available in local development.')
            return ['mock']
        if settings.default_provider == 'auto': return settings.provider_order
        return list(dict.fromkeys([settings.default_provider, *settings.provider_order]))
    if requested == 'mock':
        if not settings.enable_mock or settings.app_env != 'development':
            raise ProviderError('mock_disabled', 'Mock is only available in local development.')
        return ['mock']
    if requested not in {'openai', 'gemini', 'anthropic'}:
        raise ProviderError('invalid_provider', 'Unknown provider.')
    return list(dict.fromkeys([requested, *settings.provider_order])) if allow_fallback else [requested]

def generate_with_routing(requested_provider: str, system_prompt: str, messages: list[dict[str, str]],
                          allow_fallback: bool = False, *, settings=None, providers=None) -> RoutedResult:
    settings = settings or get_settings()
    factories = providers or PROVIDERS
    candidates = provider_candidates(requested_provider, allow_fallback, settings)
    events, attempted = [], 0
    last_error = ProviderUnavailable('No configured provider is available. Add a server API key or explicitly use local mock mode.')
    for name in candidates:
        try:
            result = factories[name]().generate(system_prompt, [dict(m) for m in messages])
            if not result.text.strip(): raise ProviderError('empty_response', 'The provider returned no usable response.')
            if result.provider != name: raise ProviderError('provider_mismatch', 'Adapter returned an inconsistent identity.')
            events.append({'provider': name, 'status': 'succeeded'})
            return RoutedResult(result, attempted > 0 or (requested_provider != 'auto' and name != requested_provider), events)
        except Exception as exc:
            error = translate_error(exc)
            events.append({'provider': name, 'status': 'skipped' if error.code == 'not_configured' else 'failed', 'code': error.code})
            last_error = error
            if error.code == 'not_configured' and (requested_provider == 'auto' or allow_fallback): continue
            attempted += 1
            if not error.retryable: raise RoutingError(error, events) from None
    raise RoutingError(last_error, events)
