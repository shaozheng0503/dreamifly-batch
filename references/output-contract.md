# Output Contract

Agents should report from structured outputs, not from guesswork.

## Files

- `images/*`: downloaded images/videos
- `images/*.json`: sidecar metadata for each media file
- `results.jsonl`: one structured record per processed item
- `failed.jsonl`: failed items that can be requeued with `--retry-failed`
- `done.txt`: human-readable log of completed/cached/failed rows
- `run.log`: timestamped execution log

## Report Format

After a run:

1. Prefer `python3 dreamify.py --summary`.
2. If more detail is needed, read `results.jsonl`.
3. Report success count, failure count, output paths, and fatal error type if any.
4. For 401, say the login cookie is missing or expired; do not print cookie content.
5. For 402, say credits are insufficient and suggest changing to cheap models or recharging.

## Privacy

Do not commit or disclose `prompts.txt`, `done.txt`, `run.log`, `results.jsonl`, `failed.jsonl`, `images/*`, or `config/cookie.txt`.
