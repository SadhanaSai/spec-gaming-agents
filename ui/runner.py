import json
import os
import time


def get_mode() -> str:
    mode = os.getenv("DEMO_MODE")
    if mode not in ("live", "replay"):
        raise ValueError(
            "Set DEMO_MODE=live or DEMO_MODE=replay before launching this dashboard."
        )
    return mode


def load_fixture(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def replay_steps(steps: list[dict]):
    for step in steps:
        time.sleep(1)
        yield step
