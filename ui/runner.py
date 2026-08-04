import json
import time


def load_fixture(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def replay_steps(steps: list[dict]):
    for step in steps:
        time.sleep(1)
        yield step
