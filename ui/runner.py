import json
import time


def load_fixture(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def replay_steps(steps: list[dict], speedup: float = 5.0):
    """Yield steps with sleeps proportional to their recorded timestamps.

    A step recorded 1s after the previous one waits 1/speedup seconds here,
    so a multi-minute agent run stays watchable without losing the relative
    pacing of the original run.
    """
    prev_timestamp = 0.0
    for step in steps:
        timestamp = step.get("timestamp", prev_timestamp)
        delta = max(timestamp - prev_timestamp, 0.0)
        time.sleep(delta / speedup)
        yield step
        prev_timestamp = timestamp
