import os
from typing import Optional
from groq import Groq, GroqError


class AIServiceError(Exception):
    pass


class AIService:
    def __init__(self, model: str = "llama3-8b-8192", temperature: float = 0.5, max_tokens: int = 1024) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise AIServiceError("GROQ_API_KEY not found in environment")
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate_summary(self, text: str, prompt: Optional[str] = None) -> str:
        if not text:
            raise AIServiceError("Empty text provided")
        
        if prompt is None:
            prompt = "Please summarize the following text concisely:"

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": f"{prompt}\n\n{text}"}],
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=1,
                stream=False,
            )
            return chat_completion.choices[0].message.content
        except GroqError as e:
            raise AIServiceError(f"Groq API error: {e}")
        except Exception as e:
            raise AIServiceError(f"Unexpected error: {e}")