"""CLI interface for BP Extract."""

import logging
import sys

from config import get_config
from core import scan_backups, tail_log
from setup_wizard import run_setup

YES_CHOICES = {"y", "yes"}
NO_CHOICES = {"n", "no"}


def main():
    """Main CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Initialize config and run setup if needed
    config = get_config()
    run_setup()

    # Get configuration
    log_file = config.get("log_file")
    data_file = config.get("data_file")
    backup_dir = config.get("backup_dir")
    poll_interval = config.get("poll_interval", 0.5)
    wait_interval = config.get("wait_interval", 1.0)

    # Validate paths
    is_valid, error_msg = config.validate_paths()
    if not is_valid:
        print(f"Error: {error_msg}")
        sys.exit(1)

    known_blueprints = None

    # Scan backups if requested
    while True:
        choice = (
            input("Would you like to scan older log backups for blueprints? (y/n): ")
            .strip()
            .lower()
        )
        if choice in YES_CHOICES:
            known_blueprints = scan_backups(backup_dir, data_file)
            break
        elif choice in NO_CHOICES:
            break
        else:
            print("Please answer 'y' or 'n'.")

    try:
        tail_log(
            log_file,
            data_file,
            poll_interval=poll_interval,
            wait_interval=wait_interval,
            known_blueprints=known_blueprints,
        )
    except KeyboardInterrupt:
        print("\nStopping blueprint logger.")


if __name__ == "__main__":
    main()
