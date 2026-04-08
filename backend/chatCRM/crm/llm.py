import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import os

# You can change model here
MODEL_NAME = os.getenv("HF_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

# Global cache (loaded once)
tokenizer = None
model = None


def load_model():
    global tokenizer, model

    if tokenizer is None or model is None:
        print("⬇️ Downloading / Loading model from HuggingFace...")

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            device_map="auto" if torch.cuda.is_available() else None
        )

        print("✅ Model loaded successfully")

    return tokenizer, model


def generate_human_reply(system_prompt: str, user_prompt: str) -> str:
    try:
        tokenizer, model = load_model()

        prompt = f"""
{system_prompt}

USER CONTEXT:
{user_prompt}

Assistant:
""".strip()

        inputs = tokenizer(prompt, return_tensors="pt")

        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id
        )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract only assistant part
        if "Assistant:" in response:
            response = response.split("Assistant:")[-1].strip()

        return response or "I checked that for you, but couldn't form a proper reply."

    except Exception as e:
        print("LLM ERROR:", str(e))
        return "I’ve checked what I can, but I’m having a little trouble replying right now. Let me connect you with a human agent."