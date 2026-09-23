"""LLM Provider abstraction layer supporting Groq, OpenRouter Qwen, and NVIDIA NIM."""

import os
from typing import Optional, Union, Any, List, Dict


FREE_MODELS = {
    "groq": [
        "llama-3.3-70b-versatile",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "openrouter": [
        "qwen/qwen3.7-flash",               # Primary model from Blog Writer-ai01.json
        "qwen/qwen-plus",                  # Secondary model from Blog Writer-ai01.json
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
    ],
    "nvidia": [
        "meta/llama-3.3-70b-instruct",
        "deepseek-ai/deepseek-r1",
    ]
}


def configure_llm_provider(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Any:
    """
    Factory function for dependency injecting LLM models into Pydantic AI Agent.
    Supports Groq, OpenRouter, and NVIDIA NIM.
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()

    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY")
        model_id = model_name or os.getenv("LLM_MODEL", FREE_MODELS["groq"][0])
        if not key:
            print("[LLM Provider] Note: GROQ_API_KEY not found in environment.")
            return "test"
        try:
            from pydantic_ai.models import infer_model
            os.environ["OPENAI_API_KEY"] = key
            os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"
            return infer_model(f"openai:{model_id}")
        except Exception:
            return f"openai:{model_id}"

    elif provider == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY")
        model_id = model_name or os.getenv("LLM_MODEL", FREE_MODELS["openrouter"][0])
        if not key:
            print("[LLM Provider] Note: OPENROUTER_API_KEY not found in environment.")
            return "test"
        return f"openrouter:{model_id}"

    elif provider == "nvidia":
        key = api_key or os.getenv("NVIDIA_API_KEY")
        model_id = model_name or os.getenv("LLM_MODEL", FREE_MODELS["nvidia"][0])
        if not key:
            print("[LLM Provider] Note: NVIDIA_API_KEY not found in environment.")
            return "test"
        try:
            from pydantic_ai.models import infer_model
            os.environ["OPENAI_API_KEY"] = key
            os.environ["OPENAI_BASE_URL"] = "https://integrate.api.nvidia.com/v1"
            return infer_model(f"openai:{model_id}")
        except Exception:
            return f"openai:{model_id}"

    else:
        return "test"


def get_fallback_chain() -> List[Dict[str, str]]:
    """
    Returns an ordered priority chain starting with Groq API, OpenRouter Qwen, and NVIDIA NIM.
    """
    chain = []
    
    # 1. Groq Free Tier (Active Key)
    if os.getenv("GROQ_API_KEY"):
        chain.append({"provider": "groq", "model": FREE_MODELS["groq"][0], "name": "Groq Llama 3.3 70B (Active Key)"})
        chain.append({"provider": "groq", "model": FREE_MODELS["groq"][1], "name": "Groq Mixtral 8x7B (Active Key)"})

    # 2. OpenRouter Qwen & Free Models
    if os.getenv("OPENROUTER_API_KEY"):
        chain.append({"provider": "openrouter", "model": FREE_MODELS["openrouter"][0], "name": "OpenRouter Qwen 3.7 Flash (Active Key)"})
        chain.append({"provider": "openrouter", "model": FREE_MODELS["openrouter"][1], "name": "OpenRouter Qwen Plus (Active Key)"})

    # 3. NVIDIA NIM Free Tier
    if os.getenv("NVIDIA_API_KEY"):
        chain.append({"provider": "nvidia", "model": FREE_MODELS["nvidia"][0], "name": "NVIDIA Llama 3.3 70B Instruct"})

    # 4. Fallback dry-run engine
    chain.append({"provider": "mock", "model": "test", "name": "Offline Harness Fallback Engine"})
    return chain


def get_llm_model(provider: Optional[str] = None, model_name: Optional[str] = None) -> Any:
    """Convenience accessor for LLM model initialization."""
    return configure_llm_provider(provider=provider, model_name=model_name)
