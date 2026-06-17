import customtkinter as ctk

import sacheck_runtime as app_runtime


def refresh_theme_globals():
    global UI_BG, UI_BORDER, UI_BORDER_SOFT, UI_MUTED, UI_SURFACE, UI_SURFACE_2, UI_TEXT
    UI_BG = app_runtime.UI_BG
    UI_BORDER = app_runtime.UI_BORDER
    UI_BORDER_SOFT = app_runtime.UI_BORDER_SOFT
    UI_MUTED = app_runtime.UI_MUTED
    UI_SURFACE = app_runtime.UI_SURFACE
    UI_SURFACE_2 = app_runtime.UI_SURFACE_2
    UI_TEXT = app_runtime.UI_TEXT


refresh_theme_globals()


class DiagnosticsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        refresh_theme_globals()
        super().__init__(master)
        self.master_app = master
        self.title("Diagnostics")
        self.geometry("760x620")
        self.minsize(660, 520)
        self.configure(fg_color=UI_BG)
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color=UI_SURFACE, corner_radius=0, border_width=1, border_color=UI_BORDER)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Diagnostics",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(14, 2), sticky="w")
        ctk.CTkLabel(
            header,
            text="Sync, render cache, filters, and recent internal events",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=11),
        ).grid(row=1, column=0, padx=18, pady=(0, 14), sticky="w")
        ctk.CTkButton(
            header,
            text="Refresh",
            width=92,
            height=30,
            command=self.render,
        ).grid(row=0, column=1, rowspan=2, padx=18, pady=14, sticky="e")

        self.body = ctk.CTkScrollableFrame(self, fg_color=UI_BG)
        self.body.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self.body.grid_columnconfigure(0, weight=1)
        self.render()

    def section(self, row, title):
        frame = ctk.CTkFrame(self.body, fg_color=UI_SURFACE, corner_radius=10, border_width=1, border_color=UI_BORDER)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            frame,
            text=title,
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(12, 8), sticky="w")
        return frame

    def kv(self, frame, row, key, value):
        ctk.CTkLabel(frame, text=key, text_color=UI_MUTED, font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=row, column=0, padx=(14, 12), pady=4, sticky="nw"
        )
        ctk.CTkLabel(frame, text=str(value), text_color=UI_TEXT, font=ctk.CTkFont(size=11), anchor="w", justify="left").grid(
            row=row, column=1, padx=(0, 14), pady=4, sticky="ew"
        )

    def render(self):
        for child in self.body.winfo_children():
            child.destroy()

        app = self.master_app
        sync = app.last_sync_info or {}
        overview = self.section(0, "System")
        self.kv(overview, 1, "Tasks", len(app.store.tasks))
        self.kv(overview, 2, "Templates", len(app.template_store.templates))
        self.kv(overview, 3, "Theme", app.theme_name)
        self.kv(overview, 4, "Window", app.geometry())
        self.kv(overview, 5, "Work root", app_runtime.work_root() / "Work")

        sync_frame = self.section(1, "Last Sync")
        self.kv(sync_frame, 1, "Time", sync.get("time", "-"))
        self.kv(sync_frame, 2, "Duration", f"{sync.get('duration_ms', 0)} ms")
        self.kv(sync_frame, 3, "Tasks changed", sync.get("tasks_changed", False))
        self.kv(sync_frame, 4, "Templates changed", sync.get("templates_changed", False))
        self.kv(sync_frame, 5, "Task count", sync.get("task_count", len(app.store.tasks)))
        self.kv(sync_frame, 6, "Template count", sync.get("template_count", len(app.template_store.templates)))
        self.kv(sync_frame, 7, "Result", sync.get("message", "-"))

        filters = self.section(2, "Current View")
        self.kv(filters, 1, "Smart view", app.smart_view_var.get())
        self.kv(filters, 2, "Category", app.category_filter_var.get())
        self.kv(filters, 3, "Sort", app.sort_var.get())
        self.kv(filters, 4, "Search", app.search_var.get().strip() or "-")
        self.kv(filters, 5, "Status filter", app.active_status_filter or "-")

        cache = self.section(3, "Render Cache")
        self.kv(cache, 1, "Columns", len(app.column_frames))
        self.kv(cache, 2, "Groups", len(app.group_frames))
        self.kv(cache, 3, "Cards", len(app.card_widgets))
        self.kv(cache, 4, "Batch jobs", len(app.render_batch_jobs))
        self.kv(cache, 5, "Search cache", len(app.search_text_cache))

        events = self.section(4, "Recent Events")
        recent = list(app.diagnostics_events)[-12:]
        if not recent:
            self.kv(events, 1, "-", "No events yet")
            return
        for index, event in enumerate(reversed(recent), start=1):
            self.kv(events, index, event.get("time", "-"), f"{event.get('kind', '-')}: {event.get('detail', '-')}")
