import anthropic
from app.ai.providers.base import AIProvider, ProviderResult, ProviderUnavailable, ProviderError
from app.core.config import get_settings

class AnthropicProvider(AIProvider):
    name = 'anthropic'
    def generate(self, system_prompt, messages):
        s = get_settings()
        if not s.anthropic_api_key: raise ProviderUnavailable()
        with anthropic.Anthropic(api_key=s.anthropic_api_key, timeout=s.provider_timeout_seconds, max_retries=0) as client:
            response = client.messages.create(model=s.anthropic_model, max_tokens=s.max_output_tokens,
                system=system_prompt, messages=[{'role':m['role'], 'content':m['content']} for m in messages])
        if response.stop_reason == 'refusal':
            raise ProviderError('refusal', 'The provider declined this request. Try a different learning question.')
        if response.stop_reason == 'max_tokens':
            raise ProviderError('incomplete_response', 'The response reached an output limit. Try a shorter request.')
        text = ''.join(b.text for b in response.content if getattr(b, 'type', '') == 'text')
        return ProviderResult(text=text, provider=self.name, model=s.anthropic_model,
            input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
