# Output Contract

- Prefer `python3 dreamify.py --summary` after a run.
- Read `results.jsonl` for per-item status, files, model, parameters, and errors.
- Read `run.log` only for diagnostics or fatal failures.
- Never print or expose `config/cookie.txt`.
- Report success count, failure count, output paths, and the next safe retry step.
