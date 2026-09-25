"""
AUTOSAR HLD AI - LLM Service
Configurable multi-provider LLM service supporting OpenAI GPT-4o,
Anthropic Claude, Groq Llama-3, Ollama (Local), and HuggingFace.
Falls back gracefully when no LLM provider is available.
"""

from typing import Optional
from app.utils.config import settings
from app.utils.logger import logger


class LLMService:
    """
    Configurable LLM service supporting multiple enterprise and local providers.
    Supports OpenAI, Anthropic Claude, Groq Llama-3, Local Ollama, and HuggingFace.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower() if settings.LLM_PROVIDER else "none"
        self._available = None

    @property
    def is_available(self) -> bool:
        """Check if an LLM provider is configured and reachable."""
        if self._available is not None:
            return self._available

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            self._available = True
        elif self.provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            self._available = True
        elif self.provider == "groq" and settings.GROQ_API_KEY:
            self._available = True
        elif self.provider == "ollama":
            self._available = self._check_ollama()
        elif self.provider == "huggingface" and settings.HF_API_TOKEN:
            self._available = True
        else:
            self._available = False

        return self._available

    def generate(self, prompt: str, max_tokens: int = 1500, temperature: float = 0.1) -> Optional[str]:
        """
        Generate a response from the configured LLM provider.

        Args:
            prompt: Input prompt
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (low for deterministic factual outputs)

        Returns:
            Generated text or None if unavailable
        """
        if not self.is_available:
            logger.warning("LLM unavailable — no provider configured or reachable")
            return None

        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, max_tokens, temperature)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, max_tokens, temperature)
            elif self.provider == "groq":
                return self._generate_groq(prompt, max_tokens, temperature)
            elif self.provider == "ollama":
                return self._generate_ollama(prompt, max_tokens, temperature)
            elif self.provider == "huggingface":
                return self._generate_huggingface(prompt, max_tokens, temperature)
            else:
                return None
        except Exception as e:
            logger.error(f"LLM generation failed ({self.provider}): {e}")
            return None

    def _generate_openai(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        """Generate using OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert AUTOSAR High-Level Design (HLD) systems architect assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            return None

    def _generate_anthropic(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        """Generate using Anthropic Claude API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            message = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are an expert AUTOSAR High-Level Design (HLD) systems architect assistant.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            if message.content and len(message.content) > 0:
                return message.content[0].text
            return None
        except ImportError:
            logger.error("Anthropic package not installed. Run `pip install anthropic`.")
            return None
        except Exception as e:
            logger.error(f"Anthropic generation error: {e}")
            return None

    def _generate_groq(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        """Generate using Groq (ultra-fast Llama-3 / Mixtral inference)."""
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert AUTOSAR High-Level Design (HLD) systems architect assistant."},
                    {"role": "user", "content": prompt}
                ],
                model=settings.GROQ_MODEL,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return chat_completion.choices[0].message.content
        except ImportError:
            logger.error("Groq package not installed. Run `pip install groq`.")
            # Fallback to direct HTTP request for Groq REST API
            import requests
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an expert AUTOSAR systems architect assistant."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"]
            logger.error(f"Groq HTTP API returned status {res.status_code}: {res.text}")
            return None
        except Exception as e:
            logger.error(f"Groq generation error: {e}")
            return None

    def _generate_ollama(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        """Generate using Ollama local model."""
        try:
            import requests
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=120
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            logger.error(f"Ollama returned status {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            return None

    def _generate_huggingface(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        """Generate using HuggingFace Inference API."""
        try:
            import requests
            headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{settings.HF_MODEL_NAME}",
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                        "return_full_text": False
                    }
                },
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "")
            logger.error(f"HuggingFace returned status {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"HuggingFace generation error: {e}")
            return None

    def _check_ollama(self) -> bool:
        """Check if Ollama server is running."""
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


# Global singleton
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
