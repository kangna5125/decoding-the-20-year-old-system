"""The core system: explain code, give a confidence score, and reuse reviewer corrections."""
import math
import os

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")  # safe on Mac GPUs, ignored elsewhere

import torch
from transformers import T5ForConditionalGeneration

from common import get_device, load_tokenizer, strip_docstring
from corrections import CorrectionStore

HIGH, MEDIUM = 0.60, 0.35  # confidence levels; tune them using the table printed by evaluate.py


def confidence_level(conf):
    return "High" if conf >= HIGH else "Medium" if conf >= MEDIUM else "Low"


class CodeExplainer:
    def __init__(self, model_dir, db_path="corrections.db", max_src=256, max_new_tokens=48):
        self.device = get_device()
        self.tok = load_tokenizer(model_dir)
        self.model = T5ForConditionalGeneration.from_pretrained(model_dir).to(self.device).eval()
        self.store = CorrectionStore(db_path) if db_path else None
        self.max_src, self.max_new_tokens = max_src, max_new_tokens

    def generate(self, code):
        """Return (explanation, confidence 0-1, was_input_truncated).

        Confidence = average probability the model gave to each word-piece it wrote
        (the geometric mean, taken from beam search's own score).
        """
        src = strip_docstring(code) or code
        full_len = len(self.tok(src).input_ids)
        enc = self.tok(src, return_tensors="pt", max_length=self.max_src, truncation=True)
        enc = {k: v.to(self.device) for k, v in enc.items()}
        with torch.no_grad():
            out = self.model.generate(**enc, num_beams=4, max_new_tokens=self.max_new_tokens,
                                      length_penalty=1.0, early_stopping=True,
                                      return_dict_in_generate=True, output_scores=True)
        text = self.tok.decode(out.sequences[0], skip_special_tokens=True).strip()
        conf = min(1.0, max(0.0, math.exp(out.sequences_scores[0].item())))
        return text, conf, full_len > self.max_src

    def explain(self, code):
        """Use a reviewer-verified note if one exists, otherwise ask the model."""
        if self.store is not None:
            hit = self.store.find(code)
            if hit:
                return {"source": "verified", "explanation": hit["corrected"],
                        "original": hit["original"], "reviewer": hit["reviewer"],
                        "saved_at": hit["created_at"], "similarity": hit["similarity"],
                        "confidence": None, "level": None, "truncated": False}
        text, conf, truncated = self.generate(code)
        return {"source": "model", "explanation": text, "confidence": conf,
                "level": confidence_level(conf), "truncated": truncated, "similarity": None}

    def save_correction(
        self,
        code,
        original,
        corrected,
        reviewer="",
        status="Approved",
        source="Human Reviewer",
        rule_type="Explanation Correction"
    ):
        if self.store is not None:
            self.store.save(
                code,
                original,
                corrected,
                reviewer=reviewer,
                status=status,
                source=source,
                rule_type=rule_type
            )
