"""
finetune_v2.py — LoRA fine-tune kenai:v2 from curated corpus

Trains a QLoRA adapter on top of qwen2.5-coder:14b using the
curated kenai-v2-finetune.jsonl dataset.

Requirements:
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
  pip install unsloth transformers peft trl datasets bitsandbytes

Usage:
  python agent_mode/training/finetune_v2.py

Output:
  agent_mode/training/output/kenai-v2-lora/  — LoRA adapter
  agent_mode/training/output/kenai-v2-gguf/  — GGUF for Ollama import
"""

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATASET_PATH = SCRIPT_DIR / "kenai-v2-finetune.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "output" / "kenai-v2-lora"
GGUF_DIR = SCRIPT_DIR / "output" / "kenai-v2-gguf"

# ── Verify deps ──────────────────────────────────────────

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
    """Load the curated JSONL into HuggingFace Dataset format."""
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
                    # Format as chat template
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


def train():
    """Run QLoRA fine-tune."""
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments

    # ── Load base model in 4-bit ──
    print("Loading base model (4-bit quantized)...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
        max_seq_length=2048,
        dtype=None,  # auto-detect
        load_in_4bit=True,
    )

    # ── Apply LoRA adapter ──
    print("Applying LoRA adapter...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,              # LoRA rank — 16 is good for 14B
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0,    # unsloth optimized = 0
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # ── Load dataset ──
    dataset = load_dataset()

    # ── Training config ──
    print("Starting training...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=2048,
        dataset_num_proc=2,
        packing=True,  # pack short examples together for efficiency
        args=TrainingArguments(
            output_dir=str(OUTPUT_DIR),
            per_device_train_batch_size=1,  # 12GB VRAM constraint
            gradient_accumulation_steps=4,
            warmup_steps=5,
            num_train_epochs=3,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=5,
            save_strategy="epoch",
            optim="adamw_8bit",
            seed=42,
            report_to="none",  # no wandb/mlflow
        ),
    )

    # ── Train ──
    stats = trainer.train()
    print(f"\nTraining complete!")
    print(f"  Loss: {stats.training_loss:.4f}")
    print(f"  Steps: {stats.global_step}")
    print(f"  Runtime: {stats.metrics.get('train_runtime', 0):.0f}s")

    # ── Save LoRA adapter ──
    print(f"\nSaving LoRA adapter to {OUTPUT_DIR}...")
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    # ── Export to GGUF for Ollama ──
    print(f"\nExporting to GGUF for Ollama import...")
    os.makedirs(str(GGUF_DIR), exist_ok=True)
    model.save_pretrained_gguf(
        str(GGUF_DIR),
        tokenizer,
        quantization_method="q4_k_m",  # 4-bit quantized, good balance
    )

    print(f"\n{'='*60}")
    print(f"DONE! Files saved:")
    print(f"  LoRA adapter: {OUTPUT_DIR}")
    print(f"  GGUF model:   {GGUF_DIR}")
    print(f"\nTo import into Ollama:")
    print(f"  ollama create kenai:v2 -f <modelfile pointing to the GGUF>")
    print(f"{'='*60}")


if __name__ == "__main__":
    check_deps()
    if not DATASET_PATH.exists():
        print(f"Dataset not found: {DATASET_PATH}")
        print("Run the corpus builder first.")
        sys.exit(1)

    print(f"Dataset: {DATASET_PATH}")
    print(f"Output:  {OUTPUT_DIR}")
    train()
