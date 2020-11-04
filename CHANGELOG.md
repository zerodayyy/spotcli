# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.3] - 2020-11-04

### Changed

- Replaced [consulate](https://pypi.org/project/consulate/) with [python-consul2](https://pypi.org/project/python-consul2/) as Consul client
- Changed mininal Python version to 3.6

### Fixed

- Fixed loading config from Consul on Python 3.9

## [1.0.2] - 2020-11-04

### Changed

- Get version from package metadata

## [1.0.1] - 2020-11-04

### Fixed

- Fixed suspend/unsuspend action for Elastigroups with multiple scaling policies
- Fixed tasks always targetting the first group in the list

## [1.0.0] - 2020-11-03

### Added

- Initial version

[unreleased]: https://github.com/SupersonicAds/spotcli/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/SupersonicAds/spotcli/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/SupersonicAds/spotcli/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/SupersonicAds/spotcli/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/SupersonicAds/spotcli/releases/tag/v1.0.0
