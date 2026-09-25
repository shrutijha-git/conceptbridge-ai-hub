from abc import ABC, abstractmethod
from dataclasses import dataclass
import httpx

@dataclass
class ProviderResult:
    text: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ''
    finish_reason: str = 'completed'

class ProviderError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable

class ProviderUnavailable(ProviderError):
    def __init__(self, message='This provider is not configured.'):
        super().__init__('not_configured', message)

def translate_error(exc: Exception) -> ProviderError:
    if isinstance(exc, ProviderError): return exc
    status = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
    name = type(exc).__name__
    # SDK exception strings can contain credentials or request content: never forward them.
    if status == 429:
        return ProviderError('rate_or_quota_limit', 'The provider reported a rate or quota limit.', True)
    if status in {408, 500, 502, 503, 504, 529}:
        return ProviderError('temporarily_unavailable', 'The provider is temporarily unavailable.', True)
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)) or name == 'APITimeoutError':
        return ProviderError('timeout', 'The provider did not respond in time.', True)
    if isinstance(exc, httpx.NetworkError) or name == 'APIConnectionError':
        return ProviderError('network_error', 'The provider connection failed.', True)
    if status in {401, 403}:
        return ProviderError('authentication_or_access', 'Check the provider credential and model access on the server.')
    if status in {400, 404, 413, 422}:
        return ProviderError('invalid_request', 'The provider rejected the request or model. Check configuration and input size.')
    return ProviderError('unexpected_error', 'The provider adapter encountered an unexpected error.')

class AIProvider(ABC):
    name: str
    @abstractmethod
    def generate(self, system_prompt: str, messages: list[dict[str, str]]) -> ProviderResult:
        raise NotImplementedError
