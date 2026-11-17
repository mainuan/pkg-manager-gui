<div align="center">

<img src="https://raw.githubusercontent.com/mainuan/.github/main/profile/assets/mainuan-logo.svg" width="96" alt="Mainuan logo">

# PKG Manager

Installs or removes, with a confirmation and a progress bar, the application in a `.flatpakref` or `.AppImage` file.

[![CI](https://github.com/mainuan/pkg-manager-gui/actions/workflows/ci.yml/badge.svg)](https://github.com/mainuan/pkg-manager-gui/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/mainuan/pkg-manager-gui)](https://github.com/mainuan/pkg-manager-gui/releases/latest)
[![License](https://img.shields.io/github/license/mainuan/pkg-manager-gui)](license)
![Platform](https://img.shields.io/badge/Kubuntu%2026.04%20%7C%20Plasma%206.6-0079c1)

[Português](README.md) · **English**

</div>

---

## About

PKG Manager (`pkg-manager-gui`) is a small Python/PySide6 (Qt 6) installer that
picks the action from the file extension. Since 1.1.0 it is a 36 KB
`Architecture: all` Debian package using Ubuntu's Python and PySide6; it
replaces the former 81 MB PyInstaller-based `flatpak-manager-gui`.

## Features

- **`.flatpakref`**: installed with `flatpak install`, or removed when an application with the same ID (file name without extension) is already installed; runs through `pkexec` unless the user is root or in the `flatpak` group.
- **`.AppImage`** (type 2): copied to `/opt/appimages-installed` with a menu entry and icon, and recorded in the dpkg database as package `<name>appimage` so it can be removed later. The AppImage is never run: the backend copies it to a private root-owned directory, finds the SquashFS offset from the ELF header, checks the `hsqs` magic and extracts only the `.desktop` file and `.DirIcon` with `unsquashfs -o <offset>`; the record is a real `.deb` built with `dpkg-deb` and installed with `dpkg -i`, so `dpkg -r` removes every file, icons included. Type 1 AppImages and other files are refused with an explanation. Done by `/usr/libexec/pkg-manager-gui/appimage_manager_backend` through `pkexec` (polkit action `br.com.aratie.appimagemanager.pkexec`, admin authentication).
- Confirmation before installing or removing, progress parsed from the process output, result in a message box.
- Interface, desktop entry and polkit policy in 33 languages.

## Installation

Preinstalled in the Mainuan Linux ISO. On another Kubuntu/Ubuntu 26.04 system,
download the `.deb` and `SHA256SUMS` from the
[latest release](https://github.com/mainuan/pkg-manager-gui/releases/latest):

```bash
sha256sum --check --ignore-missing SHA256SUMS
sudo apt install ./pkg-manager-gui_1.1.1_all.deb
```

## Usage

```bash
pkg-manager-gui ~/Downloads/org.gimp.GIMP.flatpakref
```

Without an argument it prints `Usage: pkg-manager-gui <url/file>` and exits
with status 1 (see `man pkg-manager-gui`).

## Building and testing

```bash
git clone https://github.com/mainuan/pkg-manager-gui.git
cd pkg-manager-gui
sudo apt build-dep ./
dpkg-buildpackage -us -uc -b
```

The build runs `tests/test_logic.py`, `tests/test_backend.py`, `tests/test_i18n.py`,
`desktop-file-validate` and `xmllint`. CI ([`ci.yml`](.github/workflows/ci.yml))
also runs `po/i18n.sh check-pot` and `po/i18n.sh validate`, lints the package,
installs it in a clean Ubuntu 26.04 container and smoke-tests it. Releases are
published only from `v*` tags.

## Translations

33 languages via gettext; see [docs/i18n/README.md](docs/i18n/README.md).

## Credits

Guilherme Rialli Oliveira ([@guirialli](https://github.com/guirialli)) and
Rafael Ruscher ([@ruscher](https://github.com/ruscher)).

## License

[MIT](license), Copyright (c) 2025 Charles Santana.
