from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from AIteam.agent_chain.orchestrator import AutopilotOptions, Orchestrator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _orch() -> Orchestrator:
    return Orchestrator(repo_root=REPO_ROOT)


def cmd_list_agents(_: argparse.Namespace) -> int:
    orch = _orch()
    for agent_id, spec in orch.agents_config.agents.items():
        print(f"{agent_id}\t{spec.display_name}")
    return 0


def cmd_list_runs(_: argparse.Namespace) -> int:
    orch = _orch()
    runs = orch.list_runs()
    if not runs:
        print("(no runs yet)")
        return 0
    for r in runs:
        print(r.run_id)
    return 0


def cmd_create_run(args: argparse.Namespace) -> int:
    orch = _orch()
    paths = orch.create_run(objective=args.objective, created_by="cli")
    print(paths.run_id)
    return 0


def cmd_kickoff(args: argparse.Namespace) -> int:
    orch = _orch()
    paths = orch.get_run(args.run_id)
    orch.run_kickoff(paths)
    print("ok")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    orch = _orch()
    paths = orch.get_run(args.run_id)
    print(orch.run_status_markdown(paths))
    return 0


def cmd_message(args: argparse.Namespace) -> int:
    orch = _orch()
    paths = orch.get_run(args.run_id)
    resp = orch.call_agent(paths, agent_name=args.agent, message=args.text)
    print(resp)
    return 0


def cmd_autopilot(args: argparse.Namespace) -> int:
    orch = _orch()
    paths = orch.get_run(args.run_id)
    opts = AutopilotOptions(
        max_rounds=int(args.rounds),
        write_artifacts_to_repo=bool(args.write_artifacts_to_repo),
        auto_implement_code=bool(args.executor),
        apply_code_to_repo=bool(args.apply_to_repo),
    )
    state = orch.supervisor_autopilot(paths, user_request=args.text, options=opts)
    if args.print_state:
        print(json.dumps(state, indent=2))
    else:
        sup = state.get("supervisor") or {}
        print(sup.get("summary") or "(no summary)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="AIteam.chain_cli", description="Agent Chain CLI driver")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list-agents", help="List agents and display names")
    sp.set_defaults(func=cmd_list_agents)

    sp = sub.add_parser("list-runs", help="List existing run IDs")
    sp.set_defaults(func=cmd_list_runs)

    sp = sub.add_parser("create-run", help="Create a new run")
    sp.add_argument("objective", help="Run objective")
    sp.set_defaults(func=cmd_create_run)

    sp = sub.add_parser("kickoff", help="Run kickoff pipeline")
    sp.add_argument("--run-id", required=True)
    sp.set_defaults(func=cmd_kickoff)

    sp = sub.add_parser("status", help="Print run status markdown")
    sp.add_argument("--run-id", required=True)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("message", help="Send a message to an agent (agent id or display name)")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--agent", default="Supervisor")
    sp.add_argument("--text", required=True)
    sp.set_defaults(func=cmd_message)

    sp = sub.add_parser("autopilot", help="Run New UI Supervisor autopilot")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--text", required=True)
    sp.add_argument("--rounds", type=int, default=3)
    sp.add_argument("--write-artifacts-to-repo", action="store_true")
    sp.add_argument("--executor", action="store_true")
    sp.add_argument("--apply-to-repo", action="store_true")
    sp.add_argument("--print-state", action="store_true")
    sp.set_defaults(func=cmd_autopilot)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

