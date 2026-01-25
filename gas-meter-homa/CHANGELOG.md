<!-- https://developers.home-assistant.io/docs/add-ons/presentation#keeping-a-changelog -->
# Changelog

All changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Changed
- Replaced deprecated object_id by default_entity_id in homeassistant_config

## [1.1.0] - 2026-01-18
### Fixed
- Refacored use of global variables to function attributes in gas_meter.py
- Fixed debounce handling
### Added
- Added suggested_display_precision to Home Assistant discovery config messages

## [1.0.0] - 2026-01-10
- Initial release
