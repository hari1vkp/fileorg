<p align="center"><img src="assets/icon.svg" width="72" height="72" alt="fileorg icon"></p>

<h1 align="center">fileorg</h1>

<p align="center">A small, safe Python script that turns a messy Downloads folder into tidy category folders.</p>

<p align="center">
  <a href="https://github.com/hari1vkp/fileorg/actions/workflows/tests.yml"><img src="https://github.com/hari1vkp/fileorg/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
</p>

`fileorg` scans a folder (`~/Downloads` by default) and moves each file into a category
folder such as `Images/`, `Videos/`, `Documents/`, `Archives/` or `Code/`, based on its
extension. One file, no dependencies, and a dry run unless you ask it to move something.

```console
$ python3 fileorg.py
fileorg 1.0.0 - /home/you/Downloads (dry run)

  Archives/    1 file
  Audio/       1 file
  Code/        1 file
  Documents/   3 files
  Images/      2 files
  Installers/  1 file
  Videos/      1 file

  1 unrecognised file left in place (use --move-unknown).

Would move 10 files. Re-run with --apply to do it.
```

## Features

- **Dry run by default** — nothing moves until you pass `--apply`.
- **Never overwrites** — name clashes become `photo (1).jpg`, `photo (2).jpg`, ...
- **Undo** — every run is journalled, and `--undo --apply` puts everything back.
- **150+ extensions** across 12 categories, plus an `Other/` folder for the rest.
- **Recursive mode** for nested downloads, with existing category folders skipped.
- **Cross-platform** — Linux, macOS and Windows; Python 3.9+.
- **No dependencies** and no install step.

## Quick start

```bash
git clone https://github.com/hari1vkp/fileorg.git
cd fileorg

python3 fileorg.py            # preview what would happen in ~/Downloads
python3 fileorg.py --apply    # move the files
```

## Usage

```
python3 fileorg.py [SOURCE] [options]
```

| Option | Description |
| --- | --- |
| `SOURCE` | Folder to organise. Defaults to `~/Downloads`. |
| `-d, --dest DIR` | Put the category folders somewhere else (another drive, for example). |
| `-n, --apply` | Actually move files. Without this, `fileorg` only prints a plan. |
| `-r, --recursive` | Also organise files inside subfolders. |
| `-u, --move-unknown` | Move files with unknown extensions into `Other/` instead of leaving them. |
| `--include-hidden` | Include dotfiles and hidden folders. |
| `--ignore PATTERN` | Skip names matching a glob. Repeatable. |
| `--undo` | Reverse the most recent run (preview unless combined with `--apply`). |
| `--journal FILE` | Undo a specific journal instead of the latest one. |
| `--state-dir DIR` | Store journals in `DIR` instead of the platform default. |
| `-v, --verbose` | Print every file as it is handled. |
| `--version` | Print the version. |

### Examples

```bash
# Organise a folder other than Downloads
python3 fileorg.py ~/Desktop --apply

# Include subfolders, but leave PDFs where they are
python3 fileorg.py ~/Downloads --recursive --ignore "*.pdf" --apply

# Sort onto another drive without touching the originals' names
python3 fileorg.py ~/Downloads --dest /mnt/storage/Sorted --apply

# Also file away unknown extensions
python3 fileorg.py ~/Downloads --apply --move-unknown
```

## Where files go

| Folder | Extensions (examples) |
| --- | --- |
| `Images/` | jpg, jpeg, png, gif, svg, webp, heic, avif, raw, cr2, nef, dng |
| `Videos/` | mp4, mkv, mov, avi, webm, m4v, mpg, mts, 3gp |
| `Audio/` | mp3, wav, flac, aac, ogg, m4a, opus, aiff, midi |
| `Documents/` | pdf, doc, docx, txt, rtf, odt, md, epub, tex |
| `Spreadsheets/` | xls, xlsx, csv, tsv, ods, numbers |
| `Presentations/` | ppt, pptx, odp, key |
| `Archives/` | zip, rar, 7z, tar, gz, xz, iso, dmg |
| `Installers/` | exe, msi, deb, rpm, apk, pkg, appimage |
| `Code/` | py, js, ts, html, css, json, yaml, sh, c, cpp, java, go, rs, sql |
| `Fonts/` | ttf, otf, woff, woff2 |
| `Design/` | psd, ai, xcf, fig, sketch |
| `3D/` | obj, fbx, stl, glb, gltf, blend |

Anything else stays where it is, unless you pass `--move-unknown`, in which case it goes
to `Other/`. The full mapping lives at the top of [`fileorg.py`](fileorg.py) and is easy
to edit.

## Undo

Each `--apply` run writes a journal to:

| Platform | Journal location |
| --- | --- |
| Linux | `~/.local/state/fileorg/` (or `$XDG_STATE_HOME/fileorg`) |
| macOS | `~/Library/Application Support/fileorg/` |
| Windows | `%LOCALAPPDATA%\fileorg\` |

```bash
python3 fileorg.py --undo           # preview the restore
python3 fileorg.py --undo --apply   # restore the files
```

Undo moves the files back, removes the category folders it emptied, and marks the
journal as `.undone` so the next `--undo` targets the run before it.

## Safety notes

- `fileorg` **moves** files; it does not copy them. `shutil.move` handles cross-device moves.
- Hidden files and symlinks are skipped by default.
- Existing files are never overwritten — a numbered suffix is added instead.
- Already-organised category folders are not walked again in `--recursive` mode, so files
  don't get shuffled into `Images/Images/`.
- If a run is interrupted, files moved so far are still journalled and can be undone.

## Development

```bash
python3 -m unittest discover -s tests -v
```

The test suite covers dry runs, category placement, collisions, hidden files, symlinks,
recursive runs, custom destinations, ignores and undo. CI runs it on Linux, macOS and
Windows with Python 3.9 and 3.13.

## License

[MIT](LICENSE)
