#!/usr/bin/env python3
"""
Isolated Test Repository Manager for Cage Platform

This script manages isolated test repositories in .scratchpad/ directory
and ensures CrewAI agents only work within their designated repositories.
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class IsolatedTestManager:
    def __init__(self, base_dir=".scratchpad"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def create_test_repo(self, test_name, description=""):
        """Create a new isolated test repository."""
        repo_path = self.base_dir / test_name

        if repo_path.exists():
            print(f"❌ Test repository '{test_name}' already exists")
            return None

        try:
            # Create directory
            repo_path.mkdir(parents=True)

            # Initialize git repository
            subprocess.run(["git", "init"], cwd=repo_path, check=True)

            # Create initial README
            readme_content = f"""# {test_name}

{description}

Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is an isolated test repository for Cage platform testing.
All operations are restricted to this directory only.
"""

            with open(repo_path / "README.md", "w") as f:
                f.write(readme_content)

            # Initial commit
            subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Initial commit for {test_name}"],
                cwd=repo_path,
                check=True,
            )

            print(f"✅ Created isolated test repository: {repo_path}")
            return str(repo_path.absolute())

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create test repository: {e}")
            shutil.rmtree(repo_path, ignore_errors=True)
            return None

    def list_test_repos(self):
        """List all test repositories."""
        repos = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and (item / ".git").exists():
                repos.append(
                    {
                        "name": item.name,
                        "path": str(item.absolute()),
                        "created": datetime.fromtimestamp(
                            item.stat().st_ctime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
        return repos

    def start_cage_service(self, repo_path, port=8000):
        """Start Cage service with isolated repository."""
        repo_path = Path(repo_path).absolute()

        if not repo_path.exists():
            print(f"❌ Repository path does not exist: {repo_path}")
            return False

        if not (repo_path / ".git").exists():
            print(f"❌ Not a Git repository: {repo_path}")
            return False

        print(f"🚀 Starting Cage service with isolated repository: {repo_path}")
        print(f"   Port: {port}")
        print("   Press Ctrl+C to stop the service")

        # Set environment variables
        env = os.environ.copy()
        env["REPO_PATH"] = str(repo_path)
        env["POD_TOKEN"] = "EQmjYQJJRRF4TQo3QgXn8CyQMAYrEhbz"
        env["POD_ID"] = f"isolated-{repo_path.name}"

        try:
            # Start the service
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "src.apps.crew_api.main:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(port),
                ],
                cwd=Path(__file__).parent,
                env=env,
            )
        except KeyboardInterrupt:
            print("\n🛑 Cage service stopped")
        except Exception as e:
            print(f"❌ Failed to start Cage service: {e}")
            return False

        return True

    def cleanup_test_repo(self, test_name):
        """Remove a test repository."""
        repo_path = self.base_dir / test_name

        if not repo_path.exists():
            print(f"❌ Test repository '{test_name}' does not exist")
            return False

        try:
            shutil.rmtree(repo_path)
            print(f"✅ Removed test repository: {test_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to remove test repository: {e}")
            return False

    def cleanup_all(self):
        """Remove all test repositories."""
        repos = self.list_test_repos()
        if not repos:
            print("No test repositories to clean up")
            return True

        print(f"🧹 Cleaning up {len(repos)} test repositories...")
        for repo in repos:
            self.cleanup_test_repo(repo["name"])

        print("✅ Cleanup completed")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Manage isolated test repositories for Cage platform"
    )
    parser.add_argument(
        "command",
        choices=["create", "list", "start", "cleanup", "cleanup-all"],
        help="Command to execute",
    )
    parser.add_argument("--name", help="Test repository name")
    parser.add_argument("--description", help="Test repository description")
    parser.add_argument("--port", type=int, default=8000, help="Port for Cage service")

    args = parser.parse_args()

    manager = IsolatedTestManager()

    if args.command == "create":
        if not args.name:
            print("❌ --name is required for create command")
            sys.exit(1)

        repo_path = manager.create_test_repo(args.name, args.description or "")
        if repo_path:
            print(f"\n📁 Test repository created at: {repo_path}")
            print(
                f"🚀 To start Cage service: python manage-isolated-tests.py start --name {args.name}"
            )

    elif args.command == "list":
        repos = manager.list_test_repos()
        if not repos:
            print("No test repositories found")
        else:
            print(f"📁 Found {len(repos)} test repositories:")
            for repo in repos:
                print(f"   • {repo['name']} (created: {repo['created']})")
                print(f"     Path: {repo['path']}")

    elif args.command == "start":
        if not args.name:
            print("❌ --name is required for start command")
            sys.exit(1)

        repo_path = manager.base_dir / args.name
        if not repo_path.exists():
            print(f"❌ Test repository '{args.name}' does not exist")
            print(
                "Create it first with: python manage-isolated-tests.py create --name <name>"
            )
            sys.exit(1)

        manager.start_cage_service(repo_path, args.port)

    elif args.command == "cleanup":
        if not args.name:
            print("❌ --name is required for cleanup command")
            sys.exit(1)

        manager.cleanup_test_repo(args.name)

    elif args.command == "cleanup-all":
        if (
            input(
                "⚠️  This will remove ALL test repositories. Continue? (y/N): "
            ).lower()
            == "y"
        ):
            manager.cleanup_all()
        else:
            print("Operation cancelled")


if __name__ == "__main__":
    main()
