"""AI Harness Engineering — Main Entry Point

Usage:
    python core/main.py new "Build an e-commerce system"   # New project workflow
    python core/main.py iterate "Add user login feature"   # Iteration workflow
"""

import sys
from orchestrator import Orchestrator


def main():
    if len(sys.argv) < 2:
        print("Usage: python core/main.py <command> [args...]\n")
        print("Commands:")
        print("  new      <description>   Start a new project workflow")
        print("  iterate  <description>   Start an iteration workflow")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    orchestrator = Orchestrator()

    if command == "new":
        orchestrator.run_new_project(" ".join(args))
    elif command == "iterate":
        orchestrator.run_iteration(" ".join(args))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
