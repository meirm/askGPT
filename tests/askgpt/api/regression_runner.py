#!/usr/bin/env python3
"""
Regression test runner for API tests.

Loads test cases from regression_cases.json, executes them, and generates reports.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest


def load_regression_cases() -> Dict[str, Any]:
    """Load regression test cases from JSON file."""
    cases_file = Path(__file__).parent / "regression_cases.json"
    if not cases_file.exists():
        print(f"Error: Regression cases file not found: {cases_file}")
        sys.exit(1)
    
    with open(cases_file, "r") as f:
        return json.load(f)


def run_regression_tests() -> Dict[str, Any]:
    """
    Run regression tests using pytest.
    
    Returns:
        Dictionary with test results
    """
    test_file = Path(__file__).parent / "test_regression.py"
    
    # Run pytest on regression tests
    exit_code = pytest.main([
        str(test_file),
        "-v",
        "-m", "regression",
        "--tb=short",
    ])
    
    return {
        "exit_code": exit_code,
        "success": exit_code == 0,
    }


def generate_report(results: Dict[str, Any], cases: Dict[str, Any]) -> str:
    """
    Generate HTML report from test results.
    
    Args:
        results: Test execution results
        cases: Regression test cases
        
    Returns:
        HTML report as string
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>askGPT API Regression Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .test-case {{ margin: 10px 0; padding: 10px; border-left: 3px solid #ccc; }}
    </style>
</head>
<body>
    <h1>askGPT API Regression Test Report</h1>
    <p><strong>Generated:</strong> {timestamp}</p>
    <p><strong>Status:</strong> <span class="{'success' if results['success'] else 'failure'}">
        {'PASSED' if results['success'] else 'FAILED'}
    </span></p>
    
    <h2>Test Cases</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Description</th>
        </tr>
"""
    
    for case in cases["test_cases"]:
        html += f"""
        <tr>
            <td>{case['id']}</td>
            <td>{case['name']}</td>
            <td>{case.get('description', '')}</td>
        </tr>
"""
    
    html += """
    </table>
    
    <h2>Performance Baselines</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Baseline (seconds)</th>
        </tr>
"""
    
    for metric, value in cases["performance_baselines"].items():
        html += f"""
        <tr>
            <td>{metric.replace('_', ' ').title()}</td>
            <td>{value}</td>
        </tr>
"""
    
    html += """
    </table>
</body>
</html>
"""
    
    return html


def main():
    """Main entry point for regression test runner."""
    print("=" * 60)
    print("askGPT API Regression Test Runner")
    print("=" * 60)
    
    # Load test cases
    print("\nLoading regression test cases...")
    cases = load_regression_cases()
    print(f"Loaded {len(cases['test_cases'])} test cases")
    
    # Run tests
    print("\nRunning regression tests...")
    start_time = time.time()
    results = run_regression_tests()
    execution_time = time.time() - start_time
    
    # Generate report
    print("\nGenerating report...")
    report_html = generate_report(results, cases)
    
    # Save report
    report_file = Path(__file__).parent / "regression_report.html"
    with open(report_file, "w") as f:
        f.write(report_html)
    
    print(f"\nReport saved to: {report_file}")
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Status: {'PASSED' if results['success'] else 'FAILED'}")
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()
