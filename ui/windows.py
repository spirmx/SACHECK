import shutil
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox
from urllib.parse import urlparse

import customtkinter as ctk

import sacheck_runtime as app_runtime
from sacheck_runtime import (
    CREATE_TOOLS,
    DETAIL_BUTTONS,
    FILE_TYPES,
    STATUSES,
    STATUS_DONE,
    STATUS_META,
    STATUS_PENDING,
    add_entry_context_menu,
    add_textbox_context_menu,
    adjust_color,
    best_text_color,
    blend_color,
    center_toplevel,
    focus_and_select,
    form_theme,
    infer_type_from_target,
    is_canonical_template_path,
    is_url,
    make_file_type_icon,
    messagebox as app_messagebox,
    normalize_hex_color,
    tool_default_name,
)

UI_BG = app_runtime.UI_BG
UI_BORDER = app_runtime.UI_BORDER
UI_BORDER_SOFT = app_runtime.UI_BORDER_SOFT
UI_MUTED = app_runtime.UI_MUTED
UI_NAV = app_runtime.UI_NAV
UI_NAV_TEXT = app_runtime.UI_NAV_TEXT
UI_SURFACE = app_runtime.UI_SURFACE
UI_SURFACE_2 = app_runtime.UI_SURFACE_2
UI_SURFACE_3 = app_runtime.UI_SURFACE_3
UI_TEXT = app_runtime.UI_TEXT


def refresh_theme_globals():
    global UI_BG, UI_BORDER, UI_BORDER_SOFT, UI_MUTED, UI_NAV, UI_NAV_TEXT
    global UI_SURFACE, UI_SURFACE_2, UI_SURFACE_3, UI_TEXT
    UI_BG = app_runtime.UI_BG
    UI_BORDER = app_runtime.UI_BORDER
    UI_BORDER_SOFT = app_runtime.UI_BORDER_SOFT
    UI_MUTED = app_runtime.UI_MUTED
    UI_NAV = app_runtime.UI_NAV
    UI_NAV_TEXT = app_runtime.UI_NAV_TEXT
    UI_SURFACE = app_runtime.UI_SURFACE
    UI_SURFACE_2 = app_runtime.UI_SURFACE_2
    UI_SURFACE_3 = app_runtime.UI_SURFACE_3
    UI_TEXT = app_runtime.UI_TEXT


