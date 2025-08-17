#!/usr/bin/env python3
"""Development script for automatically formatting code."""

import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def main():
    """Format all code."""
    print("🎨 Formatting code...")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    subprocess.run(["cd", str(project_root)], shell=True)
    
    formatters = [
        (["uv", "run", "isort", "backend/", "main.py"], "Sorting imports"),
        (["uv", "run", "black", "backend/", "main.py"], "Formatting code with Black"),
    ]
    
    failed_formatters = []
    
    for command, description in formatters:
        if not run_command(command, description):
            failed_formatters.append(description)
    
    if failed_formatters:
        print(f"\n❌ {len(failed_formatters)} formatter(s) failed:")
        for formatter in failed_formatters:
            print(f"  - {formatter}")
        sys.exit(1)
    else:
        print("\n🎉 Code formatting completed successfully!")


if __name__ == "__main__":
    main()