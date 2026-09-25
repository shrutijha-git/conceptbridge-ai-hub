from app.ai.providers.base import AIProvider, ProviderResult

class MockProvider(AIProvider):
    name = 'mock'
    def generate(self, system_prompt, messages):
        latest=messages[-1]['content'] if messages else ''
        prior=max(0,len(messages)-1)
        return ProviderResult(provider=self.name, model='development-mock', text=(
            '[MOCK — not an AI-generated tutoring answer]\n'
            f'Received: {latest}\n'
            f'Context contains {prior} prior messages plus the shared learning-state envelope. '
            'Configure a real provider on the server to receive tutoring feedback.'))
