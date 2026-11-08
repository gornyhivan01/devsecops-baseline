# Security Baseline integration

Copy `.github/workflows/security.yml` and `security/release_gate.py` into the repository. Keep the existing CI workflow unchanged. This is an initial implementation template, **not yet verified against a full GitHub Actions run**.

## Behavior
- Runs on PRs, pushes to main, version tags, and manual dispatch.
- Exports locked runtime dependencies using `uv export` and audits them.
- Produces SAST, SCA, IaC, container reports and two SBOM formats.
- Fails the scan job for Medium/High Bandit, Semgrep ERROR, any SCA CVE, any Checkov finding, or High/Critical Trivy finding.
- Gitleaks fails its own step if it detects secrets.
- Tag-triggered release exports a versioned Docker image only after the scan job passes.

## Required before claiming completion
1. Run the workflow and resolve action/tool compatibility or existing findings; some rules may need explicit, time-limited exception management.
2. Add an exception register with owner, justification, expiration, and a reviewed suppression mechanism. The current gate deliberately has **no bypass**.
3. Require `scan` and the existing CI jobs as GitHub branch ruleset checks; require PR review.
4. Restrict repository access and artifact retention. Do not use actual secrets or personal data in demonstrations.
5. Demonstrate: synthetic secret in a temporary PR, vulnerable test dependency in a temporary PR, a SAST issue in a temporary PR, fixes, green reruns, SBOM, container report and image artifact.
6. Add runtime deployment evidence: read-only root filesystem, cap-drop, no-new-privileges and a reproducible Compose launch. Verify app writes before enforcing read-only.
7. Build a threat model, risk register, traceability matrix and manual security report for the broader SMI deliverables.

## Caveats
- Gitleaks GitHub Action licensing and private repository behavior should be checked for your account; use a CLI alternative if required.
- Pin third-party actions to reviewed commit SHA for a production-quality supply chain.
- A scanner command using `|| true` is used only to preserve JSON evidence; the gate checks findings, but scanner infrastructure failures should also be explicitly handled before final submission.
- The image is exported as an artifact, not published to a registry. Publishing can be added behind a protected release environment.
