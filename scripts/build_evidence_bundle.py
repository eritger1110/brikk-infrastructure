#!/usr/bin/env python3
"""
Build Evidence Bundle

Gathers compliance evidence into a single ZIP artifact for auditing purposes.
"""

import os
import zipfile
import datetime
import subprocess
from pathlib import Path


def get_git_commit_info():
    """Get the current Git commit hash and date."""
    try:
        commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode("utf-8")
        commit_date = subprocess.check_output(["git", "show", "-s", "--format=%ci"]).strip().decode("utf-8")
        return commit_hash, commit_date
    except Exception as e:
        print(f"Warning: Could not get Git info: {e}")
        return "unknown", "unknown"


def get_pip_freeze():
    """Get the output of pip freeze."""
    try:
        return subprocess.check_output(["pip", "freeze"]).decode("utf-8")
    except Exception as e:
        print(f"Warning: Could not get pip freeze output: {e}")
        return ""


def main():
    """Main function to build the evidence bundle."""
    # Define paths
    root_dir = Path(__file__).parent.parent
    artifacts_dir = root_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    # Create version file
    commit_hash, commit_date = get_git_commit_info()
    (artifacts_dir / "version.txt").write_text(f"Commit: {commit_hash}\nDate: {commit_date}\n")
    
    # Create pip freeze file
    runtime_dir = artifacts_dir / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    (runtime_dir / "pip-freeze.txt").write_text(get_pip_freeze())
    
    # Create ZIP file
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    zip_filename = artifacts_dir / f"evidence-bundle-{timestamp}.zip"
    
    # Files and directories to include
    include_paths = [
        root_dir / "docs",
        root_dir / ".github/workflows",
        root_dir / "requirements.txt",
        root_dir / "poetry.lock",
        artifacts_dir / "version.txt",
        runtime_dir / "pip-freeze.txt"
    ]
    
    # Exclude patterns
    exclude_patterns = [".env", "*secret*", "**/node_modules/**"]
    
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in include_paths:
            if not path.exists():
                continue
            
            if path.is_file():
                zf.write(path, path.relative_to(root_dir))
            else:
                for file_path in path.rglob("*"):
                    if any(file_path.match(p) for p in exclude_patterns):
                        continue
                    zf.write(file_path, file_path.relative_to(root_dir))
    
    print(f"✅ Evidence bundle created: {zip_filename}")


if __name__ == "__main__":
    main()

