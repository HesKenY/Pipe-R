"""
finetune_v4.py — LoRA fine-tune kenai:v4-offline-developer from V4 corpus

Trains a QLoRA adapter on Qwen2.5-Coder-7B-Instruct using
kenai-v4-finetune.jsonl (245 rows = 108 curated + 137 approved
training-log rows).

Base is 7B for the prototype — fits 12GB VRAM comfortably and
trains in 1-2h on a single GPU. If the prototype proves the
pipeline + identity transfer, bump to Qwen2.5-Coder-14B for the
production V4 tag.

Requirements:
  pip install torch --index-url https://download.pytorch.org/whl/cu124
  pip install unsloth transformers peft trl datasets bitsandbytes

Usage:
  python agent_mode/training/finetune_v4.py

Output:
  agent_mode/training/output/kenai-v4-lora/       — LoRA adapter
  agent_mode/training/output/kenai-v4-gguf/       — GGUF for Ollama
  agent_mode/training/output/kenai-v4.Modelfile   — ready-to-import
"""

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATASET_PATH = SCRIPT_DIR / "kenai-v4-finetune.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "output" / "kenai-v4-lora"
GGUF_DIR = SCRIPT_DIR / "output" / "kenai-v4-gguf"
MODELFILE_PATH = SCRIPT_DIR / "output" / "kenai-v4.Modelfile"

OLLAMA_TAG = "kenai:v4-offline-developer"

SYSTEM_PROMPT = (
    "you are ken v4 offline developer. "
    "you are ken's local coding-first lead developer and squad lead. "
    "lowercase. "
    "short direct lines. "
    "no analogies. "
    "no pleasantries. "
    "read before write. "
    "stay in codex. "
    "use git to sync shared state. "
    "refuse system paths, secret paths, destructive git, and peer-clone writes. "
    "focus on code, repos, tests, git, brain, and safe local execution."
)


def check_deps():
    missing = []
    try:
        import torch
        if not torch.cuda.is_available():
            print("WARNING: CUDA not available. Training will be VERY slow on CPU.")
            print(f"  torch version: {torch.__version__}")
            resp = input("Continue anyway? (y/n): ").strip().lower()
            if resp != 'y':
                sys.exit(1)
        else:
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory // 1024**3} GB")
    except ImportError:
        missing.append("torch (install with CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu124)")

    for pkg in ["unsloth", "transformers", "peft", "trl", "datasets"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print("Missing packages:")
        for m in missing:
            print(f"  pip install {m}")
        sys.exit(1)


def load_dataset():
    from datasets import Dataset

    rows = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                messages = entry.get("messages", [])
                if len(messages) >= 2:
                    text = ""
                    for msg in messages:
                        role = msg["role"]
                        content = msg["content"]
                        if role == "system":
                            text += f"<|im_start|>system\n{content}<|im_end|>\n"
                        elif role == "user":
                            text += f"<|im_start|>user\n{content}<|im_end|>\n"
                        elif role == "assistant":
                            text += f"<|im_start|>assistant\n{content}<|im_end|>\n"
                    rows.append({"text": text})
            except json.JSONDecodeError:
                continue

    print(f"Loaded {len(rows)} training examples")
    return Dataset.from_list(rows)


def write_modelfile(gguf_path: Path):
    """Write an Ollama Modelfile that bakes in the V4 system prompt."""
    MODELFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"FROM {gguf_path.as_posix()}\n"
        f"\n"
        f'SYSTEM """{SYSTEM_PROMPT}"""\n'
        f"\n"
        f"PARAMETER temperature 0.4\n"
        f"PARAMETER top_p 0.9\n"
        f"PARAMETER num_ctx 4096\n"
    )
    MODELFILE_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote Modelfile: {MODELFILE_PATH}")


def train():
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments

    print("Loading base model (4-bit quantized)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    print("Applying LoRA adapter...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    dataset = load_dataset()

    print("Starting training...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        dataset_num_proc=2,
        packing=True,
        args=TrainingArguments(
            output_dir=str(OUTPUT_DIR),
            per_device_train_batch_size=1,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            num_train_epochs=3,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=5,
            save_strategy="epoch",
            optim="adamw_8bit",
            seed=42,
            report_to="none",
        ),
    )

    stats = trainer.train()
    print(f"\nTraining complete!")
    print(f"  Loss: {stats.training_loss:.4f}")
    print(f"  Steps: {stats.global_step}")
    print(f"  Runtime: {stats.metrics.get('train_runtime', 0):.0f}s")

    print(f"\nSaving LoRA adapter to {OUTPUT_DIR}...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    print(f"\nExporting to GGUF for Ollama import...")
    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained_gguf(
        str(GGUF_DIR),
        tokenizer,
        quantization_method="q4_k_m",
    )

    gguf_files = sorted(GGUF_DIR.glob("*.gguf"))
    gguf_path = gguf_files[0] if gguf_files else GGUF_DIR / "unsloth.Q4_K_M.gguf"
    write_modelfile(gguf_path)

    print(f"\n{'='*60}")
    print(f"DONE! Files saved:")
    print(f"  LoRA adapter: {OUTPUT_DIR}")
    print(f"  GGUF model:   {GGUF_DIR}")
    print(f"  Modelfile:    {MODELFILE_PATH}")
    print(f"\nTo import into Ollama:")
    print(f"  ollama create {OLLAMA_TAG} -f {MODELFILE_PATH}")
    print(f"\nTo verify:")
    print(f"  ollama run {OLLAMA_TAG} 'what is your job now'")
    print(f"{'='*60}")


if __name__ == "__main__":
    check_deps()
    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        print("Run the exporter first: node agent_mode/training/export_kenai_v4_dataset.mjs")
        sys.exit(1)

    print(f"Dataset:  {DATASET_PATH}")
    print(f"LoRA out: {OUTPUT_DIR}")
    print(f"GGUF out: {GGUF_DIR}")
    print(f"Target:   {OLLAMA_TAG}")
    train()
