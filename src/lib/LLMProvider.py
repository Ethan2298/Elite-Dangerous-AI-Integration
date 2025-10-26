"""
LLM Provider abstraction layer for COVAS NEXT / Project NEXUS

This module provides an abstract interface for different LLM backends:
- OpenAI (default, existing implementation)
- Ollama (local LLM inference)
- Future: llama.cpp, custom endpoints, etc.

Design Goals (from NEXUS vision):
- Sub-1-second response times for standard interactions
- Support for function/tool calling (critical for action system)
- Streaming responses for immediate TTS playback
- Graceful fallback between providers
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Literal
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai import OpenAI


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def get_openai_client(self) -> OpenAI:
        """
        Get the underlying OpenAI client for backward compatibility.

        Some parts of the codebase (plugins, actions) may need direct access
        to the OpenAI client. This method provides that access.

        Returns:
            OpenAI client instance
        """
        pass

    @abstractmethod
    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Create a chat completion.

        Args:
            model: Model identifier (e.g., "gpt-4.1-mini", "llama3.1:8b")
            messages: List of message dicts with role/content
            temperature: Sampling temperature (0-2)
            tools: Optional list of function/tool definitions
            **kwargs: Provider-specific parameters

        Returns:
            ChatCompletion object compatible with OpenAI format

        Raises:
            Exception: On API errors
        """
        pass

    @abstractmethod
    def chat_completion_with_raw_response(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """
        Create a chat completion with raw HTTP response.

        Used for debugging and accessing response metadata (headers, timing, etc.)

        Returns:
            Raw response object with .parse() method
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses"""
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports function/tool calling"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name for logging/debugging"""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (existing implementation)"""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            base_url: API endpoint (default: official OpenAI API)
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url

    def get_openai_client(self) -> OpenAI:
        """Return the OpenAI client for backward compatibility"""
        return self.client

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """Create chat completion using OpenAI API"""
        return self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **kwargs
        )

    def chat_completion_with_raw_response(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """Create chat completion with raw response object"""
        return self.client.chat.completions.with_raw_response.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **kwargs
        )

    def supports_streaming(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return f"OpenAI ({self.base_url})"


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider

    Ollama provides OpenAI-compatible API at http://localhost:11434
    Supports models like llama3.1:8b, mistral:7b, etc.

    Key features:
    - Local inference (no API costs, offline capable)
    - OpenAI-compatible API (easy integration)
    - Function calling support (Llama 3.1+, Mistral, etc.)
    - Streaming support

    Limitations:
    - Slower than cloud APIs (depends on hardware)
    - Requires model downloaded locally (~4-8GB per model)
    - Function calling quality varies by model
    """

    def __init__(self, base_url: str = "http://localhost:11434/v1", api_key: str = "ollama"):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama API endpoint (default: http://localhost:11434/v1)
            api_key: Dummy API key (Ollama doesn't require auth, but OpenAI client expects one)
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url

    def get_openai_client(self) -> OpenAI:
        """Return the OpenAI client for backward compatibility"""
        return self.client

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Create chat completion using Ollama API.

        Ollama uses OpenAI-compatible format, so we can use the same client.
        Tool/function calling works with models that support it (Llama 3.1+, Mistral, etc.)
        """
        # Remove kwargs that Ollama doesn't support
        # GPT-5 specific params
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def chat_completion_with_raw_response(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """Create chat completion with raw response object"""
        # Remove kwargs that Ollama doesn't support
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.with_raw_response.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def supports_streaming(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        # Ollama supports tools with compatible models
        # Llama 3.1+, Mistral 7B+, etc. have function calling
        return True

    def get_provider_name(self) -> str:
        return f"Ollama ({self.base_url})"


class LMStudioProvider(LLMProvider):
    """
    LM Studio local LLM provider

    LM Studio is a desktop app for running LLMs locally with a GUI.
    Provides OpenAI-compatible API at http://localhost:1234/v1

    Key features:
    - User-friendly GUI for model management
    - Automatic GPU acceleration
    - Model library with one-click downloads
    - Built-in model quantization options

    Requirements:
    - LM Studio installed (lmstudio.ai)
    - Model loaded in LM Studio
    - Local server running
    """

    def __init__(self, base_url: str = "http://localhost:1234/v1", api_key: str = "lm-studio"):
        """
        Initialize LM Studio provider.

        Args:
            base_url: LM Studio API endpoint (default: http://localhost:1234/v1)
            api_key: Dummy API key (LM Studio doesn't require auth)
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url

    def get_openai_client(self) -> OpenAI:
        """Return the OpenAI client for backward compatibility"""
        return self.client

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """Create chat completion using LM Studio API"""
        # Filter unsupported kwargs
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def chat_completion_with_raw_response(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """Create chat completion with raw response object"""
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.with_raw_response.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def supports_streaming(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        # LM Studio supports tools with compatible models
        return True

    def get_provider_name(self) -> str:
        return f"LM Studio ({self.base_url})"


class TextGenWebuiProvider(LLMProvider):
    """
    text-generation-webui (oobabooga) provider

    Popular open-source web UI for running LLMs locally.
    Provides OpenAI-compatible API via extensions.

    Key features:
    - Extensive model format support (GGUF, GPTQ, AWQ, etc.)
    - Advanced generation parameters
    - LoRA adapter support
    - Character/instruction templates

    Requirements:
    - text-generation-webui installed
    - openai extension enabled
    - Server running on port 5000 (default)

    Setup: https://github.com/oobabooga/text-generation-webui
    """

    def __init__(self, base_url: str = "http://localhost:5000/v1", api_key: str = "text-gen-webui"):
        """
        Initialize text-generation-webui provider.

        Args:
            base_url: API endpoint (default: http://localhost:5000/v1)
            api_key: Dummy API key
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url

    def get_openai_client(self) -> OpenAI:
        """Return the OpenAI client for backward compatibility"""
        return self.client

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """Create chat completion using text-gen-webui API"""
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def chat_completion_with_raw_response(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """Create chat completion with raw response object"""
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.with_raw_response.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def supports_streaming(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        # Tool support depends on model and configuration
        # Some models with instruction tuning can handle it
        return True

    def get_provider_name(self) -> str:
        return f"text-generation-webui ({self.base_url})"


class VLLMProvider(LLMProvider):
    """
    vLLM (Virtual LLM) provider

    High-performance inference engine optimized for throughput.
    Provides OpenAI-compatible API.

    Key features:
    - Fastest inference speed (PagedAttention)
    - Excellent for production deployments
    - Automatic batching and continuous batching
    - Multi-GPU support

    Requirements:
    - vLLM installed and running
    - CUDA-compatible GPU
    - Server started with --api-key or no auth

    Setup: https://docs.vllm.ai/
    """

    def __init__(self, base_url: str = "http://localhost:8000/v1", api_key: str = "vllm"):
        """
        Initialize vLLM provider.

        Args:
            base_url: vLLM API endpoint (default: http://localhost:8000/v1)
            api_key: API key if vLLM server requires it
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url

    def get_openai_client(self) -> OpenAI:
        """Return the OpenAI client for backward compatibility"""
        return self.client

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """Create chat completion using vLLM API"""
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def chat_completion_with_raw_response(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 1.0,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs
    ) -> Any:
        """Create chat completion with raw response object"""
        filtered_kwargs = {k: v for k, v in kwargs.items()
                          if k not in ['verbosity', 'reasoning_effort']}

        return self.client.chat.completions.with_raw_response.create(  # type: ignore
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            tools=tools,  # type: ignore
            **filtered_kwargs
        )

    def supports_streaming(self) -> bool:
        return True

    def supports_tools(self) -> bool:
        # vLLM supports tools with compatible models
        return True

    def get_provider_name(self) -> str:
        return f"vLLM ({self.base_url})"


def create_llm_provider(
    provider_type: Literal['openai', 'ollama', 'lm-studio', 'text-gen-webui', 'vllm', 'openrouter', 'google-ai-studio', 'custom', 'local-ai-server'],
    api_key: str,
    endpoint: str = "",
) -> LLMProvider:
    """
    Factory function to create appropriate LLM provider.

    Args:
        provider_type: Type of provider to create
        api_key: API key for the provider
        endpoint: Custom endpoint URL (if applicable)

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: If provider_type is not supported
    """
    if provider_type == 'ollama':
        # Default to Ollama's standard endpoint
        base_url = endpoint if endpoint else "http://localhost:11434/v1"
        return OllamaProvider(base_url=base_url, api_key=api_key or "ollama")

    elif provider_type == 'lm-studio':
        # LM Studio default endpoint
        base_url = endpoint if endpoint else "http://localhost:1234/v1"
        return LMStudioProvider(base_url=base_url, api_key=api_key or "lm-studio")

    elif provider_type == 'text-gen-webui':
        # text-generation-webui (oobabooga) default endpoint
        base_url = endpoint if endpoint else "http://localhost:5000/v1"
        return TextGenWebuiProvider(base_url=base_url, api_key=api_key or "text-gen-webui")

    elif provider_type == 'vllm':
        # vLLM default endpoint
        base_url = endpoint if endpoint else "http://localhost:8000/v1"
        return VLLMProvider(base_url=base_url, api_key=api_key or "vllm")

    elif provider_type == 'openai':
        base_url = endpoint if endpoint else "https://api.openai.com/v1"
        return OpenAIProvider(api_key=api_key, base_url=base_url)

    elif provider_type in ['openrouter', 'google-ai-studio', 'custom', 'local-ai-server']:
        # These all use OpenAI-compatible APIs, just different endpoints
        # Use OpenAI provider with custom endpoint
        base_url = endpoint if endpoint else "https://api.openai.com/v1"
        return OpenAIProvider(api_key=api_key, base_url=base_url)

    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")
