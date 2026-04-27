"""
AI service for meeting analysis using Groq API.

Provides text summarization capabilities through the Groq LLM service.
"""
import os
from typing import Optional
import logging
from groq import Groq, GroqError

from backend.constants import DEFAULT_AI_MODEL, DEFAULT_AI_TEMPERATURE, DEFAULT_AI_MAX_TOKENS

logger = logging.getLogger(__name__)


import os
from typing import Optional, Any
import logging
from groq import Groq, GroqError

from backend.constants import DEFAULT_AI_MODEL, DEFAULT_AI_TEMPERATURE, DEFAULT_AI_MAX_TOKENS
from backend.exceptions import AIServiceError

logger = logging.getLogger(__name__)


class AIService:
    """
    Service for generating AI-powered summaries using Groq API.
    
    Handles communication with Groq's LLM service, including error handling
    for API failures and response validation.
    
    Attributes:
        client: Groq API client instance.
        model: Model identifier to use for inference.
        temperature: Sampling temperature (0.0-1.0).
        max_tokens: Maximum tokens in response.
    """
    
    def __init__(
        self, 
        model: str = DEFAULT_AI_MODEL,
        temperature: float = DEFAULT_AI_TEMPERATURE,
        max_tokens: int = DEFAULT_AI_MAX_TOKENS
    ) -> None:
        """
        Initialize AI service with Groq client.
        
        Args:
            model: Groq model identifier.
            temperature: Sampling temperature for response randomness.
            max_tokens: Maximum number of tokens in generated response.
            
        Raises:
            AIServiceError: If GROQ_API_KEY environment variable is not set.
        """
        try:
            api_key: Optional[str] = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.error("GROQ_API_KEY not found in environment variables")
                raise AIServiceError("GROQ_API_KEY not found in environment")
            
            logger.info("Initializing AIService with model: %s, temperature: %.2f, max_tokens: %d",
                        model, temperature, max_tokens)
            self.client: Groq = Groq(api_key=api_key)
            self.model: str = model
            self.temperature: float = temperature
            self.max_tokens: int = max_tokens
        except Exception as e:
            if not isinstance(e, AIServiceError):
                logger.error("Failed to initialize AIService: %s", str(e), exc_info=True)
                raise AIServiceError(f"Failed to initialize AI service: {str(e)}")
            raise

    def generate_summary(self, text: str, prompt: Optional[str] = None) -> str:
        """
        Generate a summary of the provided text using Groq LLM.
        
        Args:
            text: Input text to summarize.
            prompt: Optional custom prompt. If None, uses default summarization prompt.
            
        Returns:
            str: Generated summary text.
            
        Raises:
            AIServiceError: If API call fails or returns invalid response.
            ValueError: If input text is empty.
        """
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided to generate_summary")
            raise ValueError("Empty text provided")
        
        if prompt is None:
            prompt = "Please summarize the following text concisely:"

        try:
            logger.debug("Sending request to Groq API with %d characters of input", len(text))
            chat_completion: Any = self.client.chat.completions.create(
                messages=[{"role": "user", "content": f"{prompt}\n\n{text}"}],
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=1,
                stream=False,
            )
            
            if not chat_completion.choices or not chat_completion.choices[0].message:
                logger.error("Empty response choices from Groq API")
                raise AIServiceError("Empty response from AI service")

            summary: str = chat_completion.choices[0].message.content
            if not summary:
                logger.warning("AI service returned an empty summary")
                return ""

            logger.info("Successfully generated summary (%d characters)", len(summary))
            return summary
            
        except GroqError as e:
            logger.error("Groq API error: %s", e)
            raise AIServiceError(f"Groq API error: {e}") from e
        except (IndexError, AttributeError) as e:
            logger.error("Unexpected response format from Groq API: %s", e)
            raise AIServiceError(f"Unexpected response format: {e}") from e
        except Exception as e:
            if not isinstance(e, (AIServiceError, ValueError)):
                logger.error("Unexpected error in AIService.generate_summary: %s", e, exc_info=True)
                raise AIServiceError(f"Unexpected error: {e}") from e
            raise