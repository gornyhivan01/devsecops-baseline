"""Fail closed security gate for JSON reports; no automatic exceptions."""

import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "reports")
failures = []


def load(name):
    p = root / name
    if not p.is_file():
        failures.append(f"Missing required report: {name}")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        failures.append(f"Invalid report {name}: {exc}")
        return None


bandit = load("bandit.json")
if isinstance(bandit, dict):
    for issue in bandit.get("results", []):
        if issue.get("issue_severity", "").upper() in ("HIGH", "MEDIUM"):
            failures.append(f"Bandit {issue.get('test_id')}: {issue.get('filename')}")

semgrep = load("semgrep.json")
if isinstance(semgrep, dict):
    if semgrep.get("errors"):
        failures.append("Semgrep scanner errors")
    for issue in semgrep.get("results", []):
        severity = issue.get("extra", {}).get("severity", "").upper()
        if severity in ("ERROR", "HIGH", "CRITICAL"):
            failures.append(f"Semgrep {issue.get('check_id')}: {issue.get('path')}")

sca = load("pip-audit.json")
if isinstance(sca, dict):
    for dep in sca.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            failures.append(f"SCA {dep.get('name')} {dep.get('version')}: {vuln.get('id')}")

checkov = load("checkov.json")
if isinstance(checkov, list):
    checkov = checkov[0] if checkov else {}
if isinstance(checkov, dict):
    for issue in checkov.get("results", {}).get("failed_checks", []):
        failures.append(f"IaC {issue.get('check_id')}: {issue.get('file_path')}")

trivy = load("trivy.json")
if isinstance(trivy, dict):
    for result in trivy.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            if vuln.get("Severity", "").upper() in ("CRITICAL", "HIGH"):
                failures.append(f"Container {vuln.get('VulnerabilityID')}: {vuln.get('PkgName')}")
        for issue in result.get("Misconfigurations") or []:
            if issue.get("Severity", "").upper() in ("CRITICAL", "HIGH"):
                failures.append(f"Container config {issue.get('ID')}")
        for issue in result.get("Secrets") or []:
            failures.append(f"Container secret {issue.get('RuleID')}")

for name in ("sbom.cdx.json", "sbom.spdx.json"):
    load(name)

if failures:
    print("SECURITY GATE: FAILED")
    for issue in failures:
        print(" -", issue)
    sys.exit(1)
print("SECURITY GATE: PASSED")
