from google import genai
from google.genai import types
from app.ai.providers.base import AIProvider, ProviderResult, ProviderUnavailable, ProviderError
from app.core.config import get_settings

class GeminiProvider(AIProvider):
    name = 'gemini'
    def generate(self, system_prompt, messages):
        s = get_settings()
        if not s.gemini_api_key: raise ProviderUnavailable()
        contents = [types.Content(role='model' if m['role'] == 'assistant' else 'user',
                    parts=[types.Part.from_text(text=m['content'])]) for m in messages]
        with genai.Client(api_key=s.gemini_api_key,
                http_options=types.HttpOptions(timeout=int(s.provider_timeout_seconds * 1000),
                    retry_options=types.HttpRetryOptions(attempts=1))) as client:
            response = client.models.generate_content(model=s.gemini_model, contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_prompt, max_output_tokens=s.max_output_tokens))
        if getattr(getattr(response, 'prompt_feedback', None), 'block_reason', None):
            raise ProviderError('refusal', 'The provider declined this request. Try a different learning question.')
        candidates = response.candidates or []
        finish = str(getattr(candidates[0], 'finish_reason', '')) if candidates else ''
        if any(x in finish for x in ['SAFETY', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'RECITATION']):
            raise ProviderError('refusal', 'The provider declined this response. Try a different learning question.')
        if 'MAX_TOKENS' in finish:
            raise ProviderError('incomplete_response', 'The response reached an output limit. Try a shorter request.')
        usage = response.usage_metadata
        return ProviderResult(text=response.text or '', provider=self.name, model=s.gemini_model,
            input_tokens=getattr(usage, 'prompt_token_count', 0) or 0,
            output_tokens=getattr(usage, 'candidates_token_count', 0) or 0)
