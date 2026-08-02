from __future__ import annotations

import tkinter as tk
from tkinter import ttk

KEYCODE_MAP = {
    65: "<<SelectAll>>",  # A / Ф
    67: "<<Copy>>",       # C / С
    86: "<<Paste>>",      # V / М
    88: "<<Cut>>",        # X / Ч
}

_SUPPORTED_TYPES = (tk.Text, tk.Entry, ttk.Entry, ttk.Combobox)


def _is_readonly(widget):
    if isinstance(widget, tk.Text):
        return widget.cget("state") == "disabled"
    if isinstance(widget, (tk.Entry, ttk.Entry)):
        return widget.cget("state") in ("readonly", "disabled")
    return False


def _select_all(widget):
    if isinstance(widget, tk.Text):
        widget.tag_add(tk.SEL, "1.0", tk.END)
        widget.mark_set(tk.INSERT, "1.0")
        widget.see(tk.INSERT)
    else:
        widget.selection_range(0, tk.END)
        widget.icursor(tk.END)


def _handle_shortcut(event):
    """Handle Ctrl+ physical key regardless of layout."""
    if event.state & 0x4:  # Control modifier
        action = KEYCODE_MAP.get(event.keycode)
        if action is None:
            return
        widget = event.widget
        if not isinstance(widget, _SUPPORTED_TYPES):
            return
        readonly = _is_readonly(widget)
        if readonly and action in ("<<Paste>>", "<<Cut>>"):
            return "break"
        if action == "<<SelectAll>>":
            _select_all(widget)
        else:
            widget.event_generate(action)
        return "break"


def install_global_shortcuts(root):
    root.bind_all("<KeyPress>", _handle_shortcut, add="+")


def add_context_menu(widget):
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(
        label="Вырезать",
        command=lambda: widget.event_generate("<<Cut>>"),
        accelerator="Ctrl+X",
    )
    menu.add_command(
        label="Копировать",
        command=lambda: widget.event_generate("<<Copy>>"),
        accelerator="Ctrl+C",
    )
    menu.add_command(
        label="Вставить",
        command=lambda: widget.event_generate("<<Paste>>"),
        accelerator="Ctrl+V",
    )
    menu.add_separator()
    menu.add_command(
        label="Выделить всё",
        command=lambda: _select_all(widget),
        accelerator="Ctrl+A",
    )

    def _show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", _show_menu)
    widget.bind("<Button-2>", _show_menu)


def bind_shortcuts(widget):
    """Add context menu to widget. Global keybindings via install_global_shortcuts."""
    if isinstance(widget, _SUPPORTED_TYPES):
        add_context_menu(widget)


def bind_shortcuts_recursive(parent):
    """Apply bind_shortcuts to all Entry, Text, and Combobox descendants of parent."""
    for child in parent.winfo_children():
        if isinstance(child, _SUPPORTED_TYPES):
            add_context_menu(child)
        elif isinstance(child, tk.Widget):
            bind_shortcuts_recursive(child)