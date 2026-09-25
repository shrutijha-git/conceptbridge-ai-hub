from openai import OpenAI
from app.ai.providers.base import AIProvider, ProviderResult, ProviderUnavailable, ProviderError
from app.core.config import get_settings

class OpenAIProvider(AIProvider):
    name = 'openai'
    def generate(self, system_prompt, messages):
        s = get_settings()
        if not s.openai_api_key: raise ProviderUnavailable()
        with OpenAI(api_key=s.openai_api_key, timeout=s.provider_timeout_seconds, max_retries=0) as client:
            response = client.responses.create(model=s.openai_model, instructions=system_prompt,
                input=[{'role': m['role'], 'content': m['content']} for m in messages],
                store=False, max_output_tokens=s.max_output_tokens)
        for item in response.output:
            for block in getattr(item, 'content', []):
                if getattr(block, 'type', '') == 'refusal':
                    raise ProviderError('refusal', 'The provider declined this request. Try a different learning question.')
        if response.status == 'incomplete':
            raise ProviderError('incomplete_response', 'The response reached an output limit. Try a shorter request.')
        usage = response.usage
        return ProviderResult(text=response.output_text or '', provider=self.name, model=s.openai_model,
            input_tokens=getattr(usage, 'input_tokens', 0) or 0, output_tokens=getattr(usage, 'output_tokens', 0) or 0)
