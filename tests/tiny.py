"""Builds a tiny random T5 model + tokenizer on disk so the whole pipeline can be tested offline."""
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
from transformers import PreTrainedTokenizerFast, T5Config, T5ForConditionalGeneration


def build_tiny(path, texts):
    tk = Tokenizer(models.BPE(unk_token="<unk>"))
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tk.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=300, special_tokens=["<pad>", "</s>", "<unk>"],
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tk.train_from_iterator(texts, trainer)
    tok = PreTrainedTokenizerFast(tokenizer_object=tk, pad_token="<pad>",
                                  eos_token="</s>", unk_token="<unk>")
    cfg = T5Config(vocab_size=len(tok), d_model=32, d_ff=64, d_kv=8, num_heads=4,
                   num_layers=2, num_decoder_layers=2, pad_token_id=0, eos_token_id=1,
                   decoder_start_token_id=0)
    T5ForConditionalGeneration(cfg).save_pretrained(path)
    tok.save_pretrained(path)
