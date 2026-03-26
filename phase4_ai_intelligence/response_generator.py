"""
Advanced Response Generator
============================

Generates contextual, safety-first responses using optimized LLMs.

Features:
- Multi-backend LLM support (Ollama, API-based, local)
- RAG integration for knowledge-grounded responses
- Safety constraints and guardrails
- Token optimization
- Streaming support
- Confidence scoring

Recommended Models:
- Mistral-7B-Instruct (7B, excellent accuracy/speed)
- Neural-Chat-7B-v3 (7B, optimized for chat)
- LLaMA-2-7B-Chat (7B, comprehensive)
- Zephyr-7B-Beta (7B, SOTA for small models)

For local: Use with GGML quantization (q4, q5) for efficiency
"""

import logging
import requests
import json
import time
from typing import Optional, Dict, List, Iterator, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """LLM provider options."""
    OLLAMA = "ollama"              # Local via Ollama
    HUGGINGFACE = "huggingface"    # HuggingFace API
    OPENAI = "openai"              # OpenAI API
    ANTHROPIC = "anthropic"        # Anthropic API


@dataclass
class GeneratedResponse:
    """Generated response with metadata."""
    text: str
    model_name: str
    provider: str
    confidence: float
    tokens_used: int
    generation_time_ms: float
    safety_score: float      # 0-1, higher = safer
    reasoning: str
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "model": self.model_name,
            "provider": self.provider,
            "confidence": round(self.confidence, 3),
            "safety": round(self.safety_score, 3),
            "tokens": self.tokens_used,
            "time_ms": round(self.generation_time_ms, 1),
            "reasoning": self.reasoning,
        }


