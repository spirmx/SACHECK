import flet as ft
from datetime import datetime

from core.flet_constants import BORDER, MUTED, MUTED_2, PRIMARY, TEXT, WHITE
from core.flet_data import load_templates, ensure_status_folders, create_task_from_tool, save_tasks, APP_NAME, CREATE_TOOLS
from ui.dialogs import show_task_detail, show_message
from ui.flet_widgets import CENTER, border_all, dropdown, pad_sym, task_icon
from ui.shared import DashboardContext

def render_templates(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Template Library"
    ctx.header_subtitle.value = "SA CHECK / Reusable Assets"
    templates = load_templates()
    query = ctx.state.get("template_search", "").strip().casefold()
    ordered_template_types = ["Word", "Excel", "PowerPoint", "PDF", "Design", "Code", "Other"]

    selected_template_type = {"value": ctx.state.get("template_filter", "All template types")}
    template_list = ft.ListView(expand=True, spacing=14)

    def on_template_type_change(e):
        ctx.state["template_filter"] = e.control.value
        ctx.render_current()

    def on_template_search(e):
        ctx.state["template_search"] = e.control.value or ""
        ctx.render_current()

    def add_template_dialog(kind):
        name_field = ft.TextField(label="Template Name", hint_text="Example: Monthly Report", border_radius=12, border_color=BORDER)
        type_field = dropdown(250, "Word", ordered_template_types)
        target_field = ft.TextField(
            label="Template File or URL",
            hint_text="C:\\Templates\\report.docx" if kind == "file" else "https://docs.google.com/...",
            border_radius=12,
            border_color=BORDER
        )
        note_field = ft.TextField(label="Notes (optional)", multiline=True, min_lines=3, max_lines=3, border_radius=12, border_color=BORDER)

        def save_new_template(_e):
            if not name_field.value or not target_field.value:
                show_message(ctx.page, "Missing info", "Name and target are required.")
                return
            new_item = {
                "id": str(datetime.now().timestamp()),
                "name": name_field.value,
                "type": type_field.value,
                "date_added": datetime.now().strftime("%Y-%m-%d"),
                "target_kind": kind,
                "shortcut_path" if kind == "file" else "link": target_field.value,
                "note": note_field.value,
                "usage_count": 0,
            }
            templates.append(new_item)
            try:
                from core.flet_data import save_templates
                save_templates(templates)
                ctx.page.pop_dialog()
                ctx.render_current()
                show_message(ctx.page, "Template added", f"Saved: {name_field.value}", kind="success")
            except Exception as exc:
                show_message(ctx.page, "Save failed", str(exc))

        def pick_file_for_template(_e):
            ctx.page.pop_dialog()
            ctx.pick_directory(add_template_dialog, kind) # Note: not actually pick_directory, needs pick_file in full implementation, fallback below
            show_message(ctx.page, "Not supported", "File picker not fully wired for templates in this refactored version yet. Please paste the path.")
            # Re-show dialog
            add_template_dialog(kind)

        pick_btn = ft.Button("Browse File", icon=ft.Icons.FOLDER_OPEN, on_click=pick_file_for_template) if kind == "file" else ft.Container()

        ctx.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Add {'File' if kind == 'file' else 'Link'} Template", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Column(
                    width=500,
                    height=400,
                    spacing=16,
                    controls=[name_field, type_field, ft.Row(spacing=8, controls=[target_field, pick_btn]) if kind == "file" else target_field, note_field],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                    ft.Button("Save Template", on_click=save_new_template, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
            )
        )
        ctx.page.update()

    def template_card(t_item):
        icon, icon_color = task_icon(t_item.get("type", "Other"))

        def use_template(_e):
            # Show a dialog to create a new task based on this template
            from ui.dialogs import action_button

            task_name = ft.TextField(label="New Task Name", value=f"New {t_item.get('name', 'Task')}", border_radius=12, border_color=BORDER)

            def create_from_template(_ev):
                try:
                    ensure_status_folders()
                    # Logic to copy the template file to the work directory and create a task
                    # Since this is a UI refactor, I am preserving the flow.
                    from core.flet_data import create_task_from_source, create_snapshot, push_undo, log_activity, save_templates
                    create_snapshot("Before use template")

                    target = t_item.get("shortcut_path") or t_item.get("link")
                    new_task = create_task_from_source(
                        task_name.value,
                        target,
                        file_type=t_item.get("type", "Other"),
                        note=f"Created from template: {t_item.get('name')}",
                        status=STATUS_PENDING
                    )

                    ctx.all_tasks.append(new_task)

                    t_item["usage_count"] = t_item.get("usage_count", 0) + 1
                    t_item["last_used"] = datetime.now().isoformat()
                    save_templates(templates)

                    push_undo({"kind": "task_restore", "action": "Use template", "task_id": new_task.get("id"), "before": {}, "after": dict(new_task)})
                    log_activity("Use template", f"Created {task_name.value} from template.", {"task_id": new_task.get("id")})

                    ctx.page.pop_dialog()
                    ctx.save_and_render(f"Created '{task_name.value}' in Waiting.")
                    from core.flet_data import open_target
                    open_target(new_task)

                except Exception as exc:
                    show_message(ctx.page, "Failed to create", str(exc), kind="danger")

            ctx.page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("Use Template", size=20, weight=ft.FontWeight.W_800),
                    content=ft.Column(
                        width=400, height=100, spacing=16,
                        controls=[
                            ft.Text(f"Create a new work item from '{t_item.get('name')}'?", size=14),
                            task_name
                        ]
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                        ft.Button("Create", on_click=create_from_template, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE))
                    ]
                )
            )
            ctx.page.update()

        return ft.Container(
            height=72,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=16,
            padding=14,
            content=ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=44, height=44, border_radius=12, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=22, color=icon_color)),
                    ft.Column(
                        spacing=4,
                        expand=True,
                        controls=[
                            ft.Text(t_item.get("name", "Unnamed Template"), size=16, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Text(t_item.get("type", "Other"), size=12, color=MUTED),
                                    ft.Text("•", size=12, color=MUTED_2),
                                    ft.Text(f"Used {t_item.get('usage_count', 0)} times", size=12, color=MUTED),
                                ]
                            )
                        ]
                    ),
                    ft.Button("Use", icon=ft.Icons.PLAY_ARROW_ROUNDED, on_click=use_template, height=40, style=ft.ButtonStyle(bgcolor="#EFF6FF", color=PRIMARY, shape=ft.RoundedRectangleBorder(radius=10))),
                    ft.IconButton(icon=ft.Icons.INFO_OUTLINE, tooltip="Details", on_click=lambda _e: show_task_detail(ctx.page, t_item, ctx.save_and_render, ctx.all_tasks, is_template=True, template_to_work=use_template, template_records=templates, runtime_file_types_fn=ctx.file_types)),
                ]
            )
        )

    def render_template_list():
        filtered = templates
        if selected_template_type["value"] != "All template types":
            filtered = [t for t in filtered if t.get("type") == selected_template_type["value"]]
        if query:
            filtered = [t for t in filtered if query in t.get("name", "").casefold() or query in t.get("note", "").casefold()]

        if ctx.settings.get("template_ranking_enabled", True):
            filtered.sort(key=lambda x: (-x.get("usage_count", 0), x.get("name", "").casefold()))
        else:
            filtered.sort(key=lambda x: x.get("name", "").casefold())

        template_list.controls = [template_card(t) for t in filtered]
        if not template_list.controls:
            template_list.controls.append(ft.Container(expand=True, alignment=CENTER, content=ft.Text("No templates found.", color=MUTED_2, size=15)))

    search_templates = ft.TextField(
        hint_text="Search templates...",
        prefix_icon=ft.Icons.SEARCH,
        value=ctx.state.get("template_search", ""),
        height=46,
        expand=True,
        border_radius=14,
        border_color=BORDER,
        bgcolor=WHITE,
        on_change=on_template_search,
        content_padding=pad_sym(horizontal=12),
    )
    render_template_list()

    toolbar = ft.Container(
        height=78,
        bgcolor="#F8FBFF",
        border=border_all(1, "#BFDBFE"),
        border_radius=18,
        padding=pad_sym(horizontal=18, vertical=12),
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Filter by:", size=15, color=MUTED),
                dropdown(250, selected_template_type["value"], ["All template types", *ordered_template_types], on_template_type_change),
                search_templates,
                ft.Container(expand=True),
                ft.Button("Add File Template", icon=ft.Icons.NOTE_ADD_OUTLINED, on_click=lambda _e: add_template_dialog("file"), height=46),
                ft.Button("Add Link Template", icon=ft.Icons.ADD_LINK, on_click=lambda _e: add_template_dialog("link"), height=46),
                ft.IconButton(icon=ft.Icons.SYNC, tooltip="Sync templates", icon_color=MUTED, on_click=ctx.sync_now),
            ],
        ),
    )

    grouped_all = {t.get("type", "Other") for t in templates}
    summary = ft.Row(
        spacing=10,
        controls=[
            ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#EFF6FF", content=ft.Text(f"{len(templates)} templates", size=12, weight=ft.FontWeight.W_800, color=PRIMARY)),
            ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#F5F3FF", content=ft.Text(f"{len(grouped_all)} types", size=12, weight=ft.FontWeight.W_800, color="#7C3AED")),
            ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#ECFDF5", content=ft.Text("Use -> Waiting by type", size=12, weight=ft.FontWeight.W_800, color="#047857")),
        ],
    )
    library = ft.Container(
        expand=True,
        bgcolor="#F8FBFF",
        border=border_all(1, "#DBEAFE"),
        border_radius=22,
        padding=18,
        content=template_list,
    )
    ctx.main_body.controls = [toolbar, summary, library]
    ctx.progress_badge.value = f"{len(templates)} templates"
    ctx.page.update()
