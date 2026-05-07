# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.6] - 2026-05-07

### Added

- Atkinson Hyperlegible as default font with OpenDyslexic opt-in toggle
- Font toggle button in the web header; preference persisted in localStorage

## [0.4.5] - 2026-04-15

### Fixed

- Browser-close watchdog moved to main thread in `launch.py`

## [0.4.4] - 2026-04-01

### Fixed

- `statsData` scope error in scan progress banner

## [0.4.3] - 2026-03-15

### Added

- Scan progress banner showing live stats during backup log scans
- Browser-close auto-exit: app shuts down when the browser tab is closed

## [0.4.2] - 2026-02-20

### Fixed

- Monitoring thread started with invalid paths in tests
- CI test failures: first-run state in client fixture, sys-level capture

## [0.4.1] - 2026-02-10

### Changed

- Improved `launch.bat` Python detection (uv, venv, and system Python fallback)
- Updated README quick-start instructions

## [0.4.0] - 2026-01-20

### Added

- CSRF protection on all mutating endpoints
- Logging module with structured output
- Test suite with 87% coverage and CI pipeline

### Changed

- Full web interface overhaul with modern responsive design
- `launch.bat` auto-setup: installs dependencies, opens browser automatically
- Migrated from `requirements.txt` to UV / `uv sync`

### Fixed

- Threading safety across monitoring and config paths
- Config path anchoring to prevent traversal

## [0.3.0] - 2025-11-01

### Added

- Initial public release: web dashboard, live stats, search/filter, backup scanning, pause/resume, auto-refresh, JSON storage

[0.4.6]: https://github.com/jonigirl/bp-extract/releases/tag/v0.4.6
[0.4.5]: https://github.com/jonigirl/bp-extract/releases/tag/v0.4.5
[0.4.4]: https://github.com/jonigirl/bp-extract/releases/tag/v0.4.4
[0.4.3]: https://github.com/jonigirl/bp-extract/releases/tag/v0.4.3
[0.4.2]: https://github.com/jonigirl/bp-extract/releases/tag/v0.4.2
[0.4.1]: https://github.com/jonigirl/bp-extract/releases/tag/v0.4.1
[0.4.0]: https://github.com/jonigirl/bp-extract/releases/tag/v0.4.0
[0.3.0]: https://github.com/jonigirl/bp-extract/releases/tag/v0.3.0
