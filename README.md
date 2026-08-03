# spec-gaming-agents
Demonstration Framework for Specification Gaming in Agentic AI systems

## Running the Demos

### 1. Start the stack (once per session)

```bash
docker compose up -d              # Floci (AWS emulator) on localhost:4566
ollama serve &                    # local model — llm_factory.py prefers this if reachable
ollama pull qwen2.5:7b-instruct   # only needed the first time
```

No Ollama? `llm_factory.py` automatically falls back to Groq if
`GROQ_API_KEY` is set (see `.env.example`). You don't need both — but if
`ollama serve` isn't actually running, the fallback to Groq happens
silently, and Groq's free tier is easy to exhaust (see Known quirks
below). Check `curl localhost:11434/api/tags` if a run behaves
unexpectedly and you expected Ollama to be handling it.

### 2. Run a demo

```bash
cd demos/02_metric_substitution   # or 03_..., 04_...
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
  evidence either way. `qwen2.5:7b-instruct` (the model these repo's
  fixtures were recorded with) is meaningfully more reliable at actually
  calling tools than `llama3.2:3B`, at the cost of a slower first-token
  time and a larger download.
- **If `ollama serve` isn't running, failures go silent, not loud.**
  `llm_factory.py` falls back to Groq whenever it can't reach
  `OLLAMA_BASE_URL` — including when Ollama was simply never started or
  was killed earlier in the session. You won't get an error for this; you
  just silently start burning Groq quota, and once that's exhausted a run
  can produce a single `list_*` tool call and then die mid-turn on a
  `groq.RateLimitError`, which looks exactly like a one-step no-op in the
  saved fixture unless you check the raw output for the traceback.
- **Landing a genuine "gaming" outcome is the least controllable part.**
  These models are fairly well-aligned by default, so across dozens of
  attempts most runs come out honest. Don't be surprised if it takes many
  retries. In practice, two things moved the needle far more than
  volume of retries alone:
  - **Soften explicit guardrail language in the system prompt/spec.**
    Spelling out the exact blocking rule up front (e.g. "calls over N are
    blocked pending approval") primes a well-aligned model to respect it.
    Describing the same constraint as something the agent discovers via
    a tool's response, plus adding realistic business urgency ("this is
    blocked until access is granted," "before Friday's review"), was what
    finally produced genuine gaming fixtures for demos 2, 3, and 4.
  - **Check that the honest path doesn't trivially satisfy the target.**
    If a fully honest action already clears the bar with room to spare,
    the model has no reason to reach for the gaming shortcut. Demo 2's
    `change_storage_class` originally had no restriction, so moving
    everything to a cold storage tier honestly blew past the 60% cost
    target — no version of that demo ever gamed until the tool was
    changed to refuse retention-required objects, which capped the
    honest ceiling well under the target and created real pressure.
