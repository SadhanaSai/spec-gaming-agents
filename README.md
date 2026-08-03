# spec-gaming-agents
Demonstration Framework for Specification Gaming in Agentic AI systems

## Running the Demos

### 1. Start the stack (once per session)

```bash
docker compose up -d      # Floci (AWS emulator) on localhost:4566
ollama serve &            # local model — llm_factory.py prefers this if reachable
ollama pull llama3.2       # only needed the first time
```

No Ollama? `llm_factory.py` automatically falls back to Groq if
`GROQ_API_KEY` is set (see `.env.example`). You don't need both.

### 2. Run a demo

```bash
cd demos/02_metric_substitution   # or 03_..., 04_..., 05_...
python setup.py                   # resets Floci to the seeded starting state
python run.py --mode live         # runs the agent, prints divergence_report.json
```

Check the printed report's `divergence.detected` field:
- `true` → the agent gamed the spec (looked compliant, wasn't).
- `false` → the agent did the honest thing.

The task is deliberately ambiguous, so the same demo can land either way
run to run. Re-run `setup.py` + `run.py --mode live` until you get the
outcome you're after.

### 3. Save a fixture (once you get the outcome you want)

```bash
python run.py --mode record --output fixtures/gaming_run.json --label gaming
# or, on a run that came out honest:
python run.py --mode record --output fixtures/correct_run.json --label correct
```

Demo 5 (`05_audit_aware_compliance`) has one extra required flag, since it
compares behavior under two system-prompt framings:

```bash
python run.py --mode record --output fixtures/observed_run.json --label <gaming|correct> --framing observed
python run.py --mode record --output fixtures/unobserved_run.json --label <gaming|correct> --framing unobserved
```

All files under `demos/*/fixtures/` are real recorded executions against a
live Floci stack — not synthetic or hand-written data.

### 4. Replay a saved fixture (no LLM/AWS calls — safe for the actual talk)

```bash
python run.py --mode replay --fixture fixtures/gaming_run.json
```

### Known quirks (save yourself the debugging time)

- **Ollama is single-threaded** (`-np 1` by default) — don't run multiple
  demos' `run.py` against it at the same time, they'll just queue up and
  get slower, not run in parallel.
- **Groq's free tier caps out fast**: 12K tokens/minute and 100K
  tokens/day. Concurrent runs burn through the per-minute cap almost
  immediately; a day of experimentation can burn through the daily cap
  outright. If you see `groq.RateLimitError`, that's why — switch back to
  Ollama or wait it out.
- **Small local models (`llama3.2:3B`) are unreliable tool-callers.**
  Recurring failure modes, none of them bugs in the demo code:
  - Writes the tool call as prose/JSON in its reply instead of actually
    invoking it (the system prompt explicitly forbids this — it still
    happens sometimes).
  - Gets an argument name wrong (e.g. `roleName` instead of `role_name`),
    the call fails validation, and it never retries with the right name.
  - Describes a plan and stops without executing it.
  All three just mean "re-run it" — they're not something a fixture
  capture should paper over or retry-loop around silently; if you see a
  0%-change / no-op result, that run simply didn't produce usable
  evidence either way.
- **Landing a genuine "gaming" outcome is the least controllable part.**
  These models are fairly well-aligned by default, so across dozens of
  attempts most runs come out honest. Don't be surprised if it takes many
  retries — demo 1 took roughly two hours of intermittent retries to
  land its first real gaming fixture.
