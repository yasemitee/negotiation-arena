"""
LLM Engine - Abstraction layer for language model inference.

Provides a unified interface for interacting with LLMs, currently supporting
local models via llama-cpp-python.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Any, TYPE_CHECKING
import time

# allows using other model backends if llama-cpp-python is not installed.
# This will be useful when adding support for additional local models in the future.
try:
    from llama_cpp import Llama  # type: ignore[import-not-found]
    LLAMA_AVAILABLE = True
except ImportError:
    Llama = None
    LLAMA_AVAILABLE = False

if TYPE_CHECKING:
    from llama_cpp import Llama as LlamaType  # type: ignore[import-not-found]
else:
    LlamaType = Any

@dataclass
class GenerationConfig:
    """
    Parameters controlling text generation behavior.
    Attributes:
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling probability mass
        top_k: Top-K sampling
        repeat_penalty: Penalty for repeated tokens
        stop_sequences: List of sequences to stop generation upon   
    """
    max_tokens: int = 512 
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop_sequences: list = None
    
    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = ["<|eot_id|>", "<|end_of_turn|>"]


class LLMEngine:
    """
    Singleton wrapper for local LLM inference.
    Currently uses llama-cpp-python.
    Attributes:
        model_path: Path to the GGUF model file
        n_gpu_layers: Number of layers to offload to GPU
        context_length: Maximum context window size in tokens
    """
    
    _instance: Optional["LLMEngine"] = None
    _model: Optional[LlamaType] = None
    _model_path: Optional[str] = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure a single instance across the application."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        n_gpu_layers: int = -1,
        context_length: int = 8192  # Full model capacity for Llama-3
    ):
        """
        Initialize or reconfigure the engine.
        Args:
            model_path: Path to GGUF model file. If None, searches default locations.
            n_gpu_layers: Layers to offload to GPU. -1 means all.
            context_length: Maximum context window size in tokens.
        """
        if model_path and model_path != self._model_path:
            self._model_path = model_path
            self._model = None  
        
        self._n_gpu_layers = n_gpu_layers
        self._context_length = context_length
        self._default_config = GenerationConfig()
    
    def _find_model(self) -> str:
        """Locate model file in models directory."""
        search_paths = [
            Path.cwd() / "models",
            Path.home() / ".cache" / "llama_models",
            Path("/models"),
        ]
        
        for base in search_paths:
            if base.exists():
                gguf_files = list(base.glob("*.gguf"))
                if gguf_files:
                    return str(gguf_files[0])
        
        raise FileNotFoundError(
            "No gguf model found. Please place a model in ./models/ "
            "or specify a model_path."
        )
    
    def _ensure_loaded(self) -> LlamaType:
        """Lazy-load the model on first use."""
        if not LLAMA_AVAILABLE:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Install with: pip install llama-cpp-python"
            )
        
        if self._model is not None:
            return self._model
        
        if self._model_path is None:
            self._model_path = self._find_model()
        
        if not os.path.exists(self._model_path):
            raise FileNotFoundError(f"Model not found: {self._model_path}")
        
        print(f"[Engine] Loading model from: {self._model_path}")
        load_start = time.time()
        
        self._model = Llama(
            model_path=self._model_path,
            n_gpu_layers=self._n_gpu_layers,
            n_ctx=self._context_length,
            verbose=False
        )
        
        load_time = time.time() - load_start
        print(f"[Engine] Model loaded in {load_time:.1f}s")
        
        return self._model
    
    def generate(
        self,
        messages: list[dict],
        config: Optional[GenerationConfig] = None,
        retry_attempts: int = 2
    ) -> str:
        """
        Generate a response given conversation history.
        Args:
            messages: Chat history in OpenAI format
            config: Generation parameters (uses defaults if None)
            retry_attempts: Number of retries on empty/failed generation            
        Returns:
            Generated text response
        """
        model = self._ensure_loaded()
        cfg = config or self._default_config
        
        for attempt in range(retry_attempts + 1):
            try:
                response = model.create_chat_completion(
                    messages=messages,
                    max_tokens=cfg.max_tokens,
                    temperature=cfg.temperature,
                    top_p=cfg.top_p,
                    top_k=cfg.top_k,
                    repeat_penalty=cfg.repeat_penalty,
                    stop=cfg.stop_sequences
                )
                
                content = response["choices"][0]["message"]["content"]
                
                if content and content.strip():
                    return content.strip()
                
                if attempt < retry_attempts:
                    print(f"[Engine] Empty response, retrying ({attempt + 1}/{retry_attempts})")
                    
            except Exception as e:
                if attempt < retry_attempts:
                    print(f"[Engine] Generation failed: {e}, retrying...")
                    time.sleep(0.5) 
                else:
                    raise
        
        return "[Generation failed after retries]"
    
    @classmethod
    def generate_response(cls, messages: list[dict]) -> str:
        """
        Creates/uses singleton instance with default settings.
        Args:
            messages: Chat history in OpenAI format
        Returns:
            Generated text response
        """
        instance = cls()
        return instance.generate(messages)
    
    def set_default_config(self, config: GenerationConfig) -> None:
        """
        Update default generation parameters.
        Args:
            config: New default configuration to apply
        """
        if not isinstance(config, GenerationConfig):
            raise TypeError("config must be a GenerationConfig instance")
        self._default_config = config
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance and unload the model."""
        if cls._instance and cls._model:
            cls._instance.unload()
        cls._instance = None
        cls._model = None
        cls._model_path = None
    
    @property
    def model_name(self) -> str:
        """
        Extract model name from path for logging.
         Returns:
            Model name string
         """
        if self._model_path:
            return Path(self._model_path).stem
        return "unknown"
    
    def unload(self) -> None:
        """Release model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
            print("[Engine] Model unloaded")