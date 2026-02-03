"""
Reporting utilities for load test results.

Generates HTML reports, CSV exports, and run summaries.
"""

import csv
import html
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunSummary:
    """Summary of a load test run."""

    run_id: str
    start_time: datetime
    end_time: datetime | None = None
    services_tested: list[str] = None
    scenario: str = "baseline"
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    rps: float = 0.0
    threshold_violations: list[dict] = None
    pass_fail: str = "UNKNOWN"

    def __post_init__(self):
        if self.services_tested is None:
            self.services_tested = []
        if self.threshold_violations is None:
            self.threshold_violations = []


class ReportGenerator:
    """
    Generates reports from load test results.

    Usage:
        generator = ReportGenerator()
        generator.generate_final_report(environment)
    """

    def __init__(self, output_dir: str = "html-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.run_summaries: list[RunSummary] = []

    def generate_final_report(self, environment):
        """Generate final report when test stops."""
        # Get stats from Locust environment
        stats = environment.stats

        # Calculate percentiles
        response_times = []
        for entry in stats.entries.values():
            response_times.extend([entry.avg_response_time] * entry.num_requests)

        if response_times:
            response_times.sort()
            n = len(response_times)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            p95 = response_times[p95_idx] if n > p95_idx else 0
            p99 = response_times[p99_idx] if n > p99_idx else 0
            avg = sum(response_times) / n
        else:
            p95 = p99 = avg = 0

        # Determine pass/fail
        fail_ratio = stats.total.fail_ratio
        pass_fail = "PASS" if fail_ratio < 0.01 else "FAIL"

        summary = RunSummary(
            run_id=datetime.now().strftime("%Y%m%d-%H%M%S"),
            start_time=datetime.fromtimestamp(stats.start_time or datetime.now().timestamp()),
            end_time=datetime.now(),
            total_requests=stats.total.num_requests,
            total_failures=stats.total.num_failures,
            avg_response_time_ms=avg,
            p95_response_time_ms=p95,
            p99_response_time_ms=p99,
            rps=stats.total.current_rps,
            pass_fail=pass_fail,
        )

        self.run_summaries.append(summary)

        # Generate JSON summary
        self._write_json_summary(summary)

        # Generate CSV
        self._write_csv_summary(summary)

        print(f"Report generated: {self.output_dir}/run-summary-{summary.run_id}.json")
        print(f"Pass/Fail: {pass_fail}")

    def _write_json_summary(self, summary: RunSummary):
        """Write JSON summary file."""
        output_file = self.output_dir / f"run-summary-{summary.run_id}.json"

        data = asdict(summary)
        # Convert datetime objects to strings
        data["start_time"] = summary.start_time.isoformat()
        data["end_time"] = summary.end_time.isoformat() if summary.end_time else None

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

    def _write_csv_summary(self, summary: RunSummary):
        """Write CSV summary file."""
        output_file = self.output_dir / f"run-summary-{summary.run_id}.csv"

        with open(output_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Run ID", summary.run_id])
            writer.writerow(["Start Time", summary.start_time.isoformat()])
            writer.writerow(
                ["End Time", summary.end_time.isoformat() if summary.end_time else "N/A"]
            )
            writer.writerow(["Total Requests", summary.total_requests])
            writer.writerow(["Total Failures", summary.total_failures])
            writer.writerow(["Avg Response Time (ms)", f"{summary.avg_response_time_ms:.2f}"])
            writer.writerow(["P95 Response Time (ms)", f"{summary.p95_response_time_ms:.2f}"])
            writer.writerow(["P99 Response Time (ms)", f"{summary.p99_response_time_ms:.2f}"])
            writer.writerow(["RPS", f"{summary.rps:.2f}"])
            writer.writerow(["Pass/Fail", summary.pass_fail])

    def generate_combined_report(self, run_ids: list[str]) -> Path:
        """Generate a combined report from multiple runs."""
        output_file = self.output_dir / "combined" / "index.html"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Load all summaries
        summaries = []
        for run_id in run_ids:
            summary_file = self.output_dir / f"run-summary-{run_id}.json"
            if summary_file.exists():
                with open(summary_file) as f:
                    summaries.append(json.load(f))

        # Generate HTML
        html_content = self._generate_html_report(summaries)

        with open(output_file, "w") as f:
            f.write(html_content)

        return output_file

    def _generate_html_report(self, summaries: list[dict]) -> str:
        """Generate HTML report content."""
        rows = []
        for s in summaries:
            row_class = "pass" if s.get("pass_fail") == "PASS" else "fail"
            rows.append(f"""
                <tr class="{row_class}">
                    <td>{html.escape(s.get("run_id", "N/A"))}</td>
                    <td>{html.escape(s.get("scenario", "N/A"))}</td>
                    <td>{s.get("total_requests", 0)}</td>
                    <td>{s.get("total_failures", 0)}</td>
                    <td>{s.get("p95_response_time_ms", 0):.2f} ms</td>
                    <td>{s.get("p99_response_time_ms", 0):.2f} ms</td>
                    <td>{s.get("rps", 0):.2f}</td>
                    <td class="{row_class}">{html.escape(s.get("pass_fail", "UNKNOWN"))}</td>
                </tr>
            """)

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .pass {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        h1 {{ color: #333; }}
        .summary {{ margin-bottom: 20px; padding: 10px; background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <h1>Load Test Report</h1>
    <div class="summary">
        <p>Generated: {datetime.now().isoformat()}</p>
        <p>Total Runs: {len(summaries)}</p>
    </div>
    <table>
        <tr>
            <th>Run ID</th>
            <th>Scenario</th>
            <th>Requests</th>
            <th>Failures</th>
            <th>P95 Latency</th>
            <th>P99 Latency</th>
            <th>RPS</th>
            <th>Status</th>
        </tr>
        {"".join(rows)}
    </table>
</body>
</html>
        """

    def export_to_json(self, data: dict, filename: str):
        """Export arbitrary data to JSON."""
        output_file = self.output_dir / filename
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        return output_file


# Global singleton instance
report_generator = ReportGenerator()
