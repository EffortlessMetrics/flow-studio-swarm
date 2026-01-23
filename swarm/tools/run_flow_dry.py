#!/usr/bin/env python3
"""Simple dry-run checker for swarm flows.

Parses `swarm/flows/flow-*.md` Steps tables, extracts backticked artifact filenames
from the Responsibility column, and reports whether those artifacts exist.

Usage: python swarm/tools/run_flow_dry.py flow-signal flow-plan ...
"""

import re
from pathlib import Path

FLOW_DIR = Path(__file__).resolve().parents[1] / "flows"
OUT_DIR = Path("swarm/examples/health-check/reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_flow(flow_path: Path):
    text = flow_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_table = False
    rows = []
    for line in lines:
        if not in_table:
            if line.strip().startswith("| Step") and "Node" in line and "Type" in line:
                in_table = True
                continue
        else:
            if not line.strip().startswith("|"):
                break
            # simple split on |, expect at least 4 cols
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 5 and cols[1].lower() != "step":
                # cols: ['', 'Step', 'Node', 'Type', 'Responsibility', ''] maybe
                rows.append(cols)
    return rows


def extract_artifacts(responsibility: str):
    # find backticked filenames or simple filenames mentioned
    files = re.findall(r"`([^`]+)`", responsibility)
    return files


def run_flow(flow_name: str):
    flow_file = FLOW_DIR / f"{flow_name}.md"
    if not flow_file.exists():
        return f"Flow file {flow_file} missing", False
    rows = parse_flow(flow_file)
    report_lines = [f"Flow: {flow_name}", f"File: {flow_file}", f"Steps parsed: {len(rows)}", ""]
    missing = []
    for cols in rows:
        # responsibility usually in column 4 (index 4)
        resp = cols[4] if len(cols) > 4 else ""
        artifacts = extract_artifacts(resp)
        if artifacts:
            report_lines.append(f"Step {cols[1]} artifacts:")
            for a in artifacts:
                # support glob patterns like tests/* or features/*.feature
                if "*" in a:
                    parent = Path(a).parent
                    pattern = a.split("/")[-1]
                    matches = list(parent.glob(pattern)) if parent.exists() else []
                    exists = len(matches) > 0
                else:
                    p = Path(a)
                    exists = p.exists()
                report_lines.append(f"  - {a}: {'OK' if exists else 'MISSING'}")
                if not exists:
                    missing.append(a)
    ok = len(missing) == 0
    report_path = OUT_DIR / f"{flow_name}-report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path, ok


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="run_flow_dry",
        description=(
            "Simple dry-run checker for swarm flows.\n\n"
            "Parses swarm/flows/flow-*.md Steps tables, extracts backticked artifact\n"
            "filenames from the Responsibility column, and reports whether those\n"
            "artifacts exist.\n\n"
            "Reports are written to swarm/examples/health-check/reports/"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "flows",
        nargs="+",
        metavar="FLOW",
        help="Flow names to check (e.g., flow-signal flow-plan)",
    )
    args = parser.parse_args()

    overall_ok = True
    for fn in args.flows:
        report, ok = run_flow(fn)
        if isinstance(report, str):
            print(report)
            overall_ok = False
            continue
        print(f"Wrote report: {report} — {'OK' if ok else 'MISSING artifacts'}")
        if not ok:
            overall_ok = False
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
