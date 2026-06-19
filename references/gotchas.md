# Gotchas

These rules come from failure modes and should override convenience.

- Do not run high-cost jobs without explicit approval. This includes video, `nano-banana-2`, and any item estimated at 5+ credits.
- Do not auto-retry video. A retry may spend credits again.
- Do not retry 401/402 blindly. 401 means cookie expired or missing; 402 means insufficient credits.
- Do not print `config/cookie.txt`; it is a login credential.
- Do not commit real prompt queues or outputs. Keep `prompts.txt`, `results.jsonl`, `failed.jsonl`, `done.txt`, `run.log`, and `images/*` private.
- Do not use `Qwen-Image-Edit` without `img=`.
- Do not use `Wan2.2-I2V-Lightning` without exactly one source image.
- Do not assume `aspectRatio` alone changes output shape; the script converts ratio into matching width/height.
- Do not preserve failed queue state by deleting `prompts.txt`; successful text rows are removed automatically, failed rows remain or go to `failed.jsonl`.
- Do not summarize a run from memory; use `--summary`, `results.jsonl`, or `run.log`.
