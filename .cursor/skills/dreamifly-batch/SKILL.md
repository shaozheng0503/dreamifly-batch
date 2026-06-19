---
name: dreamifly-batch
description: 批量调用 Dreamifly 生成图片或视频。Use when the user asks to batch-generate images, edit images from references, create text-to-video or image-to-video, queue prompts, estimate generation cost, validate prompt queues, retry failed jobs, or summarize generated outputs.
compatibility: Requires Python 3 and network access to dreamifly.com. High-cost models require explicit user confirmation.
metadata:
  category: media-generation
---

# Dreamifly Batch

## Quick Start

1. Read the repository root `SKILL.md` for the full playbook.
2. Write real prompts to `prompts.txt` or provide `--prompts jobs.jsonl`.
3. Run `python3 dreamify.py --validate`, then `python3 dreamify.py --estimate`, then `python3 dreamify.py --dry-run`.
4. If any item costs 5+ credits, stop and ask for explicit confirmation before running.
5. Run `./run.sh` or `python3 dreamify.py -n N`.
6. Report from `results.jsonl` and `run.log`; never print `config/cookie.txt`.

## Useful Commands

- `python3 dreamify.py --validate`
- `python3 dreamify.py --estimate`
- `python3 dreamify.py --summary`
- `python3 dreamify.py --retry-failed`
- `python3 dreamify.py --prompts jobs.jsonl --results-file results.jsonl`

## References

- Model choice and cost rules: `references/model-selection.md`
- JSONL job examples: `examples/prompts.jsonl`
