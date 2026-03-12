"""CLI utilities for DrapeStudio admin management.

Usage:
    python -m app.cli create-admin --email admin@drapestudiolk.com --password secret123
    python -m app.cli create-admin --email admin@drapestudiolk.com --password secret123 --name "Super Admin"
"""

import argparse
import sys


def create_admin(email: str, password: str, name: str = "") -> None:
    """Create or promote a user to admin with email + password auth."""
    # Import here to avoid loading the entire app just for --help
    from app.database import SessionLocal
    from app.services.admin_auth import AdminAuthService

    db = SessionLocal()
    try:
        user = AdminAuthService.create_admin_user(email, password, name, db)
        print(f"Admin user ready:")
        print(f"  ID:    {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Name:  {user.display_name}")
        print(f"  Role:  {user.role}")
        print(f"\nLogin at /admin/login with this email and password.")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="DrapeStudio CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-admin
    admin_parser = subparsers.add_parser("create-admin", help="Create or promote an admin user")
    admin_parser.add_argument("--email", required=True, help="Admin email address")
    admin_parser.add_argument("--password", required=True, help="Admin password")
    admin_parser.add_argument("--name", default="", help="Display name (optional)")

    args = parser.parse_args()

    if args.command == "create-admin":
        create_admin(args.email, args.password, args.name)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
