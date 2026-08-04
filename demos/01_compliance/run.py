import argparse
import json
import os
import sys
import time
import traceback

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

sys.path.insert(0, os.path.dirname(__file__))

from agent import build_react_agent, run_agent, load_spec, table, s3, BUCKET_NAME
import verify

DEMO_DIR = os.path.dirname(__file__)


def capture_state():
    findings = table.scan().get("Items", [])
    try:
        public_access_block = s3.get_public_access_block(Bucket=BUCKET_NAME)["PublicAccessBlockConfiguration"]
    except s3.exceptions.ClientError:
        public_access_block = None
    return {"findings": findings, "bucket_public_access_block": public_access_block}


def write_json(filename, data):
    path = os.path.join(DEMO_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def run_live(record=False, output_path=None, label=None):
    spec_text = load_spec()
    state_before = capture_state()
    write_json("state_before.json", state_before)

    agent = build_react_agent()
    messages = [HumanMessage(content=spec_text)]

    steps = []
    pending_calls = {}
    seen = 0
    start = time.monotonic()

    try:
        for state in run_agent(agent, messages):
            new_messages = state["messages"][seen:]
            seen = len(state["messages"])
            messages = state["messages"]
            elapsed = round(time.monotonic() - start, 1)

            for msg in new_messages:
                if isinstance(msg, AIMessage):
                    if msg.tool_calls:
                        for call in msg.tool_calls:
                            pending_calls[call["id"]] = {
                                "timestamp": elapsed,
                                "tool": call["name"],
                                "input": call["args"],
                            }
                    elif msg.content:
                        steps.append({"timestamp": elapsed, "type": "reasoning", "content": msg.content})
                elif isinstance(msg, ToolMessage):
                    call = pending_calls.pop(msg.tool_call_id, None)
                    if call is not None:
                        steps.append({
                            "timestamp": call["timestamp"],
                            "type": "tool_call",
                            "tool": call["tool"],
                            "input": call["input"],
                            "output": msg.content,
                        })
    except Exception as e:
        print(f"Agent run did not complete cleanly: {type(e).__name__}: {e}")
        traceback.print_exc()

    transcript = [m.model_dump() for m in messages]
    write_json("run_log.json", transcript)

    state_after = capture_state()
    write_json("state_after.json", state_after)

    intent = verify.load_json("intent.json")
    report = verify.build_divergence_report(intent, state_before, state_after, steps)
    write_json("divergence_report.json", report)

    if record:
        fixture = {
            "demo": "01_compliance",
            "mode": label,
            "spec": spec_text,
            "steps": steps,
            "state_before": state_before,
            "state_after": state_after,
            "goal_check": report["goal_check"],
            "audit_log": report["audit_log"],
            "divergence": report["divergence"],
        }
        with open(output_path, "w") as f:
            json.dump(fixture, f, indent=2)

    return report


def run_replay(fixture_path):
    with open(fixture_path) as f:
        fixture = json.load(f)

    print(f"--- Replaying {fixture['demo']} ({fixture['mode']}) ---")
    print(f"Spec: {fixture['spec']}\n")

    for step in fixture["steps"]:
        time.sleep(1)
        if step["type"] == "reasoning":
            print(f"[{step['timestamp']}s] REASONING: {step['content']}")
        elif step["type"] == "tool_call":
            print(f"[{step['timestamp']}s] TOOL CALL: {step['tool']}({step['input']}) -> {step['output']}")

    print("\n--- Final state ---")
    print(json.dumps(fixture["goal_check"], indent=2))
    print(json.dumps(fixture["audit_log"], indent=2))
    print(json.dumps(fixture["divergence"], indent=2))

    return fixture


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["live", "record", "replay"], required=True)
    parser.add_argument("--output", help="Fixture output path (record mode)")
    parser.add_argument("--fixture", help="Fixture input path (replay mode)")
    parser.add_argument("--label", choices=["gaming", "correct"], help="Fixture mode label (record mode)")
    args = parser.parse_args()

    if args.mode == "live":
        report = run_live()
        print(json.dumps(report, indent=2))
    elif args.mode == "record":
        if not args.output or not args.label:
            parser.error("--mode record requires --output and --label")
        run_live(record=True, output_path=args.output, label=args.label)
    elif args.mode == "replay":
        if not args.fixture:
            parser.error("--mode replay requires --fixture")
        run_replay(args.fixture)


if __name__ == "__main__":
    main()
