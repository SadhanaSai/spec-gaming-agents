import json
import time


def load_fixture(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def replay_steps(
    steps: list[dict],
    speedup: float = 2.0,
    min_delay: float = 0.4,
    max_delay: float = 3.0,
):
    """Yield steps with sleeps proportional to their recorded timestamps.

    A step recorded 1s after the previous one waits 1/speedup seconds here,
    so the replay keeps a sense of which steps were close together and which
    weren't. min_delay floors the wait so steps recorded milliseconds apart
    (common in these fixtures) don't flash by unreadably; max_delay caps it
    so a real multi-minute gap between steps doesn't stall a live replay.
    """
    prev_timestamp = 0.0
    for step in steps:
        timestamp = step.get("timestamp", prev_timestamp)
        delta = max(timestamp - prev_timestamp, 0.0)
        time.sleep(min(max(delta / speedup, min_delay), max_delay))
        yield step
        prev_timestamp = timestamp
