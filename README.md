# BP Extract - Star Citizen Blueprint Tracker

A modern, cross-platform web application that monitors your Star Citizen game logs and tracks blueprint acquisitions in real-time.

## ✨ Features

- **🌐 Web Dashboard** - Beautiful, responsive interface accessible from any browser
- **📊 Live Statistics** - Real-time blueprint counts, today's acquisitions, and timestamps
- **🔍 Search & Filter** - Quickly find blueprints by name
- **📂 Backup Scanning** - Scan historical backup logs for missed blueprints
- **⏸️ Pause/Resume** - Control monitoring directly from the web interface
- **🔄 Auto-Refresh** - Automatically updates every 3 seconds (toggleable)
- **💾 JSON Storage** - Modern local data storage (human-readable, exportable)
- **🖥️ Cross-Platform** - Windows, macOS, and Linux support
- **⚙️ CLI Mode** - Traditional command-line operation still available
- **🚀 Auto-Setup** - Automatic path detection with first-run wizard

## 🎯 Quick Start

### Windows Users (Easiest)

1. Open the BP Extract folder
2. Double-click **`launch.bat`**
3. Your browser automatically opens to the dashboard
4. That's it! The app will guide you through setup

### macOS & Linux Users

1. Open terminal in the BP Extract folder
2. Run: `python3 launch.py`
3. Browser opens automatically
4. Follow the setup wizard

### Manual Web Mode

```bash
# Install dependencies (one-time)
pip install Flask

# Run the web interface
python app.py

# Open in browser: http://localhost:5000
```

## 📋 System Requirements

