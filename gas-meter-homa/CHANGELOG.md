<!-- https://developers.home-assistant.io/docs/add-ons/presentation#keeping-a-changelog -->
# Changelog

All changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.2.0] - 2026-03-08
### Changed
- Replaced deprecated object_id by default_entity_id in homeassistant_config
- Set LOG_TIMESTAMP to %Y-%m-%d %T
- Bump docker/login-action from 3.6.0 to 4.0.0
- Bump actions/checkout from 6.0.1 to 6.0.2
- Bump tj-actions/changed-files from 47.0.1 to 47.0.5
- Bump home-assistant/builder from 2025.11.0 to 2026.02.1

## [1.1.0] - 2026-01-18
### Fixed
- Refacored use of global variables to function attributes in gas_meter.py
- Fixed debounce handling
### Added
- Added suggested_display_precision to Home Assistant discovery config messages

## [1.0.0] - 2026-01-10
- Initial release