class TaskForm(ctk.CTkToplevel):
    def __init__(self, master, on_save, task=None, mode=None):
        refresh_theme_globals()
        super().__init__(master)
        self.is_edit = bool(task and task.get("id"))
        self.mode = mode or (task or {}).get("target_kind") or ("url" if is_url((task or {}).get("link", "")) else "file")
        self.title("Edit task" if self.is_edit else "Add task")
        center_toplevel(self, master, 560, 560)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_save = on_save
        self.task = task or {}

        theme = form_theme()
        self.configure(fg_color=UI_BG)
        self.grid_columnconfigure(0, weight=1)
        body = ctk.CTkFrame(self, fg_color=theme["body"], corner_radius=14, border_width=1, border_color=theme["border"])
        body.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            body,
            text=("Edit project" if self.mode == "folder" else ("Edit link" if self.mode == "url" else "Edit file")) if self.is_edit else ("Add project" if self.mode == "folder" else ("Add link" if self.mode == "url" else "Add file")),
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="w")

        self.name_var = ctk.StringVar(value=self.task.get("name", ""))
        self.type_var = ctk.StringVar(value=self.task.get("type", "Other"))
        self.link_var = ctk.StringVar(value=self.task.get("link", ""))
        self.initial_link = self.link_var.get()
        self.auto_type_enabled = not bool(self.task.get("type")) or not self.initial_link
        self.setting_type_programmatically = False

        self.name_entry = self._entry(body, "Task name", self.name_var, 1)
        self.type_menu = ctk.CTkOptionMenu(
            body,
            values=list(FILE_TYPES.keys()),
            variable=self.type_var,
            command=self.mark_type_manual,
            fg_color=theme["field"],
            button_color=theme["neutral"],
            button_hover_color=theme["neutral_hover"],
            text_color=theme["text"],
        )
        ctk.CTkLabel(body, text="File type", text_color=theme["label"]).grid(
            row=3, column=0, padx=18, pady=(10, 4), sticky="w"
        )
        self.type_menu.grid(row=4, column=0, padx=18, sticky="ew")

        target_label = "Project folder path" if self.mode == "folder" else ("URL link" if self.mode == "url" else "Local file path")
        ctk.CTkLabel(body, text=target_label, text_color=theme["label"]).grid(
            row=5, column=0, padx=18, pady=(14, 4), sticky="w"
        )
        link_row = ctk.CTkFrame(body, fg_color="transparent")
        link_row.grid(row=6, column=0, padx=18, sticky="ew")
        link_row.grid_columnconfigure(0, weight=1)
        self.link_entry = ctk.CTkEntry(link_row, textvariable=self.link_var, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        self.link_entry.grid(row=0, column=0, sticky="ew")
        add_entry_context_menu(self.link_entry)
        if self.mode == "folder":
            ctk.CTkButton(link_row, text="Browse folder", width=112, command=self.browse_folder).grid(
                row=0, column=1, padx=(8, 0)
            )
        elif self.mode == "file":
            ctk.CTkButton(link_row, text="Browse", width=90, command=self.browse_file).grid(
                row=0, column=1, padx=(8, 0)
            )

        ctk.CTkLabel(body, text="Note / description", text_color=theme["label"]).grid(
            row=7, column=0, padx=18, pady=(14, 4), sticky="w"
        )
        self.note_box = ctk.CTkTextbox(body, height=120, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"], border_width=1)
        self.note_box.grid(row=8, column=0, padx=18, sticky="ew")
        add_textbox_context_menu(self.note_box)
        self.note_box.insert("1.0", self.task.get("note", ""))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=9, column=0, padx=18, pady=18, sticky="e")
        ctk.CTkButton(buttons, text="Cancel", fg_color=theme["neutral"], hover_color=theme["neutral_hover"], text_color=theme["neutral_text"], command=self.destroy).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(buttons, text="Save", command=self.save).grid(row=0, column=1)

        self.link_var.trace_add("write", self.auto_detect_type_from_target)
        self.after(80, lambda: focus_and_select(self.name_entry))

    def _entry(self, parent, label, variable, row):
        theme = form_theme()
        ctk.CTkLabel(parent, text=label, text_color=theme["label"]).grid(
            row=row, column=0, padx=18, pady=(10, 4), sticky="w"
        )
        entry = ctk.CTkEntry(parent, textvariable=variable, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        entry.grid(row=row + 1, column=0, padx=18, sticky="ew")
        add_entry_context_menu(entry)
        return entry

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select task file")
        if path:
            self.link_var.set(path)
            file_path = Path(path)
            if not self.name_var.get().strip():
                self.name_var.set(file_path.stem)
            self.auto_type_enabled = True
            self.set_type_auto(infer_type_from_target(path), allow_other=True)

    def browse_folder(self):
        path = filedialog.askdirectory(title="Select project folder")
        if path:
            self.link_var.set(path)
            folder_path = Path(path)
            if not self.name_var.get().strip():
                self.name_var.set(folder_path.name)
            self.auto_type_enabled = True
            self.set_type_auto(infer_type_from_target(path), allow_other=True)

    def mark_type_manual(self, *_):
        if self.setting_type_programmatically:
            return
        self.auto_type_enabled = False

    def set_type_auto(self, file_type: str, allow_other: bool = False):
        if not file_type or (file_type == "Other" and not allow_other):
            return
        self.setting_type_programmatically = True
        self.type_var.set(file_type)
        self.setting_type_programmatically = False

    def auto_detect_type_from_target(self, *_):
        target = self.link_var.get().strip()
        if target and target != self.initial_link:
            self.auto_type_enabled = True
        if not self.auto_type_enabled:
            return
        self.set_type_auto(infer_type_from_target(target))

    def save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Please enter a task name.")
            return
        target = self.link_var.get().strip()
        if self.mode == "url" and target and not is_url(target):
            messagebox.showwarning("Invalid URL", "Please enter a link starting with http:// or https://.")
            return
        if self.mode == "file" and not target:
            messagebox.showwarning("Missing file", "Please choose a local file path.")
            return
        if self.mode == "folder" and not target:
            messagebox.showwarning("Missing project", "Please choose a project folder path.")
            return
        task = {
            "id": self.task.get("id", str(uuid.uuid4())),
            "name": name,
            "type": self.type_var.get(),
            "link": target,
            "target_kind": self.mode,
            "shortcut_path": self.task.get("shortcut_path"),
            "note": self.note_box.get("1.0", "end").strip(),
            "status": self.task.get("status", STATUS_PENDING),
            "date_added": self.task.get("date_added", datetime.now().strftime("%Y-%m-%d %H:%M")),
            "done_date": self.task.get("done_date"),
        }
        self.on_save(task)
        self.destroy()


class LinkForm(ctk.CTkToplevel):
    def __init__(self, master, on_save, task=None):
        refresh_theme_globals()
        super().__init__(master)
        self.is_edit = bool(task and task.get("id"))
        self.title("Edit link" if self.is_edit else "Add link")
        center_toplevel(self, master, 560, 520)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_save = on_save
        self.task = task or {}

        theme = form_theme()
        self.configure(fg_color=UI_BG)
        self.grid_columnconfigure(0, weight=1)
        body = ctk.CTkFrame(self, fg_color=theme["body"], corner_radius=14, border_width=1, border_color=theme["border"])
        body.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Add link" if not self.is_edit else "Edit link",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(18, 10), sticky="w")

        self.name_var = ctk.StringVar(value=self.task.get("name", ""))
        self.type_var = ctk.StringVar(value=self.task.get("type", "Other"))
        self.link_var = ctk.StringVar(value=self.task.get("link", "https://"))
        self.initial_link = self.link_var.get()
        self.auto_type_enabled = not bool(self.task.get("type")) or not self.initial_link
        self.setting_type_programmatically = False

        self.name_entry = self._entry(body, "Task name", self.name_var, 1)

        ctk.CTkLabel(body, text="Link type", text_color=theme["label"]).grid(
            row=3, column=0, padx=18, pady=(10, 4), sticky="w"
        )
        ctk.CTkOptionMenu(
            body,
            values=list(FILE_TYPES.keys()),
            variable=self.type_var,
            command=self.mark_type_manual,
            fg_color=theme["field"],
            button_color=theme["neutral"],
            button_hover_color=theme["neutral_hover"],
            text_color=theme["text"],
        ).grid(row=4, column=0, padx=18, sticky="ew")

        ctk.CTkLabel(body, text="URL link", text_color=theme["label"]).grid(
            row=5, column=0, padx=18, pady=(14, 4), sticky="w"
        )
        url_row = ctk.CTkFrame(body, fg_color="transparent")
        url_row.grid(row=6, column=0, padx=18, sticky="ew")
        url_row.grid_columnconfigure(0, weight=1)
        self.link_entry = ctk.CTkEntry(url_row, textvariable=self.link_var, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        self.link_entry.grid(row=0, column=0, sticky="ew")
        add_entry_context_menu(self.link_entry)
        ctk.CTkButton(url_row, text="Paste URL", width=96, command=self.paste_url).grid(
            row=0, column=1, padx=(8, 0)
        )

        ctk.CTkLabel(body, text="Note / description", text_color=theme["label"]).grid(
            row=7, column=0, padx=18, pady=(14, 4), sticky="w"
        )
        self.note_box = ctk.CTkTextbox(body, height=105, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"], border_width=1)
        self.note_box.grid(row=8, column=0, padx=18, sticky="ew")
        add_textbox_context_menu(self.note_box)
        self.note_box.insert("1.0", self.task.get("note", ""))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=9, column=0, padx=18, pady=18, sticky="e")
        ctk.CTkButton(buttons, text="Cancel", fg_color=theme["neutral"], hover_color=theme["neutral_hover"], text_color=theme["neutral_text"], command=self.destroy).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(buttons, text="Save link", command=self.save, fg_color="#14b8a6", hover_color="#0f9f8f", text_color="#ffffff").grid(
            row=0, column=1
        )

        self.link_var.trace_add("write", self.auto_detect_type_from_target)
        self.after(80, lambda: focus_and_select(self.name_entry))

    def _entry(self, parent, label, variable, row):
        theme = form_theme()
        ctk.CTkLabel(parent, text=label, text_color=theme["label"]).grid(
            row=row, column=0, padx=18, pady=(10, 4), sticky="w"
        )
        entry = ctk.CTkEntry(parent, textvariable=variable, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        entry.grid(row=row + 1, column=0, padx=18, sticky="ew")
        add_entry_context_menu(entry)
        return entry

    def paste_url(self):
        try:
            value = self.clipboard_get().strip()
        except Exception:
            return "break"
        if value:
            self.link_var.set(value)
            if not self.name_var.get().strip():
                parsed = urlparse(value)
                self.name_var.set(parsed.netloc or value[:40])
        return "break"

    def mark_type_manual(self, *_):
        if self.setting_type_programmatically:
            return
        self.auto_type_enabled = False

    def set_type_auto(self, file_type: str):
        if not file_type or file_type == "Other":
            return
        self.setting_type_programmatically = True
        self.type_var.set(file_type)
        self.setting_type_programmatically = False

    def auto_detect_type_from_target(self, *_):
        target = self.link_var.get().strip()
        if target and target != self.initial_link:
            self.auto_type_enabled = True
        if not self.auto_type_enabled:
            return
        detected = infer_type_from_target(target)
        self.set_type_auto(detected)
        if target and not self.name_var.get().strip() and is_url(target):
            parsed = urlparse(target)
            path_name = Path(parsed.path.rstrip("/")).stem
            self.name_var.set(path_name or parsed.netloc or target[:40])

    def save(self):
        name = self.name_var.get().strip()
        target = self.link_var.get().strip()
        if not name:
            messagebox.showwarning("Missing name", "Please enter a task name.")
            return
        if not is_url(target):
            messagebox.showwarning("Invalid URL", "Please enter a link starting with http:// or https://.")
            return
        task = {
            "id": self.task.get("id", str(uuid.uuid4())),
            "name": name,
            "type": self.type_var.get(),
            "link": target,
            "target_kind": "url",
            "shortcut_path": self.task.get("shortcut_path"),
            "note": self.note_box.get("1.0", "end").strip(),
            "status": self.task.get("status", STATUS_PENDING),
            "date_added": self.task.get("date_added", datetime.now().strftime("%Y-%m-%d %H:%M")),
            "done_date": self.task.get("done_date"),
        }
        self.on_save(task)
        self.destroy()


class CreateNewWindow(ctk.CTkToplevel):
    def __init__(self, master):
        refresh_theme_globals()
        super().__init__(master)
        self.master_app = master
        self.title("Create New")
        center_toplevel(self, master, 820, 580)
        self.minsize(760, 520)
        self.transient(master)
        self.grab_set()
        self.tool_icons = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hero = ctk.CTkFrame(self, fg_color=UI_NAV, corner_radius=0)
        hero.grid(row=0, column=0, sticky="ew")
        hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hero,
            text="Create New Work",
            text_color=UI_NAV_TEXT,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=22, pady=(18, 2), sticky="w")
        ctk.CTkLabel(
            hero,
            text="Pick a tool. SACHECK will create a Doing task and open it right away.",
            text_color="#bfdbfe",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=22, pady=(0, 16), sticky="w")

        body = ctk.CTkFrame(self, fg_color=UI_BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        form = ctk.CTkFrame(body, fg_color=UI_SURFACE, corner_radius=14, border_width=1, border_color=UI_BORDER)
        form.grid(row=0, column=0, padx=18, pady=(16, 10), sticky="ew")
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(form, text="Task name", text_color=UI_TEXT, font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=(14, 10), pady=12, sticky="w"
        )
        self.name_var = ctk.StringVar(value="")
        name_entry = ctk.CTkEntry(
            form,
            textvariable=self.name_var,
            placeholder_text="Leave empty for auto name",
            fg_color=UI_SURFACE_2,
            text_color=UI_TEXT,
            border_color=UI_BORDER,
        )
        name_entry.grid(row=0, column=1, padx=(0, 14), pady=12, sticky="ew")
        add_entry_context_menu(name_entry)

        ctk.CTkLabel(body, text="Work tools", text_color=UI_TEXT, font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=1, column=0, padx=22, pady=(0, 8), sticky="w"
        )
        grid = ctk.CTkScrollableFrame(body, fg_color="transparent")
        grid.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="nsew")
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1, uniform="tool")

        for index, tool in enumerate(CREATE_TOOLS):
            self.render_tool_card(grid, tool, index)

    def render_tool_card(self, parent, tool, index):
        file_type = tool.get("icon") or tool.get("type", "Other")
        color = FILE_TYPES.get(tool.get("type", "Other"), FILE_TYPES.get("Other", {})).get("color", "#64748b")
        icon = make_file_type_icon(file_type, 38)
        image = ctk.CTkImage(light_image=icon, dark_image=icon, size=(38, 38))
        self.tool_icons[tool.get("name", str(index))] = image

        card = ctk.CTkFrame(
            parent,
            fg_color=UI_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=UI_BORDER,
        )
        card.grid(row=index // 3, column=index % 3, padx=8, pady=8, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="", image=image, width=42).grid(row=0, column=0, padx=(12, 8), pady=(12, 4), sticky="nw")
        ctk.CTkLabel(
            card,
            text=tool.get("name", "New Work"),
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, padx=(0, 12), pady=(14, 0), sticky="ew")
        ctk.CTkLabel(
            card,
            text=tool.get("description", ""),
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
            wraplength=190,
        ).grid(row=1, column=1, padx=(0, 12), pady=(0, 8), sticky="ew")
        ctk.CTkButton(
            card,
            text="Create + Open",
            height=30,
            corner_radius=9,
            fg_color=color,
            hover_color=adjust_color(color, -22),
            text_color=best_text_color(color),
            command=lambda selected=tool: self.create_selected_tool(selected),
        ).grid(row=2, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

    def create_selected_tool(self, tool):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = self.name_var.get().strip() or tool_default_name(tool, timestamp)
        if self.master_app.create_new_work(tool, name):
            self.destroy()


class TemplateFileForm(ctk.CTkToplevel):
    def __init__(self, master, on_save_many):
        refresh_theme_globals()
        super().__init__(master)
        self.title("Add file templates")
        center_toplevel(self, master, 560, 440)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_save_many = on_save_many
        self.paths = []

        theme = form_theme()
        self.configure(fg_color=UI_BG)
        self.grid_columnconfigure(0, weight=1)
        body = ctk.CTkFrame(self, fg_color=theme["body"], corner_radius=14, border_width=1, border_color=theme["border"])
        body.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Add file templates",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(18, 10), sticky="w")

        self.name_var = ctk.StringVar(value="")
        self.type_var = ctk.StringVar(value="Auto detect")
        self.path_var = ctk.StringVar(value="")
        self.setting_type_programmatically = False

        ctk.CTkLabel(body, text="Template name", text_color=theme["label"]).grid(
            row=1, column=0, padx=18, pady=(10, 4), sticky="w"
        )
        self.name_entry = ctk.CTkEntry(
            body,
            textvariable=self.name_var,
            fg_color=theme["field"],
            text_color=theme["text"],
            border_color=theme["border_soft"],
            placeholder_text="Used when one file is selected",
        )
        self.name_entry.grid(row=2, column=0, padx=18, sticky="ew")
        add_entry_context_menu(self.name_entry)

        ctk.CTkLabel(body, text="File type", text_color=theme["label"]).grid(
            row=3, column=0, padx=18, pady=(12, 4), sticky="w"
        )
        ctk.CTkOptionMenu(
            body,
            values=["Auto detect", *FILE_TYPES.keys()],
            variable=self.type_var,
            command=self.mark_type_choice,
            fg_color=theme["field"],
            button_color=theme["neutral"],
            button_hover_color=theme["neutral_hover"],
            text_color=theme["text"],
        ).grid(row=4, column=0, padx=18, sticky="ew")

        ctk.CTkLabel(body, text="Local file path", text_color=theme["label"]).grid(
            row=5, column=0, padx=18, pady=(14, 4), sticky="w"
        )
        path_row = ctk.CTkFrame(body, fg_color="transparent")
        path_row.grid(row=6, column=0, padx=18, sticky="ew")
        path_row.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(
            path_row,
            textvariable=self.path_var,
            fg_color=theme["field"],
            text_color=theme["text"],
            border_color=theme["border_soft"],
        )
        self.path_entry.grid(row=0, column=0, sticky="ew")
        add_entry_context_menu(self.path_entry)
        ctk.CTkButton(path_row, text="Browse", width=90, command=self.browse_files).grid(
            row=0, column=1, padx=(8, 0)
        )

        self.hint_label = ctk.CTkLabel(
            body,
            text="Select one or many files. Multiple files will be named and categorized automatically.",
            text_color=UI_MUTED,
            anchor="w",
            justify="left",
        )
        self.hint_label.grid(row=7, column=0, padx=18, pady=(10, 0), sticky="ew")

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=8, column=0, padx=18, pady=18, sticky="e")
        ctk.CTkButton(
            buttons,
            text="Cancel",
            fg_color=theme["neutral"],
            hover_color=theme["neutral_hover"],
            text_color=theme["neutral_text"],
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(buttons, text="Save", command=self.save).grid(row=0, column=1)
        self.path_var.trace_add("write", self.auto_detect_typed_path)
        self.after(80, lambda: focus_and_select(self.path_entry))

    def mark_type_choice(self, *_):
        if self.setting_type_programmatically:
            return

    def browse_files(self):
        paths = filedialog.askopenfilenames(title="Select template files")
        if not paths:
            return
        self.paths = list(paths)
        if len(self.paths) == 1:
            file_path = Path(self.paths[0])
            self.path_var.set(str(file_path))
            if not self.name_var.get().strip():
                self.name_var.set(file_path.stem)
            self.set_template_type_auto(infer_type_from_target(str(file_path)))
            self.hint_label.configure(text="One file selected. You can edit the name and type before saving.")
        else:
            self.path_var.set(f"{len(self.paths)} files selected")
            self.name_var.set("")
            self.type_var.set("Auto detect")
            self.hint_label.configure(text=f"{len(self.paths)} files selected. Names and types will be detected automatically.")

    def set_template_type_auto(self, file_type: str):
        if not file_type or file_type == "Other":
            return
        self.setting_type_programmatically = True
        self.type_var.set(file_type)
        self.setting_type_programmatically = False

    def auto_detect_typed_path(self, *_):
        if self.paths:
            return
        path = self.path_var.get().strip().strip('"')
        if not path or path.endswith("files selected"):
            return
        file_path = Path(path)
        if file_path.suffix and not self.name_var.get().strip():
            self.name_var.set(file_path.stem)
        if self.type_var.get() == "Auto detect":
            self.set_template_type_auto(infer_type_from_target(path))

    def save(self):
        typed_path = self.path_var.get().strip()
        if not self.paths and typed_path and typed_path != "0 files selected":
            self.paths = [typed_path]
        if not self.paths:
            messagebox.showwarning("Missing file", "Please choose one or more template files.")
            return

        selected_type = self.type_var.get()
        templates = []
        for path in self.paths:
            file_path = Path(path)
            file_type = infer_type_from_target(path) if selected_type == "Auto detect" else selected_type
            name = self.name_var.get().strip() if len(self.paths) == 1 else ""
            templates.append(
                {
                    "id": str(uuid.uuid4()),
                    "name": name or file_path.stem,
                    "type": file_type,
                    "link": str(file_path),
                    "target_kind": "file",
                    "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )
        self.on_save_many(templates)
        self.destroy()


class ColorPickerWindow(ctk.CTkToplevel):
    PALETTE = [
        ("Blue", "#2563eb"), ("Sky", "#0284c7"), ("Cyan", "#06b6d4"), ("Teal", "#0d9488"),
        ("Green", "#16a34a"), ("Lime", "#65a30d"), ("Yellow", "#ca8a04"), ("Amber", "#d97706"),
        ("Orange", "#ea580c"), ("Red", "#dc2626"), ("Rose", "#e11d48"), ("Pink", "#db2777"),
        ("Purple", "#9333ea"), ("Violet", "#7c3aed"), ("Indigo", "#4f46e5"), ("Slate", "#334155"),
        ("Gray", "#64748b"), ("Zinc", "#52525b"), ("Neutral", "#404040"), ("Dark", "#0f172a"),
    ]

    def __init__(self, master, initial_color, on_pick):
        refresh_theme_globals()
        super().__init__(master)
        self.title("Pick color")
        center_toplevel(self, master, 430, 390)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=UI_BG)
        self.on_pick = on_pick
        self.color_var = ctk.StringVar(value=normalize_hex_color(initial_color))
        theme = form_theme()

        self.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self, fg_color=UI_NAV, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Choose Category Color",
            text_color=UI_NAV_TEXT,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        ctk.CTkLabel(
            header,
            text="Use a clean work color or enter a hex value.",
            text_color=UI_MUTED if UI_NAV == UI_SURFACE else "#cbd5e1",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=18, pady=(0, 14), sticky="w")

        body = ctk.CTkFrame(self, fg_color=theme["body"], corner_radius=12, border_width=1, border_color=theme["border"])
        body.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        preview_row = ctk.CTkFrame(body, fg_color="transparent")
        preview_row.grid(row=0, column=0, padx=14, pady=(14, 10), sticky="ew")
        preview_row.grid_columnconfigure(1, weight=1)
        self.preview = ctk.CTkFrame(preview_row, fg_color=self.color_var.get(), width=58, height=34, corner_radius=8)
        self.preview.grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.hex_entry = ctk.CTkEntry(preview_row, textvariable=self.color_var, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        self.hex_entry.grid(row=0, column=1, sticky="ew")
        add_entry_context_menu(self.hex_entry)
        self.color_var.trace_add("write", self.update_preview)

        palette = ctk.CTkFrame(body, fg_color="transparent")
        palette.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")
        for index in range(5):
            palette.grid_columnconfigure(index, weight=1, uniform="palette")
        for index, (label, color) in enumerate(self.PALETTE):
            button = ctk.CTkButton(
                palette,
                text=label,
                height=36,
                fg_color=color,
                hover_color=blend_color(color, "#000000", 0.18),
                text_color="#ffffff" if color not in ("#ca8a04", "#65a30d") else "#111827",
                command=lambda color=color: self.color_var.set(color),
            )
            button.grid(row=index // 5, column=index % 5, padx=3, pady=3, sticky="ew")

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=2, column=0, padx=14, pady=(4, 14), sticky="ew")
        actions.grid_columnconfigure((0, 1), weight=1, uniform="actions")
        ctk.CTkButton(
            actions,
            text="Cancel",
            fg_color=theme["neutral"],
            hover_color=theme["neutral_hover"],
            text_color=theme["neutral_text"],
            command=self.destroy,
        ).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(
            actions,
            text="Use color",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.apply_color,
        ).grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def update_preview(self, *_):
        self.preview.configure(fg_color=normalize_hex_color(self.color_var.get()))

    def apply_color(self):
        color = normalize_hex_color(self.color_var.get())
        self.on_pick(color)
        self.destroy()







class TemplateWindow(ctk.CTkToplevel):
    def __init__(self, master):
        refresh_theme_globals()
        super().__init__(master)
        self.master_app = master
        self.expanded_groups = {}
        self.group_bodies = {}
        self.group_buttons = {}
        self.title("Templates")
        center_toplevel(self, master, 900, 680)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=UI_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=UI_SURFACE, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Templates",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=14, sticky="w")
        ctk.CTkButton(header, text="+ File template", command=self.add_file_template, width=130).grid(
            row=0, column=1, padx=(0, 8), pady=12
        )
        ctk.CTkButton(
            header,
            text="+ Link template",
            command=self.add_link_template,
            width=130,
            fg_color="#14b8a6",
            text_color="#ffffff",
        ).grid(row=0, column=2, padx=(0, 18), pady=12)

        self.body = ctk.CTkScrollableFrame(self, fg_color=UI_BG)
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=14)
        self.body.grid_columnconfigure(0, weight=1)
        self.refresh()

    def refresh(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.group_bodies.clear()
        self.group_buttons.clear()
        self.master_app.template_store.sync_from_template_folders()
        row = 0
        visible_types = [file_type for file_type in FILE_TYPES if any(t.get("type") == file_type for t in self.master_app.template_store.templates)]
        if not visible_types:
            ctk.CTkLabel(self.body, text="No templates yet", text_color=UI_MUTED).grid(
                row=0, column=0, padx=12, pady=20, sticky="w"
            )
            return

        for file_type in visible_types:
            templates = [t for t in self.master_app.template_store.templates if t.get("type") == file_type]
            self.render_template_group(file_type, templates, row)
            row += 1

    def toggle_group(self, file_type):
        expanded = not self.expanded_groups.get(file_type, False)
        self.expanded_groups[file_type] = expanded
        button = self.group_buttons.get(file_type)
        body = self.group_bodies.get(file_type)
        if button:
            button.configure(text="Collapse" if expanded else "Expand")
        if body:
            if expanded:
                body.grid()
            else:
                body.grid_remove()

    def render_template_group(self, file_type, templates, row):
        meta = FILE_TYPES[file_type]
        expanded = self.expanded_groups.get(file_type, False)
        group = ctk.CTkFrame(self.body, fg_color=UI_SURFACE, corner_radius=12, border_width=1, border_color=UI_BORDER)
        group.grid(row=row, column=0, padx=4, pady=6, sticky="ew")
        group.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(group, fg_color="transparent")
        header.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            header,
            text="",
            image=self.master_app.get_type_icon(file_type, 34),
            width=38,
            height=38,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ctk.CTkLabel(
            header,
            text=f"{file_type} ({len(templates)})",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            header,
            text=f"Template folder: Work\\{file_type}\\Template",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=2, padx=12, sticky="e")
        button = ctk.CTkButton(
            header,
            text="Collapse" if expanded else "Expand",
            width=82,
            height=28,
            fg_color=UI_SURFACE_2,
            hover_color=UI_SURFACE_3,
            text_color=UI_TEXT,
            command=lambda file_type=file_type: self.toggle_group(file_type),
        )
        button.grid(row=0, column=3, padx=(8, 0), sticky="e")
        self.group_buttons[file_type] = button

        body = ctk.CTkFrame(group, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew")
        body.grid_columnconfigure(0, weight=1)
        self.group_bodies[file_type] = body

        list_header = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=6)
        list_header.grid(row=0, column=0, padx=10, pady=(0, 4), sticky="ew")
        list_header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(list_header, text="", width=44).grid(row=0, column=0, padx=(8, 4), pady=5)
        ctk.CTkLabel(
            list_header,
            text="Template name",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=1, pady=5, sticky="w")
        ctk.CTkLabel(
            list_header,
            text="Action",
            width=142,
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=2, padx=(0, 8), pady=5)

        for index, template in enumerate(templates, start=1):
            self.render_template_row(body, template, index)

        if not expanded:
            body.grid_remove()

    def render_template_row(self, parent, template, row):
        meta = FILE_TYPES.get(template.get("type"), FILE_TYPES["Other"])
        row_bg = UI_SURFACE if row % 2 else UI_SURFACE_2
        name = template.get("name", "Untitled")
        display_name = name if len(name) <= 70 else f"{name[:67]}..."
        target = template.get("link", "")
        target_kind = "Link" if template.get("target_kind") == "url" or is_url(target) else "File"

        item = ctk.CTkFrame(parent, fg_color=row_bg, corner_radius=8, border_width=1, border_color=UI_BORDER_SOFT, height=64)
        item.grid(row=row, column=0, padx=10, pady=1, sticky="ew")
        item.grid_propagate(False)

        ctk.CTkFrame(item, fg_color=meta["color"], width=4, height=48, corner_radius=2).place(x=0, y=8)
        icon_label = ctk.CTkLabel(
            item,
            text="",
            image=self.master_app.get_task_icon(template),
            width=42,
            height=42,
            corner_radius=8,
            fg_color=UI_SURFACE_2,
        )
        icon_label.place(x=14, y=11)
        title_label = ctk.CTkLabel(
            item,
            text=display_name,
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
            height=20,
        )
        title_label.place(x=68, y=12, relwidth=0.70)
        meta_label = ctk.CTkLabel(
            item,
            text=f"{template.get('type', 'Other')} | {target_kind} | {template.get('date_added', '-')[:10]}",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=10),
            anchor="w",
            height=18,
        )
        meta_label.place(x=68, y=34, relwidth=0.70)
        for hover_widget in (item, icon_label, title_label, meta_label):
            hover_widget.bind("<Button-1>", lambda _e, template=template: self.open_template_detail(template))
            hover_widget.bind(
                "<Enter>",
                lambda _e, w=item, c=meta["color"], bg=row_bg: w.configure(
                    fg_color=blend_color(c, bg, 0.90),
                    border_color=c,
                ),
            )
            hover_widget.bind(
                "<Leave>",
                lambda _e, w=item, bg=row_bg: w.configure(fg_color=bg, border_color=UI_BORDER_SOFT),
            )
        ctk.CTkButton(
            item,
            text="Open",
            width=56,
            height=28,
            fg_color="#eff6ff",
            hover_color="#dbeafe",
            text_color="#1d4ed8",
            command=lambda template=template: self.master_app.open_target(template),
        ).place(relx=1, x=-124, y=18)
        ctk.CTkButton(
            item,
            text="View",
            width=56,
            height=28,
            fg_color=UI_SURFACE_2,
            hover_color="#e2e8f0",
            text_color="#334155",
            command=lambda template=template: self.open_template_detail(template),
        ).place(relx=1, x=-62, y=18)

    def add_file_template(self):
        TemplateFileForm(self, self._save_file_templates)

    def _save_file_templates(self, templates):
        for template in templates:
            template["id"] = template.get("id", str(uuid.uuid4()))
            template["target_kind"] = "file"
            template.pop("status", None)
            template.pop("done_date", None)
            self.master_app.save_template(template)
        self.refresh()

    def add_link_template(self):
        LinkForm(self, lambda template: self._save_link_template(template))

    def _save_link_template(self, template):
        template["id"] = template.get("id", str(uuid.uuid4()))
        template["target_kind"] = "url"
        template.pop("status", None)
        template.pop("done_date", None)
        self.master_app.save_template(template)
        self.refresh()

    def open_template_detail(self, template):
        TemplateDetailWindow(self, template.copy())

    def edit_template(self, template):
        target = template.get("link", "")
        if template.get("target_kind") == "url" or is_url(target):
            LinkForm(self, lambda edited: self._save_edited_template(template, edited), task=template.copy())
        else:
            mode = "folder" if template.get("target_kind") == "folder" else "file"
            TaskForm(self, lambda edited: self._save_edited_template(template, edited), task=template.copy(), mode=mode)

    def _save_edited_template(self, original, edited):
        edited["id"] = original.get("id", edited.get("id", str(uuid.uuid4())))
        edited["target_kind"] = "url" if is_url(edited.get("link", "")) else edited.get("target_kind", original.get("target_kind", "file"))
        edited["shortcut_path"] = original.get("shortcut_path")
        edited.pop("status", None)
        edited.pop("done_date", None)
        self.master_app.save_template(edited)
        self.refresh()

    def delete_template(self, template):
        name = template.get("name", "Untitled")
        if not messagebox.askyesno("Delete template", f"Delete template '{name}'?\n\nTemplate files inside the Template folder will also be removed."):
            return False
        target = self.master_app.item_path_for_actions(template)
        try:
            if target and not is_url(target):
                path = Path(target)
                canonical = is_canonical_template_path(str(path), template.get("type", "Other"))
                if canonical and path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
        except Exception as exc:
            messagebox.showerror("Cannot delete template file", f"The template record was not removed because the file could not be deleted.\n\n{exc}")
            return False
        self.master_app.template_store.delete(template["id"])
        self.refresh()
        return True


class TemplateDetailWindow(ctk.CTkToplevel):
    def __init__(self, master, template):
        refresh_theme_globals()
        super().__init__(master)
        self.template_window = master
        self.master_app = master.master_app
        self.template = template
        self.title("Template detail")
        center_toplevel(self, master, 620, 470)
        self.minsize(560, 420)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=UI_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        meta = FILE_TYPES.get(template.get("type"), FILE_TYPES["Other"])
        target = template.get("link", "")
        target_kind = "Link" if template.get("target_kind") == "url" or is_url(target) else template.get("target_kind", "file").title()

        body = ctk.CTkFrame(self, fg_color=UI_SURFACE, corner_radius=16, border_width=1, border_color=UI_BORDER)
        body.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(body, fg_color="transparent")
        info.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="ew")
        info.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(info, text="", image=self.master_app.get_task_icon(template), width=58, height=58, corner_radius=14, fg_color=blend_color(meta["color"], UI_SURFACE, 0.88)).grid(row=0, column=0, rowspan=2, padx=(0, 14), sticky="nw")
        ctk.CTkLabel(info, text=template.get("name", "Untitled"), text_color=UI_TEXT, font=ctk.CTkFont(size=20, weight="bold"), anchor="w", justify="left", wraplength=470).grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(info, text=f"{template.get('type', 'Other')}  |  {target_kind}  |  Added {template.get('date_added', '-')[:10]}", text_color=UI_MUTED, anchor="w").grid(row=1, column=1, pady=(5, 0), sticky="ew")

        target_section = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=12, border_width=1, border_color=UI_BORDER_SOFT)
        target_section.grid(row=1, column=0, padx=18, pady=(0, 10), sticky="ew")
        target_section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(target_section, text="Template target", text_color=UI_MUTED, font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=12, pady=(9, 2), sticky="w")
        target_box = ctk.CTkTextbox(target_section, height=72, fg_color=UI_SURFACE, text_color=UI_TEXT, border_width=1, border_color=UI_BORDER_SOFT)
        target_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        target_box.insert("1.0", target or "-")
        target_box.configure(state="disabled")

        note_section = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=12, border_width=1, border_color=UI_BORDER_SOFT)
        note_section.grid(row=2, column=0, padx=18, pady=(0, 10), sticky="ew")
        note_section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(note_section, text="Note", text_color=UI_MUTED, font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=12, pady=(9, 2), sticky="w")
        note_box = ctk.CTkTextbox(note_section, height=82, fg_color=UI_SURFACE, text_color=UI_TEXT, border_width=1, border_color=UI_BORDER_SOFT)
        note_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        note_box.insert("1.0", template.get("note", "").strip() or "No note")
        note_box.configure(state="disabled")

        action_section = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=12, border_width=1, border_color=UI_BORDER_SOFT)
        action_section.grid(row=3, column=0, padx=18, pady=(0, 18), sticky="ew")
        action_section.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="template_actions")
        ctk.CTkButton(action_section, text="Open", height=32, fg_color=DETAIL_BUTTONS["open"][0], hover_color=DETAIL_BUTTONS["open"][1], text_color="#ffffff", command=lambda: self.master_app.open_target(template)).grid(row=0, column=0, padx=(12, 4), pady=12, sticky="ew")
        ctk.CTkButton(action_section, text="Edit", height=32, fg_color=DETAIL_BUTTONS["edit"][0], hover_color=DETAIL_BUTTONS["edit"][1], text_color="#ffffff", command=self.edit_and_close).grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        ctk.CTkButton(action_section, text="Copy", height=32, fg_color="#0e7490", hover_color="#155e75", text_color="#ffffff", command=lambda: self.master_app.copy_item_path(template)).grid(row=0, column=2, padx=4, pady=12, sticky="ew")
        ctk.CTkButton(action_section, text="Folder", height=32, fg_color=DETAIL_BUTTONS["folder"][0], hover_color=DETAIL_BUTTONS["folder"][1], text_color="#ffffff", command=lambda: self.master_app.open_item_folder(template)).grid(row=0, column=3, padx=4, pady=12, sticky="ew")
        ctk.CTkButton(action_section, text="Delete", height=32, fg_color="#fee2e2", hover_color="#fecaca", text_color="#b91c1c", command=self.delete_and_close).grid(row=0, column=4, padx=(4, 12), pady=12, sticky="ew")

    def edit_and_close(self):
        self.destroy()
        self.template_window.edit_template(self.template)

    def delete_and_close(self):
        if self.template_window.delete_template(self.template):
            self.destroy()