- **Python**: 3.12 or higher (downloads at https://www.python.org)
- **Star Citizen**: Installed and playable

## 🔧 Installation

### 1. Get the Code

```bash
# Clone or download this repository
git clone https://github.com/jonigirl/bp-extract.git
cd bp-extract
```

### 2. Set Up Python Environment (Optional but Recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install Flask
```

Or use the bundled file:

```bash
pip install -r requirements.txt
```

## 🚀 Usage

### Web Interface (Recommended)

**First Run:**
- The setup wizard will auto-detect your Star Citizen installation
- If auto-detection fails, you can enter paths manually
- Existing CSV data will be automatically migrated to JSON

**Dashboard Features:**
- View all blueprints with acquisition timestamps
- Search by blueprint name (live filtering)
- Sort by name or acquisition time
- See statistics: total collected, today's acquisitions, last acquired
- Pause/Resume monitoring anytime
- Scan backup logs for missed blueprints
- Toggle auto-refresh (3-second intervals)

### Command-Line Interface

```bash
python main.py              # Interactive mode (prompts to scan backups)
python main.py --no-scan   # Start monitoring immediately
```

## 📁 Project Structure

```
BP Extract/
├── config.py              # Configuration management & auto-detection
├── core.py                # Core monitoring logic (JSON-based)
├── app.py                 # Flask web server
├── main.py                # CLI interface
├── setup_wizard.py        # First-run configuration wizard
├── launch.py              # Cross-platform launcher
├── launch.bat             # Windows batch launcher
├── templates/
│   └── index.html         # Web dashboard HTML
├── static/
│   └── style.css          # Dashboard styling
├── config.json            # Configuration (auto-created)
├── blueprints.json        # Blueprint data (replaces CSV)
├── blueprints.csv.backup  # Backup of original CSV (if migrated)
└── requirements.txt       # Python dependencies
```

## 🗂️ Data Format

Blueprints are now stored in modern JSON format (`blueprints.json`):

```json
{
  "blueprints": [
    {
      "name": "Aurora MR",
      "timestamp": "2026-03-26T01:43:22.515Z"
    },
    {
      "name": "Avenger Stalker",
      "timestamp": "2026-03-26T02:15:45.123Z"
    }
  ]
}
```

**Benefits over CSV:**
- Human-readable and context-aware
- Extensible for future features
- Faster JSON parsing
- Native support in all modern systems

## ⚙️ Configuration

### First-Run Setup

The setup wizard will:
1. Detect your OS (Windows/macOS/Linux)
2. Search for Star Citizen installation
3. Auto-fill game log path if found
4. Ask you to confirm or customize paths
5. Offer to migrate existing CSV data

### Manual Configuration

Edit `config.json` to customize:

```json
{
  "log_file": "/path/to/Game.log",
  "backup_dir": "/path/to/logbackups",
  "data_file": "blueprints.json",
  "poll_interval": 0.5,
  "wait_interval": 1.0,
  "first_run": false,
  "platform": "Windows"
}
```

### Environment Variables

Override config with environment variables:

```bash
# Windows PowerShell
$env:SC_LOG_FILE = "C:\Path\To\Game.log"
$env:SC_BACKUP_DIR = "C:\Path\To\logbackups"
$env:SC_DATA_FILE = "blueprints.json"
python app.py

# macOS/Linux
export SC_LOG_FILE="/path/to/Game.log"
export SC_BACKUP_DIR="/path/to/logbackups"
python app.py
```

## 🔄 Portability

BP Extract auto-detects your system and Star Citizen installation:

**Windows Locations Checked:**
- `C:\Program Files\Roberts Space Industries\StarCitizen\LIVE`
- `E:\Roberts Space Industries\StarCitizen\LIVE` (common alternate drive)
- `D:\Roberts Space Industries\StarCitizen\LIVE`
- `C:\Games\StarCitizen\LIVE`

**macOS Locations Checked:**
- `~/Library/Application Support/Star Citizen`
- `~/Games/StarCitizen`

**Linux Locations Checked:**
- `~/.local/share/StarCitizen` (native)
- `~/.wine/drive_c/Roberts Space Industries/StarCitizen` (Wine/Proton)
- `~/Games/StarCitizen`

If auto-detection doesn't find your installation, the setup wizard lets you enter the path manually.

## 🔀 CSV to JSON Migration

If you have existing Blueprint data in `blueprints.csv`:
- The setup wizard automatically detects it
- Offers to migrate all data to `blueprints.json`
- Backs up original as `blueprints.csv.backup`
- No data is lost in the process

## 📤 Export Data

### CSV Export
Export blueprints as CSV for Excel:
- Dashboard: API endpoint at `/api/export/csv`
- CLI: Manual export from `blueprints.json`

### Direct JSON Access
Blueprints are stored in `blueprints.json` for easy access or backup.

## 🐛 Troubleshooting

### "Python 3.12 required"
- Download Python 3.12+ from https://www.python.org
- Ensure Python is in your PATH
- Restart your terminal after installation

### "Star Citizen installation not found"
- Ensure Star Citizen is installed and has been run at least once
- Use the setup wizard to manually enter your installation path
- Check the path contains both `Game.log` and `logbackups` folders

### "Flask not installed"
Run: `pip install Flask`

### "Port 5000 already in use"
- Another application is using port 5000
- Close the conflicting application, or
- The launcher will automatically find another available port

### Blueprint detection not working
- Ensure Star Citizen has run and generated `Game.log`
- Check the log file format matches your SC version
- Try closing and reopening the game to generate new log entries

### macOS/Linux Issues
- Use `python3` instead of `python` if needed
- Ensure SC is running through Proton/Wine
- Check file paths use forward slashes `/` not backslashes

## 🎨 Customization

### Edit Web Dashboard
Modify `templates/index.html` and `static/style.css` to customize the interface.

### Add Features
Extend `app.py` to add new API routes or functionality.

### Change Monitoring Interval
Edit `config.json` - decrease `poll_interval` for faster detection (0.1 = very responsive, 1.0 = slower but less CPU).

## 📊 Performance

- **Startup:** <1 second
- **Dashboard Load:** <500ms
- **Memory Usage:** ~50MB
- **CPU Impact:** Minimal while idle
- **Supported Blueprints:** 1000+ without slowdown
- **Auto-refresh:** Efficient 3-second polling

## 📝 Version History

- **v0.3.0** - JSON migration, cross-platform auto-detection, setup wizard
- **v0.2.0** - Web interface with Flask dashboard
- **v0.1.0** - Initial CLI-only version

## 🙏 Credits & Acknowledgments

**Original Concept**: This project was inspired by `blueprint_extractor` created by **infectoid (fec)**, a fellow member of our Star Citizen organization.

The core log parsing and blueprint detection logic built upon their original work. BP Extract extends this concept with:
- Modern web interface with real-time dashboard
- Cross-platform support (Windows/macOS/Linux)
- JSON-based storage with automatic migration
- Interactive setup wizard with auto-detection
- Search, filter, and statistics features

Special thanks to infectoid for the original blueprint extraction concept and for sharing it with the org!

## 🤝 Contributing

Suggestions and contributions welcome! Feel free to:
- Report bugs
- Request features
- Submit improvements
- Share feedback

## 📄 License

This project is provided as-is for personal use with Star Citizen.

## ❓ Support

If you encounter issues:

1. Run the setup wizard again: `python setup_wizard.py`
2. Check your Star Citizen is installed at the detected path
3. Verify `Game.log` exists in your installation
4. Ensure Python 3.12+ is installed
5. Try running in CLI mode: `python main.py`

## 🔧 Technical Details

### Architecture
- **Backend:** Flask (lightweight Python web framework)
- **Frontend:** HTML5 + CSS3 + Vanilla JavaScript (no build process)
- **Storage:** JSON files (local, no database)
- **Monitoring:** Python threading + file polling
- **Configuration:** Auto-detection + JSON config file

### No External Dependencies (besides Flask)
- Pure Python standard library for file operations
- No database server required
- No cloud connectivity
- All data stays local on your computer

---

**Ready to track your blueprints?** Start with `launch.bat` (Windows) or `python launch.py` (Mac/Linux)!
