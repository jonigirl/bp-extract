"""First-run setup wizard for BP Extract."""

import os

from config import Config, get_config


def welcome():
    """Show welcome message."""
    print("\n" + "=" * 70)
    print("  BP Extract - First Run Setup")
    print("=" * 70)
    print("\nWelcome! Let's configure BP Extract for your system.\n")


def confirm_paths(config: Config) -> bool:
    """Confirm or update detected paths."""
    print("Auto-detected paths:")
    print(f"  Game Log:     {config.get('log_file')}")
    print(f"  Backup Dir:   {config.get('backup_dir')}")
    print(f"  Data File:    {config.get('data_file')}")
    print()

    # Validate paths
    is_valid, error_msg = config.validate_paths()
    if not is_valid:
        print(f"[WARNING] {error_msg}\n")

    while True:
        choice = input("Do you want to use these paths? (y/n/custom): ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        elif choice == "custom":
            return custom_paths(config)
        else:
            print("Please enter 'y', 'n', or 'custom'.\n")


def custom_paths(config: Config) -> bool:
    """Allow user to enter custom paths."""
    print("\nEnter custom paths (or press Enter to skip a field):\n")

    log_file = input(f"Game Log file [{config.get('log_file')}]: ").strip()
    if log_file:
        config.set("log_file", log_file)

    backup_dir = input(f"Backup directory [{config.get('backup_dir')}]: ").strip()
    if backup_dir:
        config.set("backup_dir", backup_dir)

    data_file = input(f"Data file [{config.get('data_file')}]: ").strip()
    if data_file:
        config.set("data_file", data_file)

    print()
    return confirm_paths(config)


def migrate_csv():
    """Offer to migrate existing CSV data."""
    csv_file = "blueprints.csv"

    if not os.path.exists(csv_file):
        return

    print(f"\n[FOUND] Existing {csv_file}")
    choice = (
        input("Would you like to migrate existing blueprints to JSON? (y/n): ")
        .strip()
        .lower()
    )

    if choice in ("y", "yes"):
        from core import migrate_csv_to_json

        config = get_config()
        data_file = config.get("data_file")
        if migrate_csv_to_json(csv_file, data_file):
            # Backup original CSV
            backup_name = f"{csv_file}.backup"
            os.rename(csv_file, backup_name)
            print(f"Original CSV saved as: {backup_name}\n")
        print()


def summary(config: Config):
    """Show setup summary."""
    print("=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print(f"\n[OK] Game Log:     {config.get('log_file')}")
    print(f"[OK] Backup Dir:   {config.get('backup_dir')}")
    print(f"[OK] Data File:    {config.get('data_file')}")
    print(f"[OK] Platform:     {config.get('platform')}")
    print("\nBP Extract is ready to use!")
    print("Open http://localhost:5000 in your browser to start.\n")


def run_setup():
    """Run the complete setup wizard."""
    config = get_config()

    if not config.is_first_run():
        return False

    welcome()

    # Show/confirm paths
    while not confirm_paths(config):
        pass

    # Offer CSV migration
    migrate_csv()

    # Save configuration
    config.save()

    # Show summary
    summary(config)

    return True


if __name__ == "__main__":
    run_setup()
