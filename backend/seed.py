"""Command-line script to initialize BankSim database schema and demo accounts.

Usage:
    python -m backend.seed
"""

import sys
from backend.database import init_db, seed_demo_data


def main() -> None:
    print("=" * 60)
    print("BankSim: Initializing Database Schema & Demo Accounts")
    print("=" * 60)

    try:
        init_db()
        results = seed_demo_data()

        if results["users_created"]:
            print(f"[+] Users created ({len(results['users_created'])}): {', '.join(results['users_created'])}")
        if results["users_preserved"]:
            print(f"[*] Users preserved ({len(results['users_preserved'])}): {', '.join(results['users_preserved'])}")

        if results["accounts_created"]:
            print(f"[+] Accounts created ({len(results['accounts_created'])}): {', '.join(results['accounts_created'])}")
        if results["accounts_preserved"]:
            print(f"[*] Accounts preserved ({len(results['accounts_preserved'])}): {', '.join(results['accounts_preserved'])}")

        print("\n[OK] Database schema initialized and demo accounts ready.")
    except Exception as exc:
        print(f"\n[!] Error during database seeding: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
