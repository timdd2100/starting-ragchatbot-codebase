#!/usr/bin/env python3
"""Development quality assurance script for running code quality checks."""

import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        print(f"✅ {description} passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def main():
    """Run all quality checks."""
    print("🚀 Running code quality checks...")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    subprocess.run(["cd", str(project_root)], shell=True)
    
    checks = [
        (["uv", "run", "black", "--check", "backend/", "main.py"], "Black formatting check"),
        (["uv", "run", "isort", "--check-only", "--diff", "backend/", "main.py"], "Import sorting check"),
        (["uv", "run", "flake8", "backend/", "main.py"], "Flake8 linting"),
        (["uv", "run", "pytest", "backend/tests/"], "Running tests"),
    ]
    
    failed_checks = []
    
    for command, description in checks:
        if not run_command(command, description):
            failed_checks.append(description)
    
    if failed_checks:
        print(f"\n❌ {len(failed_checks)} check(s) failed:")
        for check in failed_checks:
            print(f"  - {check}")
        sys.exit(1)
    else:
        print("\n🎉 All quality checks passed!")


if __name__ == "__main__":
    main()