class TaskDetailWindow(ctk.CTkToplevel):
    def __init__(self, master, task):
        refresh_theme_globals()
        super().__init__(master)
        self.master_app = master
        self.task = task
        self.title("Task detail")
        center_toplevel(self, master, 620, 520)
        self.minsize(560, 460)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=UI_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        meta = FILE_TYPES.get(task.get("type"), FILE_TYPES["Other"])
        status_meta = STATUS_META.get(task.get("status", STATUS_PENDING), STATUS_META[STATUS_PENDING])

        body = ctk.CTkFrame(self, fg_color=UI_SURFACE, corner_radius=16, border_width=1, border_color=UI_BORDER)
        body.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(body, fg_color="transparent")
        info.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="ew")
        info.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(info, text="", image=master.get_task_icon(task), width=56, height=56, corner_radius=14, fg_color=UI_SURFACE_2).grid(row=0, column=0, rowspan=2, padx=(0, 14), sticky="nw")
        ctk.CTkLabel(info, text=task.get("name", "Untitled"), text_color=UI_TEXT, font=ctk.CTkFont(size=20, weight="bold"), anchor="w", justify="left", wraplength=470).grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(info, text=f"{task.get('type', 'Other')}  |  {task.get('project_stack') or task.get('target_kind', 'file').title()}  |  Added {task.get('date_added', '-')[:10]}", text_color=UI_MUTED, anchor="w").grid(row=1, column=1, pady=(5, 0), sticky="ew")

        target_section = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=12, border_width=1, border_color=UI_BORDER_SOFT)
        target_section.grid(row=1, column=0, padx=18, pady=(0, 10), sticky="ew")
        target_section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(target_section, text="Target", text_color=UI_MUTED, font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=12, pady=(9, 2), sticky="w")
        target_box = ctk.CTkTextbox(target_section, height=58, fg_color=UI_SURFACE, text_color=UI_TEXT, border_width=1, border_color=UI_BORDER_SOFT)
        target_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        target_box.insert("1.0", task.get("link", "") or "-")
        target_box.configure(state="disabled")

        note_section = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=12, border_width=1, border_color=UI_BORDER_SOFT)
        note_section.grid(row=2, column=0, padx=18, pady=(0, 10), sticky="ew")
        note_section.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(note_section, text="Note", text_color=UI_MUTED, font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=12, pady=(9, 2), sticky="w")
        note_box = ctk.CTkTextbox(note_section, height=82, fg_color=UI_SURFACE, text_color=UI_TEXT, border_width=1, border_color=UI_BORDER_SOFT)
        note_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        note_box.insert("1.0", task.get("note", "").strip() or "No note")
        note_box.configure(state="disabled")

        status_section = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=12, border_width=1, border_color=UI_BORDER_SOFT)
        status_section.grid(row=3, column=0, padx=18, pady=(0, 10), sticky="ew")
        status_section.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(status_section, text=status_meta["folder"].upper(), width=100, height=28, corner_radius=14, fg_color=status_meta["bg"], text_color=status_meta["color"], font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=12, pady=10, sticky="w")
        status_row = ctk.CTkFrame(status_section, fg_color="transparent")
        status_row.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")
        for index in range(3):
            status_row.grid_columnconfigure(index, weight=1, uniform="detail_status")
        current_status = task.get("status", STATUS_PENDING)
        for index, (target_status, label) in enumerate(STATUSES):
            target_meta = STATUS_META[target_status]
            is_current = current_status == target_status
            active_bg = target_meta["color"]
            current_bg = blend_color(target_meta["color"], UI_SURFACE, 0.78)
            ctk.CTkButton(status_row, text=label, height=30, fg_color=current_bg if is_current else active_bg, hover_color=active_bg, text_color=target_meta["color"] if is_current else "#ffffff", command=(lambda: None) if is_current else (lambda target_status=target_status: self.move_and_close(target_status))).grid(row=0, column=index, padx=3, sticky="ew")

        action_section = ctk.CTkFrame(body, fg_color=UI_SURFACE_2, corner_radius=12, border_width=1, border_color=UI_BORDER_SOFT)
        action_section.grid(row=4, column=0, padx=18, pady=(0, 18), sticky="ew")
        action_section.grid_columnconfigure((0, 1), weight=1, uniform="task_actions")
        action_section.grid_columnconfigure((2, 3, 4), weight=1, uniform="task_actions")
        open_label = "Open link" if task.get("target_kind") == "url" or is_url(task.get("link", "")) else "Open file"
        ctk.CTkButton(action_section, text=open_label, height=32, fg_color=DETAIL_BUTTONS["open"][0], hover_color=DETAIL_BUTTONS["open"][1], text_color="#ffffff", command=lambda task=task: self.master_app.open_target(task)).grid(row=0, column=0, padx=(12, 4), pady=12, sticky="ew")
        ctk.CTkButton(action_section, text="Edit", height=32, fg_color=DETAIL_BUTTONS["edit"][0], hover_color=DETAIL_BUTTONS["edit"][1], text_color="#ffffff", command=self.edit_and_close).grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        ctk.CTkButton(action_section, text="Copy", height=32, fg_color="#0e7490", hover_color="#155e75", text_color="#ffffff", command=lambda task=task: self.copy_current(task)).grid(row=0, column=2, padx=4, pady=12, sticky="ew")
        ctk.CTkButton(action_section, text="Folder", height=32, fg_color=DETAIL_BUTTONS["folder"][0], hover_color=DETAIL_BUTTONS["folder"][1], text_color="#ffffff", command=lambda task=task: self.master_app.open_item_folder(task)).grid(row=0, column=3, padx=4, pady=12, sticky="ew")
        can_delete = task.get("status") == STATUS_DONE
        ctk.CTkButton(action_section, text="Delete" if can_delete else "No delete", height=32, fg_color="#fee2e2" if can_delete else UI_SURFACE, hover_color="#fecaca" if can_delete else UI_BORDER_SOFT, text_color="#b91c1c" if can_delete else UI_MUTED, state="normal" if can_delete else "disabled", command=self.delete_and_close).grid(row=0, column=4, padx=(4, 12), pady=12, sticky="ew")

    def move_and_close(self, target_status):
        self.master_app.set_task_status(self.task, target_status)
        self.destroy()

    def copy_current(self, task):
        if task.get("target_kind") == "url" or is_url(task.get("link", "")):
            self.master_app.copy_item_path(task)
        else:
            self.master_app.copy_item_file(task)

    def delete_and_close(self):
        if self.master_app.delete_task(self.task):
            self.destroy()

    def edit_and_close(self):
        self.destroy()
        self.master_app.edit_task(self.task)


