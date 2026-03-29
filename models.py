"""
models.py
---------
QwenVLExtractor   — wraps Qwen2-VL-2B-Instruct for image-based text extraction.
QwenSLMStructurer — wraps Qwen2.5-0.5B-Instruct for structured output refinement.
"""

from __future__ import annotations
import torch
import numpy as np
from PIL import Image
from typing import Any, Dict


# ─────────────────────────────────────────────────────────────────────────────
# Qwen2-VL  (2B) — Vision Language Model for OCR / text extraction
# ─────────────────────────────────────────────────────────────────────────────

VLM_MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"
SLM_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"


class QwenVLExtractor:
    """
    Loads Qwen2-VL-2B-Instruct from HuggingFace and exposes an `extract` method
    that takes a PIL Image and returns the extracted text with a confidence score.
    """

    def __init__(self, device: str | None = None):
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            VLM_MODEL_ID,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
        )
        if self.device != "cuda":
            self.model = self.model.to(self.device)
        self.model.eval()

        self.processor = AutoProcessor.from_pretrained(VLM_MODEL_ID)

    # ── Prompt ────────────────────────────────────────────────────────────────

    SYSTEM_PROMPT = (
        "You are an expert document analysis system. "
        "Extract ALL text visible in the provided image with maximum accuracy. "
        "Preserve the original structure: headings, paragraphs, tables, bullet points. "
        "Output only the extracted content — no commentary."
    )

    USER_PROMPT = (
        "Please extract all text from this document image. "
        "Preserve structure and formatting as much as possible."
    )

    # ── Main extraction ───────────────────────────────────────────────────────

    def extract(self, image: Image.Image, max_new_tokens: int = 2048) -> Dict[str, Any]:
        """
        Args:
            image: PIL Image
            max_new_tokens: max tokens to generate

        Returns:
            dict with keys: text (str), confidence (float 0–1)
        """
        from qwen_vl_utils import process_vision_info  # installed with transformers

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text",  "text": self.USER_PROMPT},
                ],
            }
        ]

        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self.processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                output_scores=True,
                return_dict_in_generate=True,
                do_sample=False,
            )

        # Decode text
        generated_ids  = output.sequences[:, inputs["input_ids"].shape[1]:]
        extracted_text = self.processor.batch_decode(
            generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True
        )[0]

        # Compute mean token confidence
        confidence = self._compute_confidence(output.scores)

        return {"text": extracted_text.strip(), "confidence": confidence}

    # ── Confidence helper ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_confidence(scores) -> float:
        if not scores:
            return 0.0
        token_probs = []
        for step_scores in scores:
            probs     = torch.softmax(step_scores, dim=-1)
            max_probs = probs.max(dim=-1).values
            token_probs.append(max_probs.mean().item())
        return float(np.mean(token_probs))


# ─────────────────────────────────────────────────────────────────────────────
# Qwen2.5-0.5B — Small Language Model for structured output
# ─────────────────────────────────────────────────────────────────────────────

class QwenSLMStructurer:
    """
    Loads Qwen2.5-0.5B-Instruct and refines raw extracted text into a
    structured, clean format (sections, key-value pairs, summaries).
    """

    def __init__(self, device: str | None = None):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(SLM_MODEL_ID)
        self.model     = AutoModelForCausalLM.from_pretrained(
            SLM_MODEL_ID,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
        )
        if self.device != "cuda":
            self.model = self.model.to(self.device)
        self.model.eval()

    SYSTEM_PROMPT = (
        "You are a document structuring assistant. "
        "Given raw extracted text from a document, your task is to:\n"
        "1. Identify and label document sections clearly.\n"
        "2. Preserve all original text — do not omit or paraphrase content.\n"
        "3. Format tables, lists, and key-value pairs cleanly.\n"
        "4. Add a brief 2–3 sentence summary at the top under 'SUMMARY'.\n"
        "Output only the structured result."
    )

    def structure(self, raw_text: str, max_new_tokens: int = 2048) -> str:
        """
        Takes raw extracted text and returns a structured string.
        Falls back to the raw text if the model call fails.
        """
        user_content = f"Structure the following extracted document text:\n\n{raw_text}"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ]

        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device)

        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated = out[0][inputs["input_ids"].shape[1]:]
        result    = self.tokenizer.decode(generated, skip_special_tokens=True).strip()

        return result if result else raw_text