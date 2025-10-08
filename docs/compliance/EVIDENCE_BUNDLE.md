# Compliance Evidence Bundle

## Overview

The Compliance Evidence Bundle is an automated artifact generated weekly by our CI/CD pipeline. It provides a
snapshot of key compliance and security-related documentation, configurations, and dependencies. This bundle is
designed to streamline audits and provide a consistent, verifiable record of our compliance posture at a specific
point in time.

By automating the collection of this evidence, we ensure that the process is repeatable, consistent, and free from
manual error. Each bundle is versioned with the Git commit hash and timestamp, providing a clear audit trail.

## Bundle Contents

Each evidence bundle is a ZIP file containing the following artifacts:

| Path | Description |
| --- | --- |
| `docs/**` | All documentation, including security policies, procedures, and architectural diagrams. |
| `.github/workflows/*.yml` | The complete, unmodified definitions of all CI/CD workflows. |
| `requirements.txt` | The list of all Python application dependencies. |
| `poetry.lock` | The deterministic lock file for Python dependencies (if present). |
| `artifacts/runtime/pip-freeze.txt` | A snapshot of the exact versions of all installed Python packages. |
| `artifacts/version.txt` | The Git commit hash and date, providing a precise version for artifacts. |

## How to Download

The evidence bundle can be downloaded directly from the GitHub Actions workflow runs.

1. **Navigate to the Actions tab** in the GitHub repository.
2. **Select the "Evidence Bundle" workflow** from the list on the left.
3. **Choose a recent workflow run.** The bundles are generated weekly, on tag pushes, or by manual dispatch.
4. **Scroll down to the "Artifacts" section** at the bottom of the run summary.
5. **Click on the `evidence-bundle-<run_number>` artifact** to download the ZIP file.

## Security and Integrity

The `build_evidence_bundle.py` script is designed to exclude sensitive information:

- It **does not** include any files matching `.env` or `*secret*` patterns.
- It **explicitly excludes** `**/node_modules/**` and other temporary build directories.
- The bundle is uploaded directly to GitHub Actions artifacts, which are secured and only accessible to users
  with appropriate repository permissions.

