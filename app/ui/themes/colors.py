"""Semantic colour palettes for the light and dark themes.

Screens never hardcode a colour: they ask the active :class:`Palette` for a
role such as ``surface`` or ``danger``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.core.constants import UNKNOWN_FOLDER


@dataclass(frozen=True)
class Palette:
    """A complete set of semantic colours for one theme."""

    background: str
    sidebar: str
    surface: str
    surface_alt: str
    border: str
    border_strong: str
    text: str
    muted: str
    faint: str
    accent: str
    accent_hover: str
    accent_soft: str
    on_accent: str
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str
    selection: str
    stripe: str
    scrollbar: str
    tip_bg: str
    tip_border: str
    tip_text: str
    nav_active_bg: str
    nav_active_fg: str
    disabled_bg: str
    disabled_text: str
    categories: Mapping[str, str]


LIGHT_CATEGORIES: Mapping[str, str] = {
    "Images": "#0284c7",
    "Videos": "#7c3aed",
    "Audio": "#059669",
    "Documents": "#d97706",
    "Spreadsheets": "#0d9488",
    "Presentations": "#ea580c",
    "Archives": "#dc2626",
    "Installers": "#4f46e5",
    "Code": "#2563eb",
    "Fonts": "#9333ea",
    "Design": "#db2777",
    "3D": "#0891b2",
    UNKNOWN_FOLDER: "#64748b",
}

DARK_CATEGORIES: Mapping[str, str] = {
    "Images": "#38bdf8",
    "Videos": "#a78bfa",
    "Audio": "#34d399",
    "Documents": "#fbbf24",
    "Spreadsheets": "#2dd4bf",
    "Presentations": "#fb923c",
    "Archives": "#f87171",
    "Installers": "#818cf8",
    "Code": "#60a5fa",
    "Fonts": "#c084fc",
    "Design": "#f472b6",
    "3D": "#22d3ee",
    UNKNOWN_FOLDER: "#94a3b8",
}

LIGHT = Palette(
    background="#eef2f7",
    sidebar="#ffffff",
    surface="#ffffff",
    surface_alt="#f8fafc",
    border="#e2e8f0",
    border_strong="#cbd5e1",
    text="#0f172a",
    muted="#64748b",
    faint="#94a3b8",
    accent="#0284c7",
    accent_hover="#0369a1",
    accent_soft="#e0f2fe",
    on_accent="#ffffff",
    success="#059669",
    success_soft="#ecfdf5",
    warning="#d97706",
    warning_soft="#fffbeb",
    danger="#dc2626",
    danger_soft="#fef2f2",
    selection="#e0f2fe",
    stripe="#f8fafc",
    scrollbar="#cbd5e1",
    tip_bg="#f0f9ff",
    tip_border="#bae6fd",
    tip_text="#075985",
    nav_active_bg="#e0f2fe",
    nav_active_fg="#0369a1",
    disabled_bg="#bae6fd",
    disabled_text="#eff6ff",
    categories=LIGHT_CATEGORIES,
)

DARK = Palette(
    background="#0b1220",
    sidebar="#0f172a",
    surface="#111c2e",
    surface_alt="#16233a",
    border="#1e293b",
    border_strong="#334155",
    text="#e2e8f0",
    muted="#94a3b8",
    faint="#64748b",
    accent="#38bdf8",
    accent_hover="#7dd3fc",
    accent_soft="#0c4a6e",
    on_accent="#04121f",
    success="#34d399",
    success_soft="#052e24",
    warning="#fbbf24",
    warning_soft="#3a2a06",
    danger="#f87171",
    danger_soft="#3a1214",
    selection="#1e3a5f",
    stripe="#0f1a2b",
    scrollbar="#334155",
    tip_bg="#0c2438",
    tip_border="#155e75",
    tip_text="#bae6fd",
    nav_active_bg="#0c4a6e",
    nav_active_fg="#e0f2fe",
    disabled_bg="#1e3a5f",
    disabled_text="#64748b",
    categories=DARK_CATEGORIES,
)

PALETTES: dict[str, Palette] = {"light": LIGHT, "dark": DARK}


def palette_for(name: str) -> Palette:
    """Return the palette for ``name``, defaulting to light."""
    return PALETTES.get(name, LIGHT)
