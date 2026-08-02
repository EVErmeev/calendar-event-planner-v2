from __future__ import annotations

import tkinter as tk
from tkinter import ttk

_SUPPORTED_TYPES = (tk.Text, tk.Entry, ttk.Entry, ttk.Combobox)


def _select_all(widget):
    if isinstance(widget, tk.Text):
        widget.tag_add(tk.SEL, "1.0", tk.END)
        widget.mark_set(tk.INSERT, "1.0")
        widget.see(tk.INSERT)
    else:
        widget.selection_range(0, tk.END)
        widget.icursor(tk.END)
    return "break"


def _add_context_menu(widget):
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
    """Bind Ctrl+C/V/X/A for both EN and RU keyboard layouts."""
    # English layout — physical keycodes: A=65, C=67, V=86, X=88
    widget.bind("<Control-KeyPress-c>", lambda e: widget.event_generate("<<Copy>>"))
    widget.bind("<Control-KeyPress-v>", lambda e: widget.event_generate("<<Paste>>"))
    widget.bind("<Control-KeyPress-x>", lambda e: widget.event_generate("<<Cut>>"))
    widget.bind("<Control-KeyPress-a>", lambda e: _select_all(widget))

    # Russian layout — Windows Tk keysyms for Ctrl in same physical position
    widget.bind("<Control-Cyrillic_es>", lambda e: widget.event_generate("<<Copy>>"))
    widget.bind("<Control-Cyrillic_em>", lambda e: widget.event_generate("<<Paste>>"))
    widget.bind("<Control-Cyrillic_che>", lambda e: widget.event_generate("<<Cut>>"))
    widget.bind("<Control-Cyrillic_ef>", lambda e: _select_all(widget))

    if isinstance(widget, _SUPPORTED_TYPES):
        _add_context_menu(widget)


def bind_shortcuts_recursive(parent):
    """Apply bind_shortcuts to all Entry, Text, and Combobox descendants of parent."""
    for child in parent.winfo_children():
        if isinstance(child, _SUPPORTED_TYPES):
            bind_shortcuts(child)
        elif isinstance(child, tk.Widget):
            bind_shortcuts_recursive(child)