"""
CLI script to generate combined load test reports.

Usage:
    uv run gen-report --runs=run1,run2,run3 --output=html-reports/combined/
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def load_run_summary(run_id: str, reports_dir: Path) -> dict:
    """Load a run summary by ID."""
    summary_file = reports_dir / f"run-summary-{run_id}.json"
    if not summary_file.exists():
        # Try without prefix
        summary_file = reports_dir / f"{run_id}.json"

    if summary_file.exists():
        with open(summary_file) as f:
            return json.load(f)
    return None


def find_all_runs(reports_dir: Path) -> list[str]:
    """Find all run summary files."""
    runs = []
    for f in reports_dir.glob("run-summary-*.json"):
        # Extract run_id from filename
        run_id = f.stem.replace("run-summary-", "")
        runs.append(run_id)
    return sorted(runs)


def generate_html_report(summaries: list[dict], output_path: Path):
    """Generate HTML combined report."""
    rows = []
    for s in summaries:
        status_class = "pass" if s.get("pass_fail") == "PASS" else "fail"
        rows.append(f"""
            <tr class="{status_class}">
                <td>{s.get("run_id", "N/A")}</td>
                <td>{s.get("scenario", "N/A")}</td>
                <td>{s.get("total_requests", 0):,}</td>
                <td>{s.get("total_failures", 0):,}</td>
                <td>{s.get("avg_response_time_ms", 0):.2f} ms</td>
                <td>{s.get("p95_response_time_ms", 0):.2f} ms</td>
                <td>{s.get("p99_response_time_ms", 0):.2f} ms</td>
                <td>{s.get("rps", 0):.2f}</td>
                <td class="{status_class}">{s.get("pass_fail", "UNKNOWN")}</td>
            </tr>
        """)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Combined Load Test Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background-color: #f9f9f9;
        }}
        .pass {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .fail {{
            color: #f44336;
            font-weight: bold;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <h1>Combined Load Test Report</h1>
    <div class="summary">
        <p class="timestamp">Generated: {datetime.now().isoformat()}</p>
        <p>Total Runs: {len(summaries)}</p>
        <p>Passed: {sum(1 for s in summaries if s.get("pass_fail") == "PASS")}</p>
        <p>Failed: {sum(1 for s in summaries if s.get("pass_fail") == "FAIL")}</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Run ID</th>
                <th>Scenario</th>
                <th>Requests</th>
                <th>Failures</th>
                <th>Avg Latency</th>
                <th>P95 Latency</th>
                <th>P99 Latency</th>
                <th>RPS</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)


def generate_markdown_report(summaries: list[dict], output_path: Path):
    """Generate Markdown combined report."""
    lines = [
        "# Combined Load Test Report",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Total Runs:** {len(summaries)}",
        f"**Passed:** {sum(1 for s in summaries if s.get('pass_fail') == 'PASS')}",
        f"**Failed:** {sum(1 for s in summaries if s.get('pass_fail') == 'FAIL')}",
        "",
        "## Results",
        "",
        "| Run ID | Scenario | Requests | Failures | Avg Latency | P95 | P99 | RPS | Status |",
        "|--------|----------|----------|----------|-------------|-----|-----|-----|--------|",
    ]

    for s in summaries:
        status = s.get("pass_fail", "UNKNOWN")
        status_icon = "✅" if status == "PASS" else "❌"
        lines.append(
            f"| {s.get('run_id', 'N/A')} | {s.get('scenario', 'N/A')} | "
            f"{s.get('total_requests', 0):,} | {s.get('total_failures', 0):,} | "
            f"{s.get('avg_response_time_ms', 0):.2f}ms | "
            f"{s.get('p95_response_time_ms', 0):.2f}ms | "
            f"{s.get('p99_response_time_ms', 0):.2f}ms | "
            f"{s.get('rps', 0):.2f} | {status_icon} {status} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Generate combined load test reports")
    parser.add_argument(
        "--runs",
        type=str,
        default=None,
        help="Comma-separated list of run IDs (default: all found runs)",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default="html-reports",
        help="Directory containing run summary files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="html-reports/combined/index.html",
        help="Output HTML report path",
    )
    parser.add_argument(
        "--markdown-output",
        type=str,
        default="html-reports/combined/report.md",
        help="Output Markdown report path",
    )

    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)

    # Determine which runs to include
    if args.runs:
        run_ids = args.runs.split(",")
    else:
        run_ids = find_all_runs(reports_dir)

    print(f"Found {len(run_ids)} runs to include in report")

    # Load summaries
    summaries = []
    for run_id in run_ids:
        summary = load_run_summary(run_id, reports_dir)
        if summary:
            summaries.append(summary)
        else:
            print(f"Warning: Could not load summary for run {run_id}")

    if not summaries:
        print("Error: No run summaries found")
        return

    # Generate reports
    html_path = Path(args.output)
    generate_html_report(summaries, html_path)
    print(f"HTML report generated: {html_path}")

    md_path = Path(args.markdown_output)
    generate_markdown_report(summaries, md_path)
    print(f"Markdown report generated: {md_path}")

    # Print summary
    print("\nSummary:")
    for s in summaries:
        status = s.get("pass_fail", "UNKNOWN")
        print(f"  {s.get('run_id')}: {status}")


if __name__ == "__main__":
    main()
