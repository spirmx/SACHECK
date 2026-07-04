import os
from datetime import datetime
from pathlib import Path

import flet as ft

from core.flet_constants import BORDER, MUTED, MUTED_2, PRIMARY, STATUS_PENDING, TEXT, WHITE
from core.flet_data import (
    create_snapshot,
    create_task_from_source,
    create_template_from_source,
    delete_item_target,
    ensure_status_folders,
    infer_type,
    item_target,
    load_templates,
    log_activity,
    normalized_file_key,
    open_folder,
    open_target,
    push_undo,
    save_templates,
)
from ui.dialogs import show_message, show_task_detail
from ui.flet_widgets import CENTER, border_all, dropdown, pad_only, pad_sym, row_action_button, task_icon
from ui.shared import DashboardContext


def render_templates(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Template Library"
    ctx.header_subtitle.value = "SA CHECK / Reusable Assets"

    templates = load_templates()
    query = ctx.state.get("template_search", "").strip().casefold()
    ordered_template_types = list(ctx.file_types()) or ["Word", "Excel", "PowerPoint", "PDF", "Design", "Code", "Other"]

    selected_template_type = {"value": ctx.state.get("template_filter", "All template types")}
    template_list = ft.ListView(expand=True, spacing=12)

    def on_template_type_change(e):
        ctx.state["template_filter"] = e.control.value
        ctx.render_current()

    def on_template_search(e):
        ctx.state["template_search"] = e.control.value or ""
        ctx.render_current()

    def commit_templates(records, message):
        save_templates(records)
        ctx.render_current()
        if message:
            show_message(ctx.page, "Templates", message, kind="success")

    def add_template_dialog(kind):
        is_file = kind == "file"
        title = "Add File Template" if is_file else "Add Link Template"
        name_field = ft.TextField(label="Template name (optional)", border_radius=12, border_color=BORDER)
        type_field = dropdown(300, "Auto-detect", ["Auto-detect", *ordered_template_types])
        target_field = ft.TextField(
            label="Local file path" if is_file else "Link (URL)",
            value="" if is_file else "https://",
            border_radius=12,
            border_color=BORDER,
            expand=True,
        )
        note_field = ft.TextField(label="Note (optional)", multiline=True, min_lines=2, max_lines=3, border_radius=12, border_color=BORDER)
        detected_label = ft.Text("Type is detected automatically.", size=12, color=MUTED)

        def refresh_detection(_e=None):
            value = (target_field.value or "").strip()
            if value and value != "https://":
                detected_label.value = f"Detected type: {infer_type(value)}"
                detected_label.color = PRIMARY
            else:
                detected_label.value = "Type is detected automatically."
                detected_label.color = MUTED
            try:
                detected_label.update()
            except Exception:
                pass

        target_field.on_change = refresh_detection

        async def browse(_e):
            picked = await ctx.file_picker.pick_files(dialog_title="Choose template file", allow_multiple=False)
            path = picked[0].path if picked else ""
            if path:
                target_field.value = path
                if not (name_field.value or "").strip():
                    name_field.value = Path(path).stem
                refresh_detection()
                ctx.page.update()

        async def paste_url(_e):
            try:
                value = await ctx.page.clipboard.get()
            except Exception:
                value = ""
            if value:
                target_field.value = str(value)
                refresh_detection()
                ctx.page.update()

        def effective_type():
            return "Other" if type_field.value == "Auto-detect" else type_field.value

        def save_template(_e):
            target = (target_field.value or "").strip()
            if not target or target == "https://":
                show_message(ctx.page, "Missing info", "Please choose a file or enter a link first.")
                return
            try:
                display_name = (name_field.value or "").strip() or (Path(target).stem if is_file else target)
                record = create_template_from_source(display_name, target, file_type=effective_type(), note=note_field.value or "")
            except Exception as exc:
                show_message(ctx.page, "Save failed", str(exc), kind="danger")
                return
            templates.append(record)
            try:
                ctx.page.pop_dialog()
            except Exception:
                pass
            commit_templates(templates, f"Saved template: {record.get('name')} ({record.get('type')})")

        target_row = ft.Row(
            spacing=10,
            controls=[
                target_field,
                ft.Button("Browse" if is_file else "Paste URL", on_click=browse if is_file else paste_url, width=130 if is_file else 110),
            ],
        )
        ctx.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(title, size=22, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Column(
                    width=560,
                    height=420,
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        name_field,
                        target_row,
                        ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text("File type" if is_file else "Link type", size=12, weight=ft.FontWeight.W_700, color=MUTED),
                                ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[type_field, detected_label]),
                            ],
                        ),
                        note_field,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                    ft.Button("Save Template", on_click=save_template, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        ctx.page.update()

    def use_template(t_item):
        ensure_status_folders()
        name_field = ft.TextField(label="New Work Item Name", value=t_item.get("name", "Task"), border_radius=12, border_color=BORDER)

        def create_from_template(_ev):
            try:
                create_snapshot("Before use template")
                source = item_target(t_item)
                new_task = create_task_from_source(
                    name_field.value,
                    source,
                    file_type=t_item.get("type", "Other"),
                    note=f"From template: {t_item.get('name', '')}",
                    status=STATUS_PENDING,
                )
                ctx.all_tasks.append(new_task)
                t_item["usage_count"] = int(t_item.get("usage_count", 0)) + 1
                t_item["last_used"] = datetime.now().isoformat()
                save_templates(templates)
                push_undo({"kind": "task_restore", "action": "Use template", "task_id": new_task.get("id"), "before": {}, "after": dict(new_task)})
                log_activity("Use template", f"Created {name_field.value} from template.", {"task_id": new_task.get("id")})
                try:
                    ctx.page.pop_dialog()
                except Exception:
                    pass
                ctx.save_and_render(f"Created '{name_field.value}' in Waiting.")
            except Exception as exc:
                show_message(ctx.page, "Failed to create", str(exc), kind="danger")

        ctx.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Use Template", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Column(
                    width=420,
                    height=120,
                    spacing=14,
                    controls=[ft.Text(f"Copy '{t_item.get('name')}' into Waiting. The template stays untouched.", size=14, color=MUTED), name_field],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                    ft.Button("Create", on_click=create_from_template, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
            )
        )
        ctx.page.update()

    def open_template(t_item):
        try:
            open_target(t_item)
        except Exception as exc:
            show_message(ctx.page, "Open failed", str(exc), kind="danger")

    def open_template_folder(t_item):
        try:
            open_folder(t_item)
        except Exception as exc:
            show_message(ctx.page, "Open folder failed", str(exc), kind="danger")

    def copy_target(t_item):
        target = item_target(t_item)
        async def worker():
            try:
                await ctx.page.clipboard.set(target or "")
                show_message(ctx.page, "Copied", "Template path copied to clipboard.", kind="success")
            except Exception as exc:
                show_message(ctx.page, "Copy failed", str(exc), kind="danger")
        ctx.page.run_task(worker)

    def delete_template(t_item):
        def confirm_delete(_e):
            try:
                ctx.page.pop_dialog()
            except Exception:
                pass
            create_snapshot("Before delete template")
            try:
                delete_item_target(t_item)
            except Exception as exc:
                show_message(ctx.page, "Delete failed", str(exc), kind="danger")
                return
            item_id = t_item.get("id")
            item_key = t_item.get("file_key") or normalized_file_key(item_target(t_item))
            remaining = [
                rec
                for rec in templates
                if not (
                    (item_id and rec.get("id") == item_id)
                    or (item_key and (rec.get("file_key") or normalized_file_key(item_target(rec))) == item_key)
                )
            ]
            log_activity("Delete template", f"Removed template {t_item.get('name')}", {"id": item_id})
            commit_templates(remaining, f"Deleted template: {t_item.get('name')}")

        ctx.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Delete Template", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Text(f"Delete '{t_item.get('name')}' and its file in Template? This cannot be undone except via snapshot.", size=14, color=MUTED),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                    ft.Button("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor="#E11D48", color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
            )
        )
        ctx.page.update()

    def template_card(t_item):
        icon, icon_color = task_icon(t_item.get("type", "Other"))
        is_url = t_item.get("target_kind") == "url"
        subtitle = "Link" if is_url else (item_target(t_item) or "")
        card = ft.Container(
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=14,
            padding=12,
            animate=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=42, height=42, border_radius=12, bgcolor=icon_color, alignment=CENTER, content=ft.Icon(icon, size=20, color=WHITE)),
                    ft.Column(
                        spacing=3,
                        expand=True,
                        controls=[
                            ft.Text(t_item.get("name", "Unnamed Template"), size=15, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Text(t_item.get("type", "Other"), size=12, color=MUTED),
                                    ft.Text("•", size=12, color=MUTED_2),
                                    ft.Text(f"Used {int(t_item.get('usage_count', 0))}x", size=12, color=MUTED),
                                    ft.Text("•", size=12, color=MUTED_2),
                                    ft.Text(subtitle, size=12, color=MUTED_2, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                                ]
                            ),
                        ],
                    ),
                    row_action_button("Use", ft.Icons.PLAY_ARROW_ROUNDED, lambda _e, item=t_item: use_template(item), primary=True),
                    ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, tooltip="Open", icon_color=MUTED, on_click=lambda _e, item=t_item: open_template(item)),
                    ft.IconButton(icon=ft.Icons.FOLDER_OPEN, tooltip="Open Folder", icon_color=MUTED, on_click=lambda _e, item=t_item: open_template_folder(item)),
                    ft.IconButton(icon=ft.Icons.CONTENT_COPY, tooltip="Copy Path", icon_color=MUTED, on_click=lambda _e, item=t_item: copy_target(item)),
                    ft.IconButton(
                        icon=ft.Icons.INFO_OUTLINE,
                        tooltip="Detail",
                        icon_color=MUTED,
                        on_click=lambda _e, item=t_item: show_task_detail(ctx.page, item, ctx.save_and_render, ctx.all_tasks, is_template=True, template_to_work=lambda _x=None, it=t_item: use_template(it), template_records=templates, runtime_file_types_fn=ctx.file_types),
                    ),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Delete", icon_color="#E11D48", on_click=lambda _e, item=t_item: delete_template(item)),
                ],
            ),
        )

        def on_hover(e):
            hovered = e.data == "true"
            card.border = border_all(1.5, PRIMARY if hovered else BORDER)
            card.bgcolor = "#FBFDFF" if hovered else WHITE
            card.shadow = ft.BoxShadow(spread_radius=0, blur_radius=16, color="#14000000", offset=ft.Offset(0, 5)) if hovered else None
            card.update()

        card.on_hover = on_hover
        return card

    def type_folder_card(type_name, items):
        icon, icon_color = task_icon(type_name)
        return ft.Container(
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=16,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#0A000000", offset=ft.Offset(0, 4)),
            content=ft.ExpansionTile(
                expanded=False,
                maintain_state=True,
                tile_padding=pad_only(left=12, right=8),
                controls_padding=pad_only(left=10, right=10, bottom=10),
                title=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=5, height=34, border_radius=999, bgcolor=icon_color),
                        ft.Container(width=34, height=34, border_radius=10, bgcolor="#F1F5F9", border=border_all(1, BORDER), alignment=CENTER, content=ft.Icon(icon, size=17, color=icon_color)),
                        ft.Column(
                            spacing=1,
                            expand=True,
                            controls=[
                                ft.Text(type_name, size=14, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"{len(items)} template(s)", size=11, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        ft.Container(padding=pad_sym(horizontal=10, vertical=4), border_radius=999, bgcolor="#EFF6FF", content=ft.Text(str(len(items)), size=12, weight=ft.FontWeight.W_800, color=PRIMARY)),
                    ],
                ),
                controls=[ft.Column(spacing=8, controls=[template_card(t) for t in items])],
            ),
        )

    def render_template_list():
        filtered = list(templates)
        if selected_template_type["value"] != "All template types":
            filtered = [t for t in filtered if t.get("type") == selected_template_type["value"]]
        if query:
            filtered = [t for t in filtered if query in (t.get("name", "") or "").casefold() or query in (t.get("note", "") or "").casefold()]

        if ctx.settings.get("template_ranking_enabled", True):
            filtered.sort(key=lambda x: (-int(x.get("usage_count", 0)), (x.get("name", "") or "").casefold()))
        else:
            filtered.sort(key=lambda x: (x.get("name", "") or "").casefold())

        groups = {}
        for t in filtered:
            groups.setdefault(t.get("type", "Other"), []).append(t)

        ordered_keys = [t for t in ordered_template_types if t in groups] + [k for k in groups if k not in ordered_template_types]

        template_list.controls = [type_folder_card(type_name, groups[type_name]) for type_name in ordered_keys]
        if not template_list.controls:
            template_list.controls.append(ft.Container(expand=True, alignment=CENTER, padding=40, content=ft.Text("No templates found. Add one, or drop files into a <type>/Template folder and Sync.", color=MUTED_2, size=15)))

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
        bgcolor="#F8FBFF",
        border=border_all(1, "#BFDBFE"),
        border_radius=18,
        padding=pad_sym(horizontal=18, vertical=12),
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Filter:", size=15, color=MUTED),
                dropdown(230, selected_template_type["value"], ["All template types", *ordered_template_types], on_template_type_change),
                search_templates,
                ft.Container(expand=True),
                ft.Button("Add File", icon=ft.Icons.NOTE_ADD_OUTLINED, on_click=lambda _e: add_template_dialog("file"), height=46),
                ft.Button("Add Link", icon=ft.Icons.ADD_LINK, on_click=lambda _e: add_template_dialog("link"), height=46),
                ft.IconButton(icon=ft.Icons.SYNC, tooltip="Sync templates from Template folders", icon_color=MUTED, on_click=ctx.sync_now),
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
        padding=14,
        content=template_list,
    )
    ctx.main_body.controls = [toolbar, summary, library]
    ctx.progress_badge.value = f"{len(templates)} templates"
    ctx.page.update()