class ResponseGenerator:
    """
    Production-grade response generation using LLMs.
    
    Supports multiple providers and models with safety constraints.
    """
    
    # Recommended models
    LOCAL_MODELS = {
        "mistral": "mistral-7b-instruct",
        "neural-chat": "neural-chat-7b-v3",
        "zephyr": "zephyr-7b-beta",
        "llama2": "llama2-7b-chat",
    }
    
    # Safety keywords to avoid
    UNSAFE_KEYWORDS = [
        "harm", "kill", "illegal", "violence",
        "exploit", "abuse", "dangerous",
    ]
    
    # Default prompts
    SYSTEM_PROMPTS = {
        "assistant": "You are a helpful, respectful, and honest assistant for a multimodal AI system. "
                     "Provide clear, concise answers. If unsure, say so.",
        "safety": "You are a safety-conscious assistant. Always consider user safety. "
                  "Never provide instructions that could cause harm.",
        "knowledge": "You are a knowledgeable assistant with access to a knowledge base. "
                     "Use provided context to give accurate answers.",
    }
    
    def __init__(self, model_type: str = "mistral", 
                 provider: str = "ollama",
                 api_key: Optional[str] = None,
                 base_url: str = "http://localhost:11434"):
        """
        Initialize response generator.
        
        Args:
            model_type: Model name (mistral, neural-chat, etc.)
            provider: Provider (ollama, openai, anthropic, huggingface)
            api_key: API key if using cloud provider
            base_url: Base URL for local provider
        """
        self.model_type = model_type
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        
        # Model-specific settings
        self.model_name = self.LOCAL_MODELS.get(model_type, model_type)
        self.temperature = 0.7
        self.max_tokens = 500
        self.top_p = 0.95
        
        logger.info(f"ResponseGenerator initialized: {model_type} via {provider}")
    
    def generate(self, prompt: str, 
                 context: Optional[str] = None,
                 system_prompt: Optional[str] = None,
                 safety_mode: bool = True,
                 timeout: int = 60) -> GeneratedResponse:
        """
        Generate response from prompt.
        
        Args:
            prompt: User prompt
            context: Optional context for RAG
            system_prompt: Optional system prompt
            safety_mode: Whether to apply safety checks
            timeout: Request timeout in seconds
            
        Returns:
            GeneratedResponse
        """
        start_time = time.time()
        
        # Build full prompt
        full_prompt = self._build_prompt(prompt, context, system_prompt)
        
        # Safety check
        if safety_mode:
            safety_score = self._check_safety(prompt)
            if safety_score < 0.3:
                return GeneratedResponse(
                    text="I cannot process this request due to safety constraints.",
                    model_name=self.model_name,
                    provider=self.provider,
                    confidence=0.0,
                    tokens_used=0,
                    generation_time_ms=0,
                    safety_score=safety_score,
                    reasoning="Safety check failed"
                )
        else:
            safety_score = 1.0
        
        try:
            if self.provider == "ollama":
                response = self._generate_ollama(full_prompt, timeout)
            elif self.provider == "openai":
                response = self._generate_openai(full_prompt)
            elif self.provider == "anthropic":
                response = self._generate_anthropic(full_prompt)
            else:
                response = self._generate_ollama(full_prompt, timeout)
            
            generation_time = (time.time() - start_time) * 1000
            
            return GeneratedResponse(
                text=response.get("text", "").strip(),
                model_name=self.model_name,
                provider=self.provider,
                confidence=response.get("confidence", 0.85),
                tokens_used=response.get("tokens", 0),
                generation_time_ms=generation_time,
                safety_score=safety_score,
                reasoning=response.get("reasoning", "LLM generation successful"),
                metadata=response.get("metadata")
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return GeneratedResponse(
                text=f"Error generating response: {str(e)[:100]}",
                model_name=self.model_name,
                provider=self.provider,
                confidence=0.0,
                tokens_used=0,
                generation_time_ms=(time.time() - start_time) * 1000,
                safety_score=safety_score,
                reasoning=f"Generation error: {e}"
            )
    
    def _build_prompt(self, prompt: str, 
                     context: Optional[str] = None,
                     system_prompt: Optional[str] = None) -> str:
        """Build complete prompt with context."""
        system = system_prompt or self.SYSTEM_PROMPTS["assistant"]
        
        parts = [f"System: {system}\n"]
        
        if context:
            parts.append(f"Context:\n{context}\n")
        
        parts.append(f"User: {prompt}\nAssistant:")
        
        return "".join(parts)
    
    def _generate_ollama(self, prompt: str, timeout: int = 60) -> Dict:
        """Generate using Ollama (local LLM)."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "top_p": self.top_p,
                        "num_predict": self.max_tokens,
                        "num_ctx": 2048,
                    }
                },
                timeout=timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            data = response.json()
            text = data.get("response", "").strip()
            
            return {
                "text": text,
                "confidence": 0.85,
                "tokens": len(text.split()),
                "reasoning": "Ollama generation successful"
            }
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    def _generate_openai(self, prompt: str) -> Dict:
        """Generate using OpenAI API."""
        try:
            import openai
            openai.api_key = self.api_key
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            text = response.choices[0].message.content
            
            return {
                "text": text,
                "confidence": 0.9,
                "tokens": response.usage.completion_tokens,
                "reasoning": "OpenAI generation successful"
            }
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    def _generate_anthropic(self, prompt: str) -> Dict:
        """Generate using Anthropic API."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            
            return {
                "text": text,
                "confidence": 0.9,
                "tokens": response.usage.output_tokens,
                "reasoning": "Anthropic generation successful"
            }
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise
    
    def _check_safety(self, text: str) -> float:
        """Safety score for input (0-1, higher = safer)."""
        text_lower = text.lower()
        unsafe_count = sum(1 for kw in self.UNSAFE_KEYWORDS if kw in text_lower)
        
        # More unsafe keywords = lower safety score
        safety_score = max(0.0, 1.0 - (unsafe_count * 0.15))
        
        return safety_score
    
    def set_generation_params(self, temperature: float = None,
                            max_tokens: int = None,
                            top_p: float = None):
        """Configure generation parameters."""
        if temperature is not None:
            self.temperature = max(0.0, min(2.0, temperature))
        if max_tokens is not None:
            self.max_tokens = max(10, min(4000, max_tokens))
        if top_p is not None:
            self.top_p = max(0.0, min(1.0, top_p))
    
    def stream_generate(self, prompt: str, 
                       context: Optional[str] = None) -> Iterator[str]:
        """
        Generate response with streaming.
        
        Yields chunks of generated text.
        """
        if self.provider != "ollama":
            logger.warning("Streaming only supported for Ollama")
            return
        
        try:
            full_prompt = self._build_prompt(prompt, context)
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {
                        "temperature": self.temperature,
                        "top_p": self.top_p,
                        "num_predict": self.max_tokens,
                    }
                },
                stream=True,
                timeout=120
            )
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    yield data.get("response", "")
                    
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"Error: {e}"
