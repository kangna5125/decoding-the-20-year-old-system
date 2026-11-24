"""Step 2: fine-tune CodeT5-small so it turns Python code into a plain-English description."""
import argparse
import json
import os
import time

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch
from torch.utils.data import DataLoader
from transformers import T5ForConditionalGeneration, get_linear_schedule_with_warmup

from common import get_device, load_tokenizer, read_jsonl


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_model", default="Salesforce/codet5-small")
    ap.add_argument("--data_dir", default="data")
    ap.add_argument("--out", default="models/codet5-small-csn")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch_size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--max_src", type=int, default=256)
    ap.add_argument("--max_tgt", type=int, default=48)
    ap.add_argument("--max_steps", type=int, default=0, help="stop early (for quick tests)")
    ap.add_argument("--log_every", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)

    torch.manual_seed(a.seed)
    device = get_device()
    print("Training on:", device)

    tok = load_tokenizer(a.base_model)
    model = T5ForConditionalGeneration.from_pretrained(a.base_model).to(device)
    train = read_jsonl(os.path.join(a.data_dir, "train.jsonl"))
    val = read_jsonl(os.path.join(a.data_dir, "val.jsonl"))
    print(f"train={len(train)}  val={len(val)}")

    def collate(batch):
        enc = tok([b["code"] for b in batch], max_length=a.max_src,
                  truncation=True, padding=True, return_tensors="pt")
        lab = tok(text_target=[b["description"] for b in batch], max_length=a.max_tgt,
                  truncation=True, padding=True, return_tensors="pt").input_ids
        lab[lab == tok.pad_token_id] = -100
        return {"input_ids": enc.input_ids, "attention_mask": enc.attention_mask, "labels": lab}

    tl = DataLoader(train, batch_size=a.batch_size, shuffle=True, collate_fn=collate)
    vl = DataLoader(val, batch_size=a.batch_size, collate_fn=collate)

    total = a.epochs * len(tl)
    if a.max_steps:
        total = min(total, a.max_steps)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    sched = get_linear_schedule_with_warmup(opt, int(0.05 * total), total)

    def val_loss():
        model.eval()
        losses = []
        with torch.no_grad():
            for b in vl:
                b = {k: v.to(device) for k, v in b.items()}
                losses.append(model(**b).loss.item())
        model.train()
        return sum(losses) / max(len(losses), 1)

    start, step, best, log = time.time(), 0, float("inf"), []
    model.train()
    for epoch in range(a.epochs):
        epoch_losses = []
        for b in tl:
            b = {k: v.to(device) for k, v in b.items()}
            loss = model(**b).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            step += 1
            loss_val = loss.item()
            epoch_losses.append(loss_val)
            if step % a.log_every == 0:
                print(f"epoch {epoch + 1}  step {step}/{total}  loss {loss_val:.3f}")
                log.append({"step": step, "train_loss": round(loss_val, 4)})
            if step >= total:
                break
        epoch_train_loss = sum(epoch_losses) / max(len(epoch_losses), 1)
        v = val_loss()
        print(f"== epoch {epoch + 1} done: train loss {epoch_train_loss:.3f}, validation loss {v:.3f}")
        log.append({"epoch": epoch + 1, "train_loss": round(epoch_train_loss, 4), "val_loss": round(v, 4)})
        if v < best:
            best = v
            os.makedirs(a.out, exist_ok=True)
            model.save_pretrained(a.out)
            tok.save_pretrained(a.out)
            print("   saved best model to", a.out)
        if step >= total:
            break

    info = {"args": vars(a), "device": str(device), "best_val_loss": round(best, 4),
            "minutes": round((time.time() - start) / 60, 1), "log": log}
    with open(os.path.join(a.out, "training_log.json"), "w") as f:
        json.dump(info, f, indent=2)
    print(f"Done in {info['minutes']} min. Best validation loss {best:.3f}")


if __name__ == "__main__":
    main()
