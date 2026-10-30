"""User-facing dialogs, kept separate from the screens that trigger them."""

from __future__ import annotations

from tkinter import messagebox

from app.models.organise import OrganisePlan, OrganiseResult, UndoPlan, UndoResult
from app.utils.helpers import error_lines, plural


class Dialogs:
    """A thin, theme-neutral wrapper around Tk's message boxes."""

    def __init__(self, root) -> None:
        self.root = root

    def confirm_organise(self, plan: OrganisePlan) -> bool:
        return messagebox.askyesno(
            "Organise files?",
            f"Move {plural(len(plan.moves), 'file')} into "
            f"{plural(plan.folder_count, 'folder')} in:\n\n{plan.destination}\n\n"
            "Nothing is overwritten, and this run can be undone.",
            icon="question",
            default="yes",
            parent=self.root,
        )

    def confirm_undo(self, plan: UndoPlan) -> bool:
        return messagebox.askyesno(
            "Undo the last run?",
            f"Restore {plural(len(plan.entries), 'file')} to their original places?\n\n"
            "Emptied category folders will be removed.",
            icon="question",
            default="yes",
            parent=self.root,
        )

    def nothing_to_move(self) -> None:
        self.info(
            "Nothing to move",
            "This folder is already tidy for the selected options.",
        )

    def nothing_to_undo(self) -> None:
        self.info("Nothing to undo", "No organise run has been recorded yet.")

    def nothing_to_restore(self) -> None:
        self.info(
            "Nothing to restore",
            "The files from the last run are no longer where they were moved.",
        )

    def organise_done(self, result: OrganiseResult) -> None:
        lines = [f"Moved {plural(result.moved_count, 'file')}."]
        if result.errors:
            pairs = [(error.name, error.message) for error in result.errors]
            lines.append("")
            lines.append(f"{plural(len(result.errors), 'file')} could not be moved:")
            lines.extend(error_lines(pairs))
            self.warning("Finished with errors", "\n".join(lines))
            return
        if result.journal is not None:
            lines.append("")
            lines.append(f"Journal: {result.journal}")
        self.info("Organised", "\n".join(lines))

    def undo_done(self, result: UndoResult) -> None:
        lines = [f"Restored {plural(result.restored_count, 'file')}."]
        if result.removed:
            lines.append(f"Removed {plural(len(result.removed), 'empty folder')}.")
        if result.missing:
            lines.append("")
            lines.append(
                f"{plural(len(result.missing), 'file')} was no longer in its "
                "organised place."
            )
        if result.errors:
            pairs = [(error.name, error.message) for error in result.errors]
            lines.append("")
            lines.append(f"{plural(len(result.errors), 'file')} could not be restored:")
            lines.extend(error_lines(pairs))
            self.warning("Undo complete", "\n".join(lines))
            return
        self.info("Undo complete", "\n".join(lines))

    def info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message, parent=self.root)

    def warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message, parent=self.root)

    def error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self.root)
