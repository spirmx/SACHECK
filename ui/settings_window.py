import os
import shutil
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from core.app_paths import app_folder
from core.app_settings import (
    add_settings_log,
    clear_settings_log,
    is_startup_enabled,
    read_settings_log,
    save_app_settings,
    set_startup_enabled,
)
import sacheck_runtime as app_runtime
from sacheck_runtime import (
    CATEGORY_ICON_DIR, EXTENSION_TYPES, FILE_TYPES, UI_BG, UI_BORDER,
    UI_BORDER_SOFT, UI_MUTED, UI_NAV, UI_NAV_TEXT, UI_SURFACE, UI_SURFACE_2,
    UI_TEXT, URL_RULES, add_entry_context_menu,
    apply_category_settings, ensure_status_folders,
    form_theme, is_valid_category_name, move_category_files,
    normalize_hex_color, save_category_config, unique_destination,
)


def sync_runtime_globals():
    global CATEGORY_ICON_DIR, EXTENSION_TYPES, FILE_TYPES, UI_BG, UI_BORDER
    global UI_BORDER_SOFT, UI_MUTED, UI_NAV, UI_NAV_TEXT, UI_SURFACE
    global UI_SURFACE_2, UI_TEXT, URL_RULES
    CATEGORY_ICON_DIR = app_runtime.CATEGORY_ICON_DIR
    EXTENSION_TYPES = app_runtime.EXTENSION_TYPES
    FILE_TYPES = app_runtime.FILE_TYPES
    UI_BG = app_runtime.UI_BG
    UI_BORDER = app_runtime.UI_BORDER
    UI_BORDER_SOFT = app_runtime.UI_BORDER_SOFT
    UI_MUTED = app_runtime.UI_MUTED
    UI_NAV = app_runtime.UI_NAV
    UI_NAV_TEXT = app_runtime.UI_NAV_TEXT
    UI_SURFACE = app_runtime.UI_SURFACE
    UI_SURFACE_2 = app_runtime.UI_SURFACE_2
    UI_TEXT = app_runtime.UI_TEXT
    URL_RULES = app_runtime.URL_RULES


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        sync_runtime_globals()
        super().__init__(master)
        self.master_app = master
        self.title("Settings")
        self.geometry("980x740")
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=UI_BG)
        self.editing_category = None
        self.icon_preview_image = None
        self.icon_text_manual = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=UI_NAV, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="SACHECK Settings",
            text_color=UI_NAV_TEXT,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        ctk.CTkLabel(
            header,
            text="Theme, category rules, realtime scan, folder structure, icon assets, and activity log",
            text_color="#cbd5e1",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=18, pady=(0, 14), sticky="w")
        ctk.CTkButton(
            header,
            text="Reload + Rescan",
            width=140,
            fg_color="#22c55e",
            hover_color="#16a34a",
            command=self.reload_and_rescan,
        ).grid(row=0, column=1, rowspan=2, padx=(0, 10), pady=16)
        ctk.CTkButton(
            header,
            text="Open category.py",
            width=140,
            fg_color="#334155",
            hover_color="#1e293b",
            command=self.open_category_file,
        ).grid(row=0, column=2, rowspan=2, padx=(0, 18), pady=16)

        self.body = ctk.CTkScrollableFrame(self, fg_color=UI_BG)
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=14)
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_columnconfigure(1, weight=1)

        self.build_quick_tools()
        self.build_category_form()
        self.build_category_list()
        self.build_log_panel()

    def build_quick_tools(self):
        panel = ctk.CTkFrame(self.body, fg_color=UI_SURFACE, corner_radius=12, border_width=1, border_color=UI_BORDER)
        panel.grid(row=0, column=0, columnspan=2, padx=4, pady=(0, 10), sticky="ew")
        for index in range(4):
            panel.grid_columnconfigure(index, weight=1)
        tools = [
            ("Reload rules", "Read category.py again", self.reload_rules),
            ("Rescan folders", "Read Work folders now", self.rescan_folders),
            ("Open icon folder", "assets/category_icons", self.open_icon_folder),
            ("Create folders", "Ensure category folders", self.create_folders),
        ]
        for index, (title, subtitle, command) in enumerate(tools):
            button = ctk.CTkButton(
                panel,
                text=f"{title}\n{subtitle}",
                height=58,
                fg_color=UI_SURFACE_2,
                hover_color=UI_BORDER_SOFT,
                border_width=1,
                border_color=UI_BORDER_SOFT,
                text_color=UI_TEXT,
                font=ctk.CTkFont(size=12, weight="bold"),
                command=command,
            )
            button.grid(row=0, column=index, padx=8, pady=8, sticky="ew")

        theme_row = ctk.CTkFrame(panel, fg_color="transparent")
        theme_row.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="ew")
        theme_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            theme_row,
            text="Appearance",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=(4, 12), sticky="w")
        self.theme_var = ctk.StringVar(value=self.master_app.theme_name)
        ctk.CTkSegmentedButton(
            theme_row,
            values=["Light", "Dark"],
            variable=self.theme_var,
            command=self.change_theme,
            selected_color="#2563eb",
            selected_hover_color="#1d4ed8",
            unselected_color=UI_SURFACE_2,
            unselected_hover_color=UI_BORDER_SOFT,
            text_color=UI_TEXT,
        ).grid(row=0, column=1, sticky="ew")

        startup_row = ctk.CTkFrame(panel, fg_color=UI_SURFACE_2, corner_radius=10, border_width=1, border_color=UI_BORDER_SOFT)
        startup_row.grid(row=2, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="ew")
        startup_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            startup_row,
            text="Launch SACHECK when Windows starts",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(9, 1), sticky="w")
        ctk.CTkLabel(
            startup_row,
            text="Uses the current installed app path. You can turn it off any time.",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, padx=12, pady=(0, 9), sticky="w")
        self.startup_var = ctk.BooleanVar(value=is_startup_enabled())
        ctk.CTkSwitch(
            startup_row,
            text="Auto Run",
            variable=self.startup_var,
            command=self.change_startup,
            progress_color="#22c55e",
            button_color="#ffffff",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=1, rowspan=2, padx=12, pady=10, sticky="e")

    def change_startup(self):
        enabled = bool(self.startup_var.get())
        try:
            set_startup_enabled(enabled)
            self.master_app.app_settings["launch_on_startup"] = enabled
            save_app_settings(self.master_app.app_settings)
            add_settings_log("Startup", "Enabled Auto Run" if enabled else "Disabled Auto Run")
        except Exception as exc:
            self.startup_var.set(not enabled)
            messagebox.showerror("Startup setting", f"Could not update Windows startup:\n{exc}")

    def build_category_form(self):
        theme = form_theme()
        self.form = ctk.CTkFrame(self.body, fg_color=UI_SURFACE, corner_radius=12, border_width=1, border_color=UI_BORDER)
        form = self.form
        form.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)
        self.form_title = ctk.CTkLabel(form, text="Add category", text_color=UI_TEXT, font=ctk.CTkFont(size=18, weight="bold"))
        self.form_title.grid(
            row=0, column=0, padx=14, pady=(14, 4), sticky="w"
        )
        ctk.CTkLabel(
            form,
            text="Example: Policy, Flow, Claim. Extensions can be .abc,.xyz. URL keywords match domains or link text.",
            text_color=UI_MUTED,
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, padx=14, pady=(0, 10), sticky="w")

        self.cat_name_var = ctk.StringVar()
        self.cat_color_var = ctk.StringVar(value="#2563eb")
        self.cat_icon_var = ctk.StringVar(value="N")
        self.cat_icon_file_var = ctk.StringVar(value="")
        self.cat_extensions_var = ctk.StringVar(value="")
        self.cat_url_keywords_var = ctk.StringVar(value="")

        self._settings_entry(form, "Category name", self.cat_name_var, 2)

        ctk.CTkLabel(form, text="Color", text_color=UI_MUTED).grid(row=4, column=0, padx=14, pady=(8, 3), sticky="w")
        color_row = ctk.CTkFrame(form, fg_color="transparent")
        color_row.grid(row=5, column=0, padx=14, sticky="ew")
        color_row.grid_columnconfigure(0, weight=1)
        self.color_entry = ctk.CTkEntry(color_row, textvariable=self.cat_color_var, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        self.color_entry.grid(row=0, column=0, sticky="ew")
        add_entry_context_menu(self.color_entry)
        self.color_preview = ctk.CTkFrame(color_row, fg_color="#2563eb", width=36, height=28, corner_radius=7)
        self.color_preview.grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(
            color_row,
            text="Choose",
            width=84,
            fg_color=theme["neutral"],
            hover_color=theme["neutral_hover"],
            text_color=theme["neutral_text"],
            command=self.pick_color,
        ).grid(row=0, column=2, padx=(8, 0))

        self.icon_text_label = ctk.CTkLabel(form, text="Icon text", text_color=UI_MUTED)
        self.icon_text_label.grid(row=6, column=0, padx=14, pady=(8, 3), sticky="w")
        self.icon_text_entry = ctk.CTkEntry(form, textvariable=self.cat_icon_var, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        self.icon_text_entry.grid(row=7, column=0, padx=14, sticky="ew")
        add_entry_context_menu(self.icon_text_entry)
        self.icon_text_entry.bind("<KeyRelease>", self.mark_icon_text_manual)

        ctk.CTkLabel(form, text="Icon image", text_color=UI_MUTED).grid(row=8, column=0, padx=14, pady=(8, 3), sticky="w")
        icon_row = ctk.CTkFrame(form, fg_color="transparent")
        icon_row.grid(row=9, column=0, padx=14, sticky="ew")
        icon_row.grid_columnconfigure(0, weight=1)
        self.icon_file_entry = ctk.CTkEntry(icon_row, textvariable=self.cat_icon_file_var, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        self.icon_file_entry.grid(row=0, column=0, sticky="ew")
        add_entry_context_menu(self.icon_file_entry)
        ctk.CTkButton(icon_row, text="Choose", width=84, command=self.choose_icon_file).grid(row=0, column=1, padx=(8, 0))
        self.icon_preview = ctk.CTkLabel(form, text="No image selected", text_color=UI_MUTED, height=34)
        self.icon_preview.grid(row=10, column=0, padx=14, pady=(6, 0), sticky="w")

        self._settings_entry(form, "Extensions", self.cat_extensions_var, 11)
        self._settings_entry(form, "URL keywords/domains", self.cat_url_keywords_var, 13)
        ctk.CTkButton(
            form,
            text="Save category",
            height=36,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.save_category,
        ).grid(row=15, column=0, padx=14, pady=(14, 8), sticky="ew")
        self.delete_category_button = ctk.CTkButton(
            form,
            text="Delete category",
            height=32,
            fg_color="#fee2e2",
            hover_color="#fecaca",
            text_color="#b91c1c",
            state="disabled",
            command=self.delete_current_category,
        )
        self.delete_category_button.grid(row=16, column=0, padx=14, pady=(0, 8), sticky="ew")
        ctk.CTkButton(
            form,
            text="Clear form",
            height=32,
            fg_color=theme["neutral"],
            hover_color=theme["neutral_hover"],
            text_color=theme["neutral_text"],
            command=self.clear_form,
        ).grid(row=17, column=0, padx=14, pady=(0, 14), sticky="ew")

        self.cat_name_var.trace_add("write", self.auto_icon_text_from_name)
        self.cat_icon_file_var.trace_add("write", self.update_icon_preview)
        self.cat_color_var.trace_add("write", self.update_color_preview)

    def _settings_entry(self, parent, label, variable, row):
        theme = form_theme()
        ctk.CTkLabel(parent, text=label, text_color=theme["label"]).grid(row=row, column=0, padx=14, pady=(8, 3), sticky="w")
        entry = ctk.CTkEntry(parent, textvariable=variable, fg_color=theme["field"], text_color=theme["text"], border_color=theme["border_soft"])
        entry.grid(row=row + 1, column=0, padx=14, sticky="ew")
        add_entry_context_menu(entry)
        return entry

    def auto_icon_text_from_name(self, *_):
        if self.icon_text_manual or self.cat_icon_file_var.get().strip():
            return
        name = self.cat_name_var.get().strip()
        self.cat_icon_var.set((name[:1] or "N").upper())

    def mark_icon_text_manual(self, *_):
        self.icon_text_manual = True

    def pick_color(self):
        _rgb, hex_color = colorchooser.askcolor(color=self.cat_color_var.get() or "#2563eb", parent=self)
        if hex_color:
            self.set_category_color(hex_color)

    def set_category_color(self, color):
        self.cat_color_var.set(normalize_hex_color(color))

    def update_color_preview(self, *_):
        self.color_preview.configure(fg_color=normalize_hex_color(self.cat_color_var.get()))

    def choose_icon_file(self):
        path = filedialog.askopenfilename(
            title="Choose category icon",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.ico"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        source = Path(path)
        icon_folder = app_folder() / CATEGORY_ICON_DIR
        icon_folder.mkdir(parents=True, exist_ok=True)
        destination = icon_folder / source.name
        if source.resolve() != destination.resolve():
            destination = unique_destination(icon_folder, source.name)
            shutil.copy2(str(source), str(destination))
        self.cat_icon_file_var.set(destination.name)

    def update_icon_preview(self, *_):
        icon_file = self.cat_icon_file_var.get().strip()
        icon_path = app_folder() / CATEGORY_ICON_DIR / icon_file if icon_file else None
        if icon_file and icon_path and icon_path.exists():
            self.icon_text_label.grid_remove()
            self.icon_text_entry.grid_remove()
            try:
                image = Image.open(icon_path).convert("RGBA")
                self.icon_preview_image = ctk.CTkImage(light_image=image, dark_image=image, size=(30, 30))
                self.icon_preview.configure(text=f" {icon_file}", image=self.icon_preview_image)
                return
            except Exception:
                pass
        self.icon_text_label.grid()
        self.icon_text_entry.grid()
        self.icon_preview.configure(
            text=f"Image not found: {icon_file}" if icon_file else "No image selected",
            image=None,
        )

    def build_category_list(self):
        self.list_panel = ctk.CTkFrame(self.body, fg_color=UI_SURFACE, corner_radius=12, border_width=1, border_color=UI_BORDER)
        self.list_panel.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")
        self.list_panel.grid_columnconfigure(0, weight=1)
        self.render_category_list()

    def render_category_list(self):
        sync_runtime_globals()
        for child in self.list_panel.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.list_panel,
            text=f"Categories ({len(FILE_TYPES)})",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(14, 8), sticky="w")
        for row, (name, meta) in enumerate(FILE_TYPES.items(), start=1):
            extensions = sorted(ext for ext, file_type in EXTENSION_TYPES.items() if file_type == name)
            card = ctk.CTkFrame(self.list_panel, fg_color=UI_SURFACE_2, corner_radius=9, border_width=1, border_color=UI_BORDER_SOFT)
            card.grid(row=row, column=0, padx=12, pady=4, sticky="ew")
            card.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(card, text="", image=self.master_app.get_type_icon(name, 28), width=34, height=34).grid(
                row=0, column=0, padx=(8, 6), pady=8
            )
            ctk.CTkLabel(card, text=name, text_color=UI_TEXT, font=ctk.CTkFont(size=13, weight="bold")).grid(
                row=0, column=1, padx=(0, 8), pady=(7, 0), sticky="w"
            )
            ctk.CTkButton(
                card,
                text="Edit",
                width=54,
                height=26,
                fg_color="#eff6ff",
                hover_color="#dbeafe",
                text_color="#1d4ed8",
                command=lambda name=name: self.load_category_for_edit(name),
            ).grid(row=0, column=2, rowspan=2, padx=(0, 6), pady=8)
            ctk.CTkButton(
                card,
                text="Delete",
                width=62,
                height=26,
                fg_color="#fee2e2" if name != "Other" else "#f1f5f9",
                hover_color="#fecaca" if name != "Other" else "#e2e8f0",
                text_color="#b91c1c" if name != "Other" else UI_MUTED,
                state="normal" if name != "Other" else "disabled",
                command=lambda name=name: self.delete_category(name),
            ).grid(row=0, column=3, rowspan=2, padx=(0, 8), pady=8)
            ctk.CTkLabel(
                card,
                text=", ".join(extensions[:12]) + (" ..." if len(extensions) > 12 else ""),
                text_color=UI_MUTED,
                font=ctk.CTkFont(size=10),
            ).grid(row=1, column=1, padx=(0, 8), pady=(0, 7), sticky="w")

    def build_log_panel(self):
        self.log_panel = ctk.CTkFrame(self.body, fg_color=UI_SURFACE, corner_radius=12, border_width=1, border_color=UI_BORDER)
        self.log_panel.grid(row=2, column=0, columnspan=2, padx=4, pady=(10, 4), sticky="ew")
        self.log_panel.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self.log_panel, fg_color="transparent")
        header.grid(row=0, column=0, padx=14, pady=(12, 6), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Settings Activity Log",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header,
            text="Clear log",
            width=92,
            height=28,
            fg_color=UI_SURFACE_2,
            hover_color=UI_BORDER_SOFT,
            text_color=UI_TEXT,
            command=self.clear_log,
        ).grid(row=0, column=1, sticky="e")
        self.log_list = ctk.CTkScrollableFrame(self.log_panel, fg_color=UI_SURFACE_2, height=170)
        self.log_list.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="ew")
        self.log_list.grid_columnconfigure(2, weight=1)
        self.render_log()

    def render_log(self):
        for child in self.log_list.winfo_children():
            child.destroy()
        logs = list(reversed(read_settings_log(limit=60)))
        if not logs:
            ctk.CTkLabel(
                self.log_list,
                text="No settings activity yet",
                text_color=UI_MUTED,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).grid(row=0, column=0, padx=12, pady=12, sticky="w")
            return
        badge_colors = {
            "Created": "#16a34a",
            "Updated": "#2563eb",
            "Deleted": "#dc2626",
            "Theme": "#7c3aed",
            "Reload": "#0891b2",
            "Rescan": "#d97706",
            "Folders": "#059669",
        }
        for row, entry in enumerate(logs):
            action = entry.get("action", "Log")
            color = badge_colors.get(action, "#64748b")
            ctk.CTkLabel(
                self.log_list,
                text=entry.get("time", "-"),
                text_color=UI_MUTED,
                font=ctk.CTkFont(size=10),
                width=132,
                anchor="w",
            ).grid(row=row, column=0, padx=(8, 6), pady=4, sticky="w")
            ctk.CTkLabel(
                self.log_list,
                text=action,
                fg_color=color,
                text_color="#ffffff",
                corner_radius=8,
                width=74,
                height=22,
                font=ctk.CTkFont(size=10, weight="bold"),
            ).grid(row=row, column=1, padx=(0, 8), pady=4, sticky="w")
            ctk.CTkLabel(
                self.log_list,
                text=entry.get("detail", ""),
                text_color=UI_TEXT,
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).grid(row=row, column=2, padx=(0, 8), pady=4, sticky="ew")

    def clear_log(self):
        if messagebox.askyesno("Clear log", "Clear all Settings activity log entries?"):
            clear_settings_log()
            self.render_log()

    def change_theme(self, theme_name):
        self.master_app.set_theme(theme_name)
        add_settings_log("Theme", f"Changed appearance to {theme_name}")
        self.destroy()
        self.master_app.after(80, self.master_app.open_settings)

    def load_category_for_edit(self, name):
        sync_runtime_globals()
        meta = FILE_TYPES.get(name, {})
        self.editing_category = name
        self.icon_text_manual = False
        self.form_title.configure(text=f"Edit category: {name}")
        self.delete_category_button.configure(state="normal" if name != "Other" else "disabled")
        self.cat_name_var.set(name)
        self.cat_color_var.set(meta.get("color", "#2563eb"))
        self.cat_icon_var.set(meta.get("icon", name[:1].upper()))
        self.cat_icon_file_var.set(meta.get("icon_file", ""))
        extensions = sorted(ext for ext, file_type in EXTENSION_TYPES.items() if file_type == name)
        self.cat_extensions_var.set(", ".join(extensions))
        keywords = []
        for rule in URL_RULES:
            if rule.get("type") == name:
                for key in ("host_contains", "host", "path_contains"):
                    value = rule.get(key)
                    if value:
                        keywords.append(str(value))
        self.cat_url_keywords_var.set(", ".join(dict.fromkeys(keywords)))

    def save_category(self):
        name = self.cat_name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing category", "Please enter a category name.")
            return
        if not is_valid_category_name(name):
            messagebox.showwarning(
                "Invalid category",
                'Category name cannot contain: < > : " / \\ | ? * and cannot be . or ..',
            )
            return
        color = normalize_hex_color(self.cat_color_var.get())
        self.cat_color_var.set(color)
        icon_text = (self.cat_icon_var.get().strip() or name[:1]).upper()[:4]
        icon_file = self.cat_icon_file_var.get().strip()

        categories = dict(FILE_TYPES)
        extension_types = dict(EXTENSION_TYPES)
        url_rules = [dict(rule) for rule in URL_RULES]
        old_name = self.editing_category
        if old_name and old_name != name:
            categories.pop(old_name, None)
            extension_types = {
                extension: (name if file_type == old_name else file_type)
                for extension, file_type in extension_types.items()
            }
            for rule in url_rules:
                if rule.get("type") == old_name:
                    rule["type"] = name
        categories[name] = {"color": color, "icon": icon_text, "label": name, "icon_file": icon_file}

        extension_types = {
            extension: file_type
            for extension, file_type in extension_types.items()
            if file_type != name
        }
        url_rules = [rule for rule in url_rules if rule.get("type") != name]

        for raw_ext in self.cat_extensions_var.get().split(","):
            ext = raw_ext.strip().lower()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = f".{ext}"
            extension_types[ext] = name

        for keyword in self.cat_url_keywords_var.get().split(","):
            keyword = keyword.strip().lower()
            if keyword:
                url_rules.append({"host_contains": keyword, "type": name})

        save_category_config(categories, extension_types, url_rules)
        apply_category_settings(categories, extension_types, url_rules)
        sync_runtime_globals()
        log_action = "Updated" if old_name else "Created"
        log_detail = f"{old_name} -> {name}" if old_name and old_name != name else name
        if old_name and old_name != name:
            move_category_files(old_name, name)
            self.master_app.store.replace_type(old_name, name)
            self.master_app.template_store.replace_type(old_name, name)
        add_settings_log(log_action, f"Category {log_detail}")
        self.master_app.reload_category_settings(show_message=False)
        self.clear_form()
        self.render_category_list()
        self.render_log()
        messagebox.showinfo("Saved", f"Category '{name}' has been saved and loaded.")

    def delete_current_category(self):
        if self.editing_category:
            self.delete_category(self.editing_category)

    def delete_category(self, name):
        if name == "Other":
            messagebox.showinfo("Protected category", "Other is the fallback category and cannot be deleted.")
            return
        if name not in FILE_TYPES:
            messagebox.showinfo("Not found", f"Category '{name}' is already gone.")
            self.clear_form()
            self.render_category_list()
            return
        if not messagebox.askyesno(
            "Delete category",
            f"Delete category '{name}'?\n\nFiles and items will not be deleted. They will move to Other.",
        ):
            return

        categories = dict(FILE_TYPES)
        extension_types = {
            extension: file_type
            for extension, file_type in EXTENSION_TYPES.items()
            if file_type != name
        }
        url_rules = [dict(rule) for rule in URL_RULES if rule.get("type") != name]
        categories.pop(name, None)

        save_category_config(categories, extension_types, url_rules)
        apply_category_settings(categories, extension_types, url_rules)
        sync_runtime_globals()
        move_category_files(name, "Other")
        self.master_app.store.replace_type(name, "Other")
        self.master_app.template_store.replace_type(name, "Other")
        add_settings_log("Deleted", f"Category {name}; items moved to Other")
        self.master_app.reload_category_settings(show_message=False)
        self.clear_form()
        self.render_category_list()
        self.render_log()
        messagebox.showinfo("Deleted", f"Category '{name}' was deleted. Items moved to Other.")

    def clear_form(self):
        self.editing_category = None
        self.form_title.configure(text="Add category")
        self.delete_category_button.configure(state="disabled")
        self.icon_text_manual = False
        self.cat_name_var.set("")
        self.cat_color_var.set("#2563eb")
        self.cat_icon_var.set("N")
        self.cat_icon_file_var.set("")
        self.cat_extensions_var.set("")
        self.cat_url_keywords_var.set("")

    def reload_rules(self):
        self.master_app.reload_category_settings()
        sync_runtime_globals()
        self.render_category_list()
        add_settings_log("Reload", "Category rules reloaded")
        self.render_log()

    def rescan_folders(self):
        self.master_app.rescan_work_folders()
        add_settings_log("Rescan", "Work and Template folders scanned")
        self.render_log()

    def reload_and_rescan(self):
        self.master_app.reload_category_settings(show_message=False)
        sync_runtime_globals()
        self.master_app.rescan_work_folders(show_message=False)
        self.render_category_list()
        add_settings_log("Reload", "Rules reloaded and folders scanned")
        self.render_log()
        messagebox.showinfo("Reloaded", "Categories were reloaded and Work folders were scanned.")

    def create_folders(self):
        ensure_status_folders()
        add_settings_log("Folders", "Category/status/template folders ensured")
        self.render_log()
        messagebox.showinfo("Folders ready", "Category, status, and template folders are ready.")

    def open_category_file(self):
        path = app_folder() / "config" / "category.py"
        if not path.exists():
            save_category_config()
        os.startfile(str(path))

    def open_icon_folder(self):
        folder = app_folder() / CATEGORY_ICON_DIR
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder))

