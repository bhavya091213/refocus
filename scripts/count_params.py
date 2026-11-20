"""Count SVD-based model parameters from configs only (meta device, no weights).

Usage: python scripts/count_params.py --configs <dir with unet/ vae/ image_encoder/> --out <json>
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import torch
from accelerate import init_empty_weights
from diffusers import AutoencoderKLTemporalDecoder, UNetSpatioTemporalConditionModel
from transformers import CLIPVisionConfig, CLIPVisionModelWithProjection

TRAIN_FILTER = "temporal_transformer_block"  # project's exact training filter
# Category rules, first match wins (order matters: temporal_transformer_blocks
# contains the substring "transformer_blocks").
RULES = [
    ("temporal_transformer", "temporal_transformer_block"),
    ("spatial_transformer", ".transformer_blocks."),
    ("spatial_resnet", ".spatial_res_block."),
    ("temporal_resnet", ".temporal_res_block."),
    ("sampler_conv", ".downsamplers."),
    ("sampler_conv", ".upsamplers."),
]
CATS = ["spatial_resnet", "temporal_resnet", "spatial_transformer",
        "temporal_transformer", "sampler_conv", "other"]


def categorize(name):
    for cat, sub in RULES:
        if sub in name:
            return cat
    return "other"


def block_of(name):
    p = name.split(".")
    if p[0] in ("down_blocks", "up_blocks"):
        return f"{p[0]}.{p[1]}"
    if p[0] == "mid_block":
        return "mid_block"
    if p[0] in ("conv_in",):
        return "conv_in"
    if p[0] in ("time_embedding", "add_time_proj", "add_embedding", "time_proj"):
        return "time_and_added_cond_embeddings"
    if p[0] in ("conv_norm_out", "conv_out"):
        return "final_norm_conv_out"
    return "unassigned:" + p[0]


def build(cls, cfg):
    with init_empty_weights():
        return cls.from_config(cfg)


def conv_out_size(n, k=3, s=2, p=1):
    return (n + 2 * p - k) // s + 1


def unet_report(cfg, frames, width_px, height_px):
    m = build(UNetSpatioTemporalConditionModel, cfg)
    params = {n: p.numel() for n, p in m.named_parameters()}
    total = sum(params.values())
    trainable = sum(v for n, v in params.items() if TRAIN_FILTER in n)
    blocks = defaultdict(lambda: defaultdict(int))
    for n, v in params.items():
        b = block_of(n)
        blocks[b][categorize(n)] += v
        blocks[b]["total"] += v
    overall = defaultdict(int)
    for n, v in params.items():
        overall[categorize(n)] += v

    # attention structure
    tst = [(n, mod) for n, mod in m.named_modules()
           if type(mod).__name__ == "TransformerSpatioTemporalModel"]
    n_tb = sum(1 for n in params if TRAIN_FILTER in n and n.endswith("norm_in.weight"))
    heads = {}
    for n, mod in tst:
        key = n.split(".attentions")[0]
        tb = mod.temporal_transformer_blocks[0]
        sb = mod.transformer_blocks[0]
        heads[key] = dict(
            channels=mod.inner_dim,
            heads=sb.attn1.heads,
            head_dim=mod.inner_dim // sb.attn1.heads,
            temporal_heads=tb.attn1.heads,
            cross_attn_dim=getattr(sb.attn2, "to_k").in_features,
        )

    # one temporal transformer block at each width
    def tblock(prefix):
        mod = dict(m.named_modules())[prefix]
        layers = {n: list(p.shape) for n, p in mod.named_parameters()}
        return dict(params=sum(p.numel() for p in mod.parameters()), layers=layers)

    tblocks = {
        "320": tblock("down_blocks.0.attentions.0.temporal_transformer_blocks.0"),
        "640": tblock("down_blocks.1.attentions.0.temporal_transformer_blocks.0"),
        "1280": tblock("down_blocks.2.attentions.0.temporal_transformer_blocks.0"),
    }

    # feature maps: latent H x W per frame
    h, w = height_px // 8, width_px // 8
    chans = cfg["block_out_channels"]
    fm = {"input_latent": dict(c=cfg["in_channels"], h=h, w=w)}
    fm["conv_in_out"] = dict(c=chans[0], h=h, w=w)
    cur_h, cur_w = h, w
    down_types = cfg["down_block_types"]
    for i, c in enumerate(chans):
        entry = dict(c=c, h_during_block=cur_h, w_during_block=cur_w)
        if i < len(chans) - 1:  # DownBlock has a stride-2 conv downsampler except last
            cur_h, cur_w = conv_out_size(cur_h), conv_out_size(cur_w)
        entry.update(c_out=c, h_out=cur_h, w_out=cur_w, type=down_types[i])
        fm[f"down_block_{i}"] = entry
    fm["mid_block"] = dict(c=chans[-1], h=cur_h, w=cur_w)
    up_chans = list(reversed(chans))
    for i, c in enumerate(up_chans):
        entry = dict(c=c, h_during_block=cur_h, w_during_block=cur_w,
                     type=cfg["up_block_types"][i])
        if i < len(up_chans) - 1:  # nearest 2x upsample + conv
            cur_h, cur_w = cur_h * 2, cur_w * 2
        entry.update(h_out=cur_h, w_out=cur_w)
        fm[f"up_block_{i}"] = entry
    fm["output"] = dict(c=cfg["out_channels"], h=cur_h, w=cur_w)

    return dict(
        total=total,
        trainable_temporal_transformer=trainable,
        trainable_pct=100 * trainable / total,
        overall_by_category=dict(overall),
        by_block={k: dict(v) for k, v in blocks.items()},
        conv_in_weight_shape=list(m.conv_in.weight.shape),
        conv_out_weight_shape=list(m.conv_out.weight.shape),
        block_out_channels=chans,
        num_attention_heads_cfg=cfg["num_attention_heads"],
        num_TransformerSpatioTemporalModel=len(tst),
        num_temporal_transformer_blocks=n_tb,
        attention_per_module=heads,
        temporal_transformer_block_internals=tblocks,
        input_assumption=dict(frames=frames, width_px=width_px, height_px=height_px,
                              latent_h=h, latent_w=w),
        feature_maps=fm,
    )


def vae_report(cfg):
    m = build(AutoencoderKLTemporalDecoder, cfg)
    cnt = lambda mod: sum(p.numel() for p in mod.parameters())
    total = cnt(m)
    enc, dec = cnt(m.encoder), cnt(m.decoder)
    return dict(
        total=total, encoder=enc, decoder=dec,
        other=total - enc - dec,  # quant_conv
        block_out_channels=cfg["block_out_channels"],
        latent_channels=cfg["latent_channels"],
        scaling_factor=cfg["scaling_factor"],
        spatial_downsample_factor=2 ** (len(cfg["block_out_channels"]) - 1),
    )


def clip_report(cfg):
    c = CLIPVisionConfig(**{k: v for k, v in cfg.items()
                            if k not in ("architectures", "model_type", "torch_dtype",
                                         "transformers_version", "_name_or_path")})
    with init_empty_weights():
        m = CLIPVisionModelWithProjection(c)
    n_patch = (c.image_size // c.patch_size) ** 2
    return dict(
        total=sum(p.numel() for p in m.parameters()),
        hidden_size=c.hidden_size, layers=c.num_hidden_layers,
        heads=c.num_attention_heads, patch_size=c.patch_size, image_size=c.image_size,
        num_tokens=n_patch + 1, num_patches=n_patch, projection_dim=c.projection_dim,
        intermediate_size=c.intermediate_size,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--frames", type=int, default=9)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=896)
    a = ap.parse_args()
    load = lambda d: json.loads((a.configs / d / "config.json").read_text())
    out = dict(
        rules=dict(trainable_filter=TRAIN_FILTER, categories=RULES),
        unet=unet_report(load("unet"), a.frames, a.width, a.height),
        vae=vae_report(load("vae")),
        clip=clip_report(load("image_encoder")),
        torch=torch.__version__,
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
