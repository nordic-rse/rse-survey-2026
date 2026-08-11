"""Hugging Face model access: shared on-disk cache, embedder, label LLM.

Heavy ML imports are deferred to call time so the rest of the package stays
light. Models are cached in-process so a multi-question run loads each once.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rse_survey.config.paths import REPO_ROOT

# Optional project-local Hub cache (used only when no HF cache env/default exists yet)
HF_CACHE_ROOT = REPO_ROOT / ".hf_cache"

# In-process caches so multi-config runs load each model once
_EMBEDDERS: dict[str, Any] = {}
_LABELERS: dict[str, Any] = {}


def configure_hf_cache() -> Path:
    """Resolve the shared on-disk Hub cache (download once, reuse across questions).

    Order of preference:
    1. ``HF_HUB_CACHE`` / ``HF_HOME`` already set in the environment
    2. Default ``~/.cache/huggingface`` if it already exists (keeps prior downloads)
    3. Project-local ``.hf_cache/``
    """
    if "HF_HUB_CACHE" in os.environ:
        hub = Path(os.environ["HF_HUB_CACHE"])
        hub.mkdir(parents=True, exist_ok=True)
        return hub

    if "HF_HOME" in os.environ:
        home = Path(os.environ["HF_HOME"])
        hub = home / "hub"
        hub.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HUB_CACHE", str(hub))
        return hub

    default_home = Path.home() / ".cache" / "huggingface"
    if default_home.exists():
        os.environ.setdefault("HF_HOME", str(default_home))
        os.environ.setdefault("HF_HUB_CACHE", str(default_home / "hub"))
        return Path(os.environ["HF_HUB_CACHE"])

    hub = HF_CACHE_ROOT / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(HF_CACHE_ROOT)
    os.environ["HF_HUB_CACHE"] = str(hub)
    os.environ["TRANSFORMERS_CACHE"] = str(HF_CACHE_ROOT / "transformers")
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(
        HF_CACHE_ROOT / "sentence-transformers"
    )
    return hub


def hub_model_dir(repo_id: str) -> Path:
    return Path(os.environ["HF_HUB_CACHE"]) / ("models--" + repo_id.replace("/", "--"))


def model_is_cached(repo_id: str) -> bool:
    root = hub_model_dir(repo_id)
    if not root.exists():
        return False
    # A completed download has at least one snapshots/ revision with files.
    snaps = root / "snapshots"
    return snaps.exists() and any(snaps.iterdir())


def ensure_model_on_disk(repo_id: str) -> Path:
    """Download ``repo_id`` into the shared cache if missing; never re-fetch if present."""
    from huggingface_hub import snapshot_download

    configure_hf_cache()
    cached = model_is_cached(repo_id)
    if cached:
        print(f"Using cached weights for {repo_id} under {hub_model_dir(repo_id)}")
        local = snapshot_download(repo_id=repo_id, local_files_only=True)
    else:
        print(f"Downloading weights for {repo_id} once into {HF_CACHE_ROOT} …")
        local = snapshot_download(repo_id=repo_id, local_files_only=False)
        print(f"Cached {repo_id} at {local}")
    return Path(local)


def get_embedder(model_name: str) -> Any:
    """Load embedding model once per process; weights come from shared disk cache."""
    if model_name in _EMBEDDERS:
        print(f"Reusing in-memory embedding model {model_name}")
        return _EMBEDDERS[model_name]

    from sentence_transformers import SentenceTransformer

    local = ensure_model_on_disk(model_name)
    print(f"Loading embedding model {model_name} into memory (CPU) …")
    # Keep embeddings on CPU so an 8GB GPU can host the label model.
    model = SentenceTransformer(str(local), device="cpu")
    _EMBEDDERS[model_name] = model
    return model


def release_embedders_from_gpu() -> None:
    """Move cached embedders to CPU and free CUDA cache before loading a large LLM."""
    import gc

    import torch

    for model in _EMBEDDERS.values():
        try:
            model.to("cpu")
        except Exception:
            pass
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def get_labeler(label_model: str, label_load: str = "4bit") -> Any:
    """Load label pipeline once per process; weights come from shared disk cache.

    ``label_load`` controls VRAM use:
      - ``4bit``: bitsandbytes NF4 (fits ~8GB GPUs for 7B models) — default
      - ``8bit``: bitsandbytes 8-bit
      - ``fp16``: full float16 on GPU (needs ~14GB+ for 7B)
      - ``cpu``: CPU only (slow, no GPU needed)
    """
    cache_key = f"{label_model}|{label_load}"
    if cache_key in _LABELERS:
        print(f"Reusing in-memory label model {cache_key}")
        return _LABELERS[cache_key]

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    release_embedders_from_gpu()

    local = ensure_model_on_disk(label_model)
    print(f"Loading label model {label_model} ({label_load}) into memory …")
    tokenizer = AutoTokenizer.from_pretrained(
        str(local),
        clean_up_tokenization_spaces=False,
        local_files_only=True,
    )

    load = label_load.lower().strip()
    use_cuda = torch.cuda.is_available() and load != "cpu"
    if load in {"4bit", "8bit"} and not use_cuda:
        print(f"{load} requested but CUDA unavailable — falling back to CPU")
        load = "cpu"

    model_kwargs: dict[str, Any] = {"local_files_only": True}
    pipe_kwargs: dict[str, Any] = {}

    if load == "4bit":
        from transformers import BitsAndBytesConfig

        print("Using 4-bit quantization (recommended on ≤8GB GPUs)")
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs["device_map"] = "auto"
    elif load == "8bit":
        from transformers import BitsAndBytesConfig

        print("Using 8-bit quantization")
        model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
        model_kwargs["device_map"] = "auto"
    elif load == "fp16":
        if not use_cuda:
            raise RuntimeError("label_load=fp16 requires CUDA")
        print("Using float16 on GPU (needs substantial VRAM for 7B)")
        model_kwargs["dtype"] = torch.float16
        model_kwargs["device_map"] = "auto"
    elif load == "cpu":
        print("Running label model on CPU (slow for 7B)")
        pipe_kwargs["device"] = -1
    else:
        raise ValueError(
            f"Unknown label_load={label_load!r}; use one of: 4bit, 8bit, fp16, cpu"
        )

    model = AutoModelForCausalLM.from_pretrained(str(local), **model_kwargs)

    gen_config = model.generation_config
    gen_config.max_new_tokens = 16
    gen_config.do_sample = False
    gen_config.max_length = None
    gen_config.temperature = None
    gen_config.top_p = None
    gen_config.top_k = None
    if tokenizer.pad_token_id is not None:
        gen_config.pad_token_id = tokenizer.pad_token_id
    elif tokenizer.eos_token_id is not None:
        gen_config.pad_token_id = tokenizer.eos_token_id

    pipe_kwargs["model"] = model
    pipe_kwargs["tokenizer"] = tokenizer
    labeler = pipeline("text-generation", **pipe_kwargs)
    _LABELERS[cache_key] = labeler
    return labeler
