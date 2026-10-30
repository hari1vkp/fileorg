"""Shared constants and design tokens for fileorg."""

from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "fileorg"
APP_VERSION = "1.2.0"
APP_TAGLINE = "Sort a folder into tidy category folders. Preview first, undo anytime."
DEFAULT_SOURCE_TEXT = "~/Downloads"

UNKNOWN_FOLDER = "Other"

JOURNAL_PREFIX = "journal-"
JOURNAL_SUFFIX = ".json"
JOURNAL_VERSION = 1

# Folder name -> space separated extensions (lower case, no leading dot).
CATEGORIES: dict[str, str] = {
    "Images": (
        "jpg jpeg png gif bmp svg webp tiff tif heic heif avif ico "
        "raw cr2 cr3 nef arw dng orf rw2"
    ),
    "Videos": "mp4 mkv mov avi wmv flv webm m4v mpg mpeg mts m2ts 3gp ogv",
    "Audio": "mp3 wav flac aac ogg oga m4a wma opus aiff alac mid midi",
    "Documents": "pdf doc docx txt rtf odt md markdown pages epub mobi azw3 djvu tex",
    "Spreadsheets": "xls xlsx xlsm csv tsv ods numbers",
    "Presentations": "ppt pptx pps ppsx odp key",
    "Archives": "zip rar 7z tar gz bz2 xz zst tgz tbz2 txz iso dmg",
    "Installers": "exe msi deb rpm apk pkg appimage flatpak snap",
    "Code": (
        "py js mjs cjs ts tsx jsx html htm css scss sass less json xml yml yaml "
        "toml ini cfg sh bash zsh fish ps1 bat cmd c h cpp hpp cc java kt go rs "
        "rb php lua pl sql ipynb"
    ),
    "Fonts": "ttf otf woff woff2 eot",
    "Design": "psd ai xcf fig sketch afdesign afphoto",
    "3D": "obj fbx stl glb gltf blend usdz",
}

CATEGORY_FOLDERS: tuple[str, ...] = tuple(CATEGORIES)

COMPOUND_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz", ".tar.zst")

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEMES: tuple[str, ...] = (THEME_LIGHT, THEME_DARK)

# Tone names used by the UI when reporting an outcome.
TONE_MUTED = "muted"
TONE_ACCENT = "accent"
TONE_SUCCESS = "success"
TONE_WARNING = "warning"
TONE_DANGER = "danger"


def extension_map() -> dict[str, str]:
    """Build a lower-case extension -> folder mapping."""
    mapping: dict[str, str] = {}
    for folder, extensions in CATEGORIES.items():
        for ext in extensions.split():
            mapping[ext] = folder
    return mapping


@dataclass(frozen=True)
class Spacing:
    """Consistent space increments, in pixels."""

    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True)
class Radii:
    """Corner radii used by the rounded components, in pixels."""

    sm: int = 8
    md: int = 14
    lg: int = 20
    pill: int = 999


SPACE = Spacing()
RADII = Radii()
