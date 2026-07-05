import json
import os
import subprocess
import sys
import uuid
import urllib.error
import urllib.request
import calendar
import csv
import html
import hashlib
import time
import threading
import re
import tempfile
import base64
import asyncio
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

import flet as ft

from ui.shared import DashboardContext
from ui.screens import render_overview, render_board, render_browser, render_calendar, render_templates, render_health, render_settings

from core.app_paths import APP_SETTINGS_FILE, DATA_FILE, app_folder, work_folder
from core.bulk_import import import_rows
from core.flet_theme import CALENDAR_EVENT_COLOR_CHOICES, calendar_event_style
from core.native_file_drop import install_native_file_drop


BG = "#F8FAFC"
WHITE = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"
MUTED_2 = "#94A3B8"
BORDER = "#E2E8F0"
PRIMARY = "#2563EB"

WAITING_BG = "#EFF6FF"
WAITING_TEXT = "#2563EB"
DOING_BG = "#FFFBEB"
DOING_TEXT = "#D97706"
DONE_BG = "#F0FDF4"
DONE_TEXT = "#16A34A"

STATUS_PENDING = "pending"
STATUS_PROGRESS = "progress"
STATUS_DONE = "done"

SCREEN_OVERVIEW = "overview"
SCREEN_BOARD = "board"
SCREEN_BROWSER = "browser"

STATUS_BY_FILTER = {"Waiting": STATUS_PENDING, "Doing": STATUS_PROGRESS, "Completed": STATUS_DONE}
STATUS_LABELS = {STATUS_PENDING: "Waiting", STATUS_PROGRESS: "Doing", STATUS_DONE: "Success"}
FILE_TYPES = ["Other", "Word", "Excel", "Google Sheet", "Miro", "Web", "Project", "Link"]
MAX_GROUP_RENDER_ITEMS = 80
STATUS_THEME_PRESETS = {
    "Classic Blue": {
        STATUS_PENDING: ("#EFF6FF", "#2563EB"),
        STATUS_PROGRESS: ("#FFFBEB", "#D97706"),
        STATUS_DONE: ("#F0FDF4", "#16A34A"),
    },
    "Clean Slate": {
        STATUS_PENDING: ("#F8FAFC", "#475569"),
        STATUS_PROGRESS: ("#FFF7ED", "#EA580C"),
        STATUS_DONE: ("#ECFDF5", "#059669"),
    },
    "High Contrast": {
        STATUS_PENDING: ("#EEF2FF", "#4338CA"),
        STATUS_PROGRESS: ("#FEF3C7", "#92400E"),
        STATUS_DONE: ("#DCFCE7", "#166534"),
    },
}

APP_THEME_PRESETS = {
    "Ocean Pro": {"bg": "#F8FAFC", "surface": "#FFFFFF", "text": "#0F172A", "muted": "#64748B", "muted_2": "#94A3B8", "border": "#E2E8F0", "primary": "#2563EB", "nav": "#08111F", "nav_active": "#1D4ED8", "soft": "#EFF6FF"},
    "Candy Cartoon": {"bg": "#FFF7ED", "surface": "#FFFFFF", "text": "#1F2937", "muted": "#7C3AED", "muted_2": "#F472B6", "border": "#FBCFE8", "primary": "#DB2777", "nav": "#2E1065", "nav_active": "#F97316", "soft": "#FDF2F8"},
    "Sakura Desk": {"bg": "#FFF1F2", "surface": "#FFFFFF", "text": "#27272A", "muted": "#71717A", "muted_2": "#FB7185", "border": "#FFE4E6", "primary": "#E11D48", "nav": "#3F0A1D", "nav_active": "#FB7185", "soft": "#FFF7F9"},
    "Mint Studio": {"bg": "#F0FDFA", "surface": "#FFFFFF", "text": "#134E4A", "muted": "#0F766E", "muted_2": "#5EEAD4", "border": "#CCFBF1", "primary": "#0D9488", "nav": "#042F2E", "nav_active": "#14B8A6", "soft": "#ECFEFF"},
    "Sunset Pop": {"bg": "#FFF7ED", "surface": "#FFFFFF", "text": "#1F2937", "muted": "#9A3412", "muted_2": "#F59E0B", "border": "#FED7AA", "primary": "#EA580C", "nav": "#1E1B4B", "nav_active": "#F97316", "soft": "#FFFBEB"},
    "Night Arcade": {"bg": "#0B1020", "surface": "#111827", "text": "#E5E7EB", "muted": "#A5B4FC", "muted_2": "#67E8F9", "border": "#334155", "primary": "#22D3EE", "nav": "#020617", "nav_active": "#7C3AED", "soft": "#172554"},
    "Graphite Focus": {"bg": "#F4F4F5", "surface": "#FFFFFF", "text": "#18181B", "muted": "#52525B", "muted_2": "#A1A1AA", "border": "#D4D4D8", "primary": "#334155", "nav": "#111827", "nav_active": "#475569", "soft": "#F8FAFC"},
}


DARK_UI = False
UI_LANGUAGE = "en"


def bundled_asset_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return str(base.joinpath("assets", *parts))


APP_NAME = "SA CHECK"
APP_VERSION = "2.1.0"
MANUAL_VERSION = "2026-06-18-user-guide"
DEFAULT_UPDATE_CHANNEL_URL = "https://raw.githubusercontent.com/spirmx/SACHECK/main/sacheck_update.json"
UPDATE_MANIFEST_FILE = "sacheck_update.json"
DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES = 1
VERSION_HISTORY = [
    {
        "version": "2.1.0",
        "date": "2026-07-06",
        "latest": True,
        "items": [
            "Added a four-state scheduled-sync indicator: gray idle, animated amber syncing, green success, and red failure with diagnostic logging.",
            "Added a live Doing strip in the header with marquee task names and a fixed status-change time.",
            "Hardened scheduled/manual sync with a single-run lock, safe timeout handling, structured failure records, and guarded UI actions.",
            "Consolidated the stability and workflow work accumulated since the 1.x platform into the 2.1 release line.",
        ],
    },
    {
        "version": "2.0.9",
        "date": "2026-07-06",
        "latest": False,
        "items": [
            "Added the new Home hero alert panel for today and tomorrow.",
            "Added smooth count-up, glow, pulse, stagger, status, type, Board, Files, Templates, and Calendar animations.",
            "Redesigned the sidebar connection card as an animated live network console.",
            "Preserved drag-and-drop, unified Add flows, custom types, bulk import, and 2,000-task Board performance.",
        ],
    },
    {
        "version": "2.0.8-1",
        "date": "2026-07-05",
        "latest": False,
        "items": [
            "Added native Windows Explorer drag-and-drop into the Board bulk-import flow.",
            "Dropped files open Add files automatically or join the currently open import dialog.",
            "Kept Browse files as a fallback and reused classification, custom types, progress, and cancellation.",
        ],
    },
    {
        "version": "2.0.8",
        "date": "2026-07-05",
        "latest": False,
        "items": [
            "Unified Add file and Add link dialogs across Board and Templates with clear destination badges.",
            "Removed the confusing Add path action and restored inline custom-type creation for Templates.",
            "Added smooth event-driven animations for navigation, status, type, task, and workflow controls.",
            "Added a verified source snapshot exporter and agent continuation guide.",
        ],
    },
    {
        "version": "2.0.7",
        "date": "2026-07-05",
        "latest": False,
        "items": [
            "Added an inline custom-type popup when Other is selected while adding work or importing files.",
            "Kept the current Add form open and selected the newly created type automatically.",
            "Unified inline and Settings type creation through the same validation and storage service.",
        ],
    },
    {
        "version": "2.0.6",
        "date": "2026-07-05",
        "latest": False,
        "items": [
            "Added background bulk import with live progress, cancellation, and a clear result summary.",
            "Batched large category dialogs so thousands of tasks no longer create thousands of controls at once.",
            "Added repeatable stress coverage for 2,000 Board tasks and bulk-import failure handling.",
        ],
    },
    {
        "version": "2.0.5",
        "date": "2026-07-05",
        "latest": False,
        "items": [
            "Restored the complete cached Board, Calendar, Settings, startup, and dialog improvements.",
            "Moved Board quick actions into the filter row and restored grouped category controls.",
            "Regenerated integrity data so startup repair keeps the restored code instead of reverting it.",
        ],
    },
    {
        "version": "2.0.4",
        "date": "2026-07-05",
        "latest": False,
        "items": [
            "Kept calendar event colors consistent across Calendar, Overview, and event details.",
            "Normalized saved event colors and added regression coverage for the shared palette.",
            "Published this release as a required update while preserving Work folders, settings, cache, and user data.",
        ],
    },
    {
        "version": "2.0.3",
        "date": "2026-07-03",
        "latest": False,
        "items": [
            "Fixed the Board gray error panel caused by a wrapped filter row in Flutter layout.",
            "Made Board filters horizontally scrollable at narrow window sizes.",
            "Added a regression smoke check for the safe Board filter layout.",
        ],
    },
    {
        "version": "2.0.0",
        "date": "2026-07-03",
        "latest": False,
        "items": [
            "Added the Command Center overview, command palette, and cleaner interactive cards.",
            "Expanded the work model with progress, priority, tags, and members.",
            "Improved Board performance, group persistence, and layout reliability.",
            "Added automated core tests and headless smoke tests for every screen.",
        ],
    },
    {
        "version": "1.0.9-02 Abillity",
        "date": "2026-06-30",
        "latest": False,
        "items": [
            "Removed the black native startup frame by keeping the window hidden until the loader is ready.",
            "Replaced the Flet executable and title-bar icon with the SA CHECK logo.",
            "Changed the startup loader from a floating card to a clean full-window loading surface.",
            "Kept safe in-app refresh, Git update checks, and local Work data protection unchanged.",
        ],
    },
    {
        "version": "1.0.9-01 Abillity",
        "date": "2026-06-30",
        "latest": False,
        "items": [
            "Sync now performs a safe in-app refresh without closing or blanking the main window.",
            "The refresh loader reloads Work data and settings, then checks Git for updates.",
            "Added timeout and error recovery so a slow folder cannot leave the app stuck on Working.",
            "The startup loader is centered on screen and remains visible long enough to read its status.",
            "Fixed About SA CHECK and User guide buttons in the Settings Credits section.",
            "Settings now opens the same About, User guide, and Version notes dialogs as the main dashboard.",
            "Work folders, settings, and cache remain local and are never cleared by refresh.",
        ],
    },
    {
        "version": "1.0.9",
        "date": "2026-06-29",
        "latest": False,
        "items": [
            "Added a bright, colorful startup loader before the Work Board opens.",
            "Online startup checks now verify the Git update channel with a short timeout.",
            "Offline mode skips update and integrity network checks and opens local work immediately.",
            "Added SHA-256 verified repair support for app system files without touching Work folders, settings, or cache.",
            "Startup failures fall back to the existing dashboard instead of leaving the app stuck on loading.",
        ],
    },
    {
        "version": "1.0.8 Stable",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Stabilized Calendar event dialog click handling.",
            "Removed nested DatePicker/TimePicker popups from inside the edit dialog.",
            "Moved Calendar event buttons back to standard AlertDialog actions.",
            "Added direct date/time validation so invalid values do not save.",
        ],
    },
    {
        "version": "1.0.7.7 Calendar TimePicker Hotfix",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Hotfixed Calendar event time selection when the dropdown stopped opening.",
            "Replaced the time dropdown with a standard 24-hour TimePicker popup.",
            "Removed the dropdown menu-height setting that could break the packaged Flet runtime.",
            "Kept the compact Calendar event dialog layout and saved event data compatible.",
        ],
    },
    {
        "version": "1.0.7.6 Calendar Dialog Fit",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Fixed Calendar event dialog height so bottom actions are no longer clipped.",
            "Limited the 24-hour time dropdown height so it does not stretch across the screen.",
            "Tightened Calendar event spacing while keeping the clean card-based layout.",
            "Kept DatePicker popup, time dropdown, color chips, and saved event data compatible.",
        ],
    },
    {
        "version": "1.0.7.5 Calendar Native Picker",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Rebuilt Calendar event dialog into a clean card-based layout.",
            "Selected date now opens a standard DatePicker popup instead of manual +/- controls.",
            "Selected time now uses a 24-hour dropdown in 30-minute intervals.",
            "Moved Delete to the far left and Save/Cancel to the far right for safer actions.",
        ],
    },
    {
        "version": "1.0.7.4 Calendar UX Polish",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Polished Calendar event date/time UX into compact picker cards.",
            "Removed the tall stepper block that made the dialog feel crowded.",
            "Added clearer date and time quick actions without long dropdown menus.",
            "Reduced dialog height pressure so the note box and action buttons stay visible.",
        ],
    },
    {
        "version": "1.0.7.3 Calendar UX",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Reworked Calendar event date/time UX to avoid dropdown menus overflowing the dialog.",
            "Changed Year, Month, Day, Hour, and Minute into fixed stepper controls.",
            "Kept quick date and quick time buttons for faster scheduling.",
            "Kept calendar event storage compatible with previous versions.",
        ],
    },
    {
        "version": "1.0.7.2 Calendar Picker",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Replaced free-typing calendar event date/time with guided dropdown pickers.",
            "Added Today/Tomorrow and quick time buttons for safer event scheduling.",
            "Calendar event save now uses picker-backed YYYY-MM-DD and HH:MM values.",
            "Kept existing event storage and reminders compatible with previous versions.",
        ],
    },
    {
        "version": "1.0.7.1 UI Sharpness",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Sharpened dashboard cards, navigation buttons, and Health Center panels.",
            "Reduced heavy blur shadows so borders and text read cleaner.",
            "Improved contrast on Health Check and Broken Link Center controls.",
            "Kept this as a small UI-only patch without changing user Work data.",
        ],
    },
    {
        "version": "1.0.7 Health Center",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Added Health Check overview for Work folder, data files, templates, updates, and snapshots.",
            "Added Broken Link Center filters for tasks, templates, missing targets, and URL shortcuts.",
            "Improved broken-link detection for older records and URL shortcut records.",
            "Added clearer repair status counts without touching Work files during scans.",
        ],
    },
    {
        "version": "1.0.6 Reliability Patch",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Hardened Template use, delete, and target fallback for older records.",
            "Fixed task edit behavior when changing a URL item into a file or folder target.",
            "Added clearer failure handling when a selected target file or folder is missing.",
            "Cleaned up stale URL shortcuts when an item is changed to a local file/folder target.",
        ],
    },
    {
        "version": "1.0.5 Template Fix",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Fixed Template edit, type move, and target update flow.",
            "Fixed Template delete so both file and record are removed reliably.",
            "Template category changes now move the stored template file to the correct Work type folder.",
            "Added safer Template file handling without clearing Work folders or user data.",
        ],
    },
    {
        "version": "1.0.4-01 Stable Hotfix",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Changed update finish behavior so SA CHECK stays closed after installation.",
            "Users should open SA CHECK manually after the installer finishes.",
            "Avoids black-screen or empty-data states caused by relaunching too quickly.",
            "Keeps Work folders, settings, cache, and user data safe.",
        ],
    },
    {
        "version": "1.0.4 Stable",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Required stability update for SA CHECK.",
            "Hardened update flow to prevent duplicate installer launches.",
            "Required updates can start automatically while Online mode is enabled.",
            "Keeps Work folders, settings, cache, and user data safe.",
        ],
    },
    {
        "version": "1.0.3-06 Build 6",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "Added configurable automatic update check interval.",
            "Default update check interval is now 1 minute for easier update testing.",
            "Settings can choose 1, 5, 15, 30, or 60 minutes.",
        ],
    },
    {
        "version": "1.0.3-05 Build 5",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "แพตเล็กสำหรับทดสอบระบบแจ้งเตือนอัพเดทจาก GitHub",
            "ใช้ทดสอบว่าแอพเด้งเตือนเมื่อ manifest มีเวอร์ชันใหม่",
            "ไม่เปลี่ยนข้อมูลผู้ใช้ Work folder settings หรือ cache",
        ],
    },
    {
        "version": "1.0.3-04 Build 4",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "ซ่อนหน้าต่าง Setup wizard ตอนอัปเดตจากในแอพ",
            "รัน installer แบบ silent พร้อมปิดกล่องถาม task/shortcut/startup",
            "ใช้ Inno Setup silent flags สำหรับ update flow เท่านั้น",
        ],
    },
    {
        "version": "1.0.3-03 Build 3",
        "date": "2026-06-22",
        "latest": False,
        "items": [
            "แก้หน้า Download Update ค้าง 0% ให้เห็น progress เร็วขึ้น",
            "เช็กขนาดไฟล์ด้วย HEAD ก่อนโหลดจริง",
            "ใส่ cachebuster ให้ installer URL และลด chunk download ให้ progress ถี่ขึ้น",
        ],
    },
    {
        "version": "1.0.3-02 Build 2",
        "date": "2026-06-21",
        "latest": False,
        "items": [
            "แก้ระบบอัปเดตให้แจ้งเตือนทุกครั้งที่มีแพลตใหม่",
            "ถอดตัวกัน popup ซ้ำใน session เพื่อให้เทสอัปเดตเห็นชัด",
            "เพิ่ม cachebuster ตอนอ่าน manifest จาก GitHub API/Raw",
        ],
    },
    {
        "version": "1.0.3-01 Build 1",
        "date": "2026-06-21",
        "latest": False,
        "items": [
            "แก้ DarkMode ให้สีพื้นหลังและตัวอักษรไม่กลืนกัน",
            "ปรับ DarkMode ให้ระบบเปลี่ยนโทนทั้งแอพ ไม่ใช่เฉพาะกรอบหน้าต่าง",
            "ปล่อยเป็นแพลตเล็กสำหรับทดสอบระบบอัปเดตผ่าน GitHub",
        ],
    },
    {
        "version": "1.0.3 BigUp",
        "date": "2026-06-21",
        "latest": False,
        "items": [
            "เพิ่มกฎบังคับอัปเดตแบบแพลตหลัก/แพลตย่อยให้ชัดขึ้น",
            "เพิ่มโครงภาษา TH/EN ใน Settings",
            "เพิ่ม safety guard ให้หน้า render หลักไม่ล่มทั้งแอพง่ายๆ",
            "ปรับ Version Notes ให้มี Remark สีเขียวสำหรับเวอร์ชันล่าสุด",
        ],
    },
    {
        "version": "1.0.2",
        "date": "2026-06-21",
        "latest": False,
        "items": [
            "เปลี่ยน update channel ไป GitHub spirmx/SACHECK",
            "เพิ่มปุ่ม Apply theme และถอดการเปลี่ยนธีมทันที",
            "เพิ่มหน้าดาวน์โหลด update พร้อมขนาดไฟล์และเปอร์เซ็นต์",
        ],
    },
    {
        "version": "1.0.1 Finally",
        "date": "2026-06-20",
        "latest": False,
        "items": [
            "แก้ FilePicker packaged runtime",
            "เพิ่ม fallback เลือกโฟลเดอร์แบบ Windows native",
            "เพิ่ม theme presets, sidebar media, และ online/offline switch",
        ],
    },
]
CURRENT_CHANGELOG = [
    "V1.0.8 Stable: Calendar event dialog uses standard actions and direct date/time validation to avoid unclickable overlays.",
    "V1.0.7.7 Calendar TimePicker Hotfix: Time selection now uses a 24-hour TimePicker popup after the dropdown stopped opening.",
    "V1.0.7.6 Calendar Dialog Fit: Calendar dialog bottom actions no longer clip and time dropdown is height-limited.",
    "V1.0.7.5 Calendar Native Picker: Calendar dialog now uses DatePicker popup, 24-hour time dropdown, compact color chips, and safer bottom actions.",
    "V1.0.7.4 Calendar UX Polish: Calendar date/time picker now uses compact cards, quick actions, and no long dropdown list.",
    "V1.0.7.3 Calendar UX: Replaced overflowing calendar dropdowns with fixed stepper controls for date and time.",
    "V1.0.7.2 Calendar Picker: Calendar events now use guided date/time selectors with quick date and time buttons.",
    "V1.0.7.1 UI Sharpness: Sharpened card borders, navigation buttons, Health Center panels, and reduced heavy blur shadows.",
    "V1.0.7 Health Center: Added Health Check overview, Broken Link Center filters, and stronger broken target detection.",
    "V1.0.6 Reliability Patch: Hardened Template target fallback, URL-to-file edits, stale shortcut cleanup, and missing-target errors.",
    "V1.0.5 Template Fix: Fixed Template edit, type move, delete, and create-to-work reliability.",
    "V1.0.4-01 Stable Hotfix: Update install now leaves SA CHECK closed so users reopen it manually after setup finishes.",
    "V1.0.4 Stable: Required stability update with safer forced-update flow and duplicate-launch protection.",
    "V1.0.3-06 Build 6: Auto update checks can run every minute and are configurable in Settings.",
    "V1.0.3-05 Build 5: Small Git update notification test patch.",
    "V1.0.3-04 Build 4: In-app updates now launch the installer silently without showing the setup wizard.",
    "V1.0.3-03 Build 3: Fixed update download staying at 0% by adding size precheck and finer progress updates.",
    "V1.0.3-02 Build 2: Update prompt now appears every time the app detects a newer platform.",
    "V1.0.3-01 Build 1: Fixed DarkMode text/background contrast and applied dark colors across the app surface.",
    "V1.0.3 BigUp: เพิ่มกฎบังคับอัปเดตตามแพลตหลัก/แพลตย่อยและเพิ่ม Version Remark ล่าสุด.",
    "V1.0.3 BigUp: เพิ่มโครงภาษา TH/EN และ safety guard สำหรับหน้า render หลัก.",
    "V1.0.2: Update channel now uses GitHub repo spirmx/SACHECK and Drive fallback was removed from the app flow.",
    "V1.0.2: Theme changes now wait for the Apply theme button, so users can choose before committing.",
    "Added App Theme presets for the whole workspace look.",
    "Added a brighter update button above the user guide button when updates are available.",
    "Improved the user guide layout with grouped sections.",
    "Kept offline-first behavior and safe app updates without clearing user Work data.",
]
APP_LOGO_SRC = "app/app_logo.png"
APP_LOGO_PATH = bundled_asset_path("app", "app_logo.png")
APP_ICON_PATH = bundled_asset_path("app", "app.ico")
PROFILE_MEDIA_DIR = APP_SETTINGS_FILE.parent / "profile_media"
PROFILE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
PROFILE_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
LANGUAGE_LABELS = {"en": "English", "th": "ไทย"}
UI_TEXT = {
    "en": {
        "settings": "Settings",
        "system_setup": "System Setup",
        "language": "Language",
        "language_hint": "Choose the app language. Some technical terms stay short so teams can understand them.",
        "apply_theme": "Apply theme",
        "theme_apply_hint": "Theme changes apply after pressing this button.",
        "updates": "System Updates",
    },
    "th": {
        "settings": "ตั้งค่า",
        "system_setup": "ตั้งค่าระบบ",
        "language": "ภาษา",
        "language_hint": "เลือกภาษาของแอพ คำเทคนิคบางคำจะคงไว้ให้อ่านเข้าใจง่ายในทีม",
        "apply_theme": "ใช้ธีมนี้",
        "theme_apply_hint": "ธีมจะเปลี่ยนหลังจากกดปุ่มนี้",
        "updates": "อัปเดตระบบ",
    },
}

TH_TEXT = {
    "Project Overview": "ภาพรวมงาน",
    "Work Board": "บอร์ดงาน",
    "Settings": "ตั้งค่า",
    "System Setup": "ตั้งค่าระบบ",
    "System": "ระบบ",
    "Credits": "เครดิต",
    "Desktop Work Board": "บอร์ดงานเดสก์ท็อป",
    "About SA CHECK": "เกี่ยวกับ SA CHECK",
    "User guide": "คู่มือ",
    "Work Folder Source": "แหล่งโฟลเดอร์งาน",
    "Choose Work folder": "เลือกโฟลเดอร์งาน",
    "Open Work folder": "เปิดโฟลเดอร์งาน",
    "Data file": "ไฟล์ข้อมูล",
    "Appearance": "หน้าตาแอพ",
    "Dark mode": "โหมดมืด",
    "Sidebar profile media": "รูปโปรไฟล์แถบข้าง",
    "Upload media": "อัปโหลดรูป",
    "App theme": "ธีมแอพ",
    "Status theme": "ธีมสถานะ",
    "Apply theme": "ใช้ธีมนี้",
    "System Updates": "อัปเดตระบบ",
    "Current version": "เวอร์ชันปัจจุบัน",
    "Online update checks": "เช็กอัปเดตออนไลน์",
    "Offline mode": "โหมดออฟไลน์",
    "Check now": "เช็กตอนนี้",
    "Version notes": "บันทึกเวอร์ชัน",
    "Sync & Safety Policy": "ซิงก์และความปลอดภัย",
    "Realtime sync": "ซิงก์แบบทันที",
    "Sync interval": "รอบซิงก์",
    "Snapshots kept": "จำนวนสำรองที่เก็บ",
    "Move files when status changes": "ย้ายไฟล์เมื่อเปลี่ยนสถานะ",
    "Confirm risky actions": "ยืนยันก่อนทำรายการเสี่ยง",
    "Smart Features": "ฟีเจอร์ช่วยคิด",
    "Smart Search parser": "ค้นหาอัจฉริยะ",
    "Smart Health insights": "วิเคราะห์สุขภาพงาน",
    "Workload & zombie hints": "แจ้งเตือนงานค้าง/งานล้น",
    "Smart Template ranking": "จัดอันดับ Template อัตโนมัติ",
    "Smart thresholds": "เกณฑ์วิเคราะห์งาน",
    "Stale Doing": "Doing ค้าง",
    "Zombie Waiting": "Waiting ค้างนาน",
    "Overload Doing": "Doing ล้น",
    "Overload Total": "งานรวมล้น",
    "Reset Defaults": "คืนค่าเริ่มต้น",
    "Reset smart": "รีเซ็ตตัวช่วย",
    "Reset sync": "รีเซ็ตซิงก์",
    "Reset UI": "รีเซ็ตหน้าตา",
    "Save settings": "บันทึกตั้งค่า",
    "Work browser": "คลังงาน",
    "Sync now": "ซิงก์ตอนนี้",
    "Reload data": "โหลดข้อมูลใหม่",
    "Create folders": "สร้างโฟลเดอร์",
    "Open data folder": "เปิดโฟลเดอร์ข้อมูล",
    "Type Library": "คลังประเภทงาน",
    "+ Add custom type": "+ เพิ่มประเภทเอง",
    "System type": "ประเภทระบบ",
    "My type": "ประเภทของฉัน",
    "Smart classify": "จัดประเภทอัตโนมัติ",
    "Waiting": "รอทำ",
    "Doing": "กำลังทำ",
    "Success": "สำเร็จ",
    "Completed": "เสร็จแล้ว",
    "Waiting List": "รายการรอทำ",
    "Active Work": "กำลังทำ",
    "Complete": "เสร็จแล้ว",
    "TOTAL": "ทั้งหมด",
    "WAITING": "รอทำ",
    "DOING": "กำลังทำ",
    "COMPLETED": "เสร็จแล้ว",
    "All work": "งานทั้งหมด",
    "All types": "ทุกประเภท",
    "Newest": "ใหม่สุด",
    "Oldest": "เก่าสุด",
    "Name": "ชื่อ",
    "Reset": "รีเซ็ต",
    "Smart Search:": "ค้นหาอัจฉริยะ:",
    "Create New Work": "สร้างงานใหม่",
    "Task name": "ชื่องาน",
    "File type": "ประเภทไฟล์",
    "Link type": "ประเภทลิงก์",
    "Note / description": "โน้ต / รายละเอียด",
    "Browse": "เลือกไฟล์",
    "Browse folder": "เลือกโฟลเดอร์",
    "Paste URL": "วาง URL",
    "Save": "บันทึก",
    "Save link": "บันทึกลิงก์",
    "Cancel": "ยกเลิก",
    "Close": "ปิด",
    "Open": "เปิด",
    "Detail": "รายละเอียด",
    "Copy path": "คัดลอก path",
    "Rename": "เปลี่ยนชื่อ",
    "Delete": "ลบ",
    "Templates": "Template",
    "Template Library": "คลัง Template",
    "Health": "สุขภาพระบบ",
    "Calendar": "ปฏิทิน",
    "Version Notes": "บันทึกเวอร์ชัน",
    "Latest Remark": "ล่าสุด",
    "Update Ready": "มีอัปเดตพร้อมใช้",
    "Update now": "อัปเดตตอนนี้",
    "Later": "ไว้ทีหลัง",
    "Downloading Update": "กำลังดาวน์โหลดอัปเดต",
    "Language": "ภาษา",
    "English": "อังกฤษ",
    "ไทย": "ไทย",
}


def localize_text(value):
    if UI_LANGUAGE != "th" or not isinstance(value, str):
        return value
    return TH_TEXT.get(value, value)


def pad_sym(horizontal=0, vertical=0):
    return ft.Padding(horizontal, vertical, horizontal, vertical)


def pad_only(left=0, top=0, right=0, bottom=0):
    return ft.Padding(left, top, right, bottom)


def border_all(width=1, color=BORDER):
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


CENTER = ft.Alignment(0, 0)


def parse_version(value):
    text = str(value or "0").strip()
    match = re.search(r"(\d+)\.(\d+)\.(\d+)(?:[-._ ]+(\d+))?", text)
    if not match:
        return (0, 0, 0, 0)
    return tuple(int(part or 0) for part in match.groups())


def is_newer_version(candidate, current=APP_VERSION):
    return parse_version(candidate) > parse_version(current)


def is_core_platform_update(candidate, current=APP_VERSION):
    target = parse_version(candidate)
    installed = parse_version(current)
    return target[:2] > installed[:2]


def update_force_reason(candidate, manifest, dismissed_count):
    if bool(manifest.get("required")):
        return "This update is marked as required."
    current = parse_version(APP_VERSION)
    target = parse_version(candidate)
    if target[:2] > current[:2]:
        return "This is a core platform update and will install automatically."
    if target[:2] == current[:2] and target[2] - current[2] >= 2:
        return "This machine is behind by 2 platform patch releases."
    if target[:3] == current[:3] and target[3] - current[3] >= 3:
        return "This machine is 3 small update builds behind."
    if dismissed_count >= 3:
        return "This update was skipped 3 times."
    return ""


def normalize_update_manifest(raw):
    if not isinstance(raw, dict):
        return {}
    version = str(raw.get("version") or "").strip()
    if not version:
        return {}
    notes = raw.get("notes") or raw.get("changes") or []
    if isinstance(notes, str):
        notes = [line.strip() for line in notes.splitlines() if line.strip()]
    if not isinstance(notes, list):
        notes = []
    try:
        installer_size = max(0, int(raw.get("installer_size") or 0))
    except (TypeError, ValueError):
        installer_size = 0
    return {
        "version": version,
        "installer_url": str(raw.get("installer_url") or raw.get("download_url") or raw.get("url") or "").strip(),
        "installer_sha256": str(raw.get("installer_sha256") or "").strip().lower(),
        "installer_size": installer_size,
        "release_date": str(raw.get("release_date") or raw.get("date") or "").strip(),
        "required": bool(raw.get("required") or raw.get("force")),
        "notes": [str(item) for item in notes],
    }


def direct_download_url(url):
    return str(url or "").strip()


def cachebusted_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}t={int(time.time())}"


def remote_file_size(url, timeout=12):
    try:
        request = urllib.request.Request(cachebusted_url(url), method="HEAD", headers={"User-Agent": f"SA-CHECK/{APP_VERSION}"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.headers.get("content-length") or 0)
    except Exception:
        return 0


def read_update_url(url, max_bytes=2 * 1024 * 1024, timeout=7):
    url = str(url or "").strip()
    separator = "&" if "?" in url else "?"
    url = f"{url}{separator}t={int(time.time())}"
    request = urllib.request.Request(url, headers={"User-Agent": f"SA-CHECK/{APP_VERSION}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(max_bytes)


def task_icon(task_type):
    mapping = {
        "Word": (ft.Icons.ARTICLE_OUTLINED, "#2563EB"),
        "Excel": (ft.Icons.TABLE_CHART_OUTLINED, "#16A34A"),
        "Google Sheet": (ft.Icons.TABLE_CHART_OUTLINED, "#16A34A"),
        "Miro": (ft.Icons.DASHBOARD_CUSTOMIZE_OUTLINED, "#D97706"),
        "Web": (ft.Icons.LANGUAGE_ROUNDED, "#2563EB"),
        "Link": (ft.Icons.LINK_ROUNDED, "#0F766E"),
        "Project": (ft.Icons.FOLDER_OUTLINED, "#8B5CF6"),
    }
    return mapping.get(task_type, (ft.Icons.DESCRIPTION_OUTLINED, "#64748B"))


NAV_BG = "#08111F"
NAV_ACTIVE = "#1D4ED8"


def dropdown(width, value, options, on_select=None):
    return ft.Dropdown(
        width=width,
        height=44,
        value=value,
        options=[ft.dropdown.Option(option) for option in options],
        border_radius=12,
        border_color=BORDER,
        border_width=1,
        focused_border_color=ACCENT,
        focused_border_width=2,
        bgcolor=WHITE,
        fill_color=WHITE,
        filled=True,
        text_size=13,
        color=TEXT,
        text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_700, color=TEXT),
        content_padding=pad_sym(horizontal=13),
        hover_color="#F1F5F9",
        elevation=6,
        on_select=on_select,
    )


ALERT_STYLES = {
    "success": {
        "bg": "#ECFDF5",
        "fg": "#047857",
        "border": "#A7F3D0",
        "icon": ft.Icons.CHECK_CIRCLE_OUTLINE,
    },
    "info": {
        "bg": "#EFF6FF",
        "fg": "#1D4ED8",
        "border": "#BFDBFE",
        "icon": ft.Icons.INFO_OUTLINE,
    },
    "warning": {
        "bg": "#FFFBEB",
        "fg": "#B45309",
        "border": "#FDE68A",
        "icon": ft.Icons.WARNING_AMBER_ROUNDED,
    },
    "danger": {
        "bg": "#FEF2F2",
        "fg": "#DC2626",
        "border": "#FECACA",
        "icon": ft.Icons.ERROR_OUTLINE,
    },
}


def alert_kind(title, message=""):
    text = f"{title} {message}".lower()
    danger_words = ("failed", "error", "cannot", "delete failed", "not found", "missing item", "invalid url")
    warning_words = ("missing", "invalid", "already", "unsupported", "nothing to", "folder not found")
    success_words = ("copied", "saved", "updated", "ready", "complete", "deleted", "added", "created", "restored", "synced", "used")
    if any(word in text for word in danger_words):
        return "danger"
    if any(word in text for word in warning_words):
        return "warning"
    if any(word in text for word in success_words):
        return "success"
    return "info"


def show_message(page, title, message, kind=None):
    style = ALERT_STYLES.get(kind or alert_kind(title, message), ALERT_STYLES["info"])
    snack = ft.SnackBar(
        content=ft.Container(
            border=border_all(1, style["border"]),
            border_radius=14,
            padding=pad_sym(horizontal=12, vertical=10),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(style["icon"], size=19, color=style["fg"]),
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text(title, color=style["fg"], size=13, weight=ft.FontWeight.W_900),
                            ft.Text(message, color=style["fg"], size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                ],
            ),
        ),
        bgcolor=style["bg"],
        duration=3200,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()


def show_windows_toast(title, message):
    safe_title = html.escape(str(title or APP_NAME))[:120]
    safe_message = html.escape(str(message or ""))[:220]
    xml = f"""
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{safe_title}</text>
      <text>{safe_message}</text>
    </binding>
  </visual>
</toast>
""".strip()
    script = f"""
try {{
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
  [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
  $xml = @'
{xml}
'@
  $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
  $doc.LoadXml($xml)
  $toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{APP_NAME}").Show($toast)
}} catch {{ }}
"""
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception:
        pass


def row_action_button(label, icon, on_click, width=124, primary=False):
    return ft.Button(
        label,
        icon=icon,
        on_click=on_click,
        width=width,
        height=36,
        style=ft.ButtonStyle(
            bgcolor=TEXT if primary else "#F8FAFC",
            color=WHITE if primary else "#1E3A8A",
            overlay_color="#1E293B" if primary else "#DBEAFE",
            padding=pad_sym(horizontal=8, vertical=0),
            shape=ft.RoundedRectangleBorder(radius=999),
            side=ft.BorderSide(1, "#CBD5E1" if not primary else TEXT),
            mouse_cursor=ft.MouseCursor.CLICK,
            animation_duration=120,
        ),
    )


TYPE_PALETTE = {
    "Word": ("#EFF6FF", "#DBEAFE", "#2563EB"),
    "Excel": ("#ECFDF5", "#BBF7D0", "#16A34A"),
    "Google Sheet": ("#ECFDF5", "#A7F3D0", "#059669"),
    "Miro": ("#FEF9C3", "#FDE68A", "#D97706"),
    "Web": ("#ECFEFF", "#A5F3FC", "#0891B2"),
    "Project": ("#F5F3FF", "#DDD6FE", "#7C3AED"),
    "Canva": ("#FDF2F8", "#FBCFE8", "#DB2777"),
    "PDF": ("#FEF2F2", "#FECACA", "#DC2626"),
    "Slide": ("#FFF7ED", "#FED7AA", "#EA580C"),
    "Figma": ("#F5F3FF", "#DDD6FE", "#A855F7"),
    "Diagram": ("#ECFEFF", "#A5F3FC", "#0891B2"),
    "Library": ("#F5F3FF", "#DDD6FE", "#7C3AED"),
    "Image": ("#FDF2F8", "#FBCFE8", "#EC4899"),
    "Video": ("#FEF2F2", "#FECACA", "#EF4444"),
    "Audio": ("#F0FDFA", "#99F6E4", "#14B8A6"),
    "Archive": ("#FEFCE8", "#FDE68A", "#A16207"),
    "Code": ("#F8FAFC", "#CBD5E1", "#334155"),
    "Data": ("#F0FDFA", "#99F6E4", "#0F766E"),
    "Link": ("#ECFEFF", "#BAE6FD", "#0284C7"),
    "Other": ("#F8FAFC", "#E2E8F0", "#64748B"),
}


AUTO_TYPE_PALETTE = [
    ("#EFF6FF", "#BFDBFE", "#2563EB"),
    ("#ECFEFF", "#A5F3FC", "#0891B2"),
    ("#F0FDFA", "#99F6E4", "#0F766E"),
    ("#F0FDF4", "#BBF7D0", "#16A34A"),
    ("#F7FEE7", "#D9F99D", "#65A30D"),
    ("#FEFCE8", "#FDE68A", "#CA8A04"),
    ("#FFFBEB", "#FED7AA", "#D97706"),
    ("#FFF7ED", "#FDBA74", "#EA580C"),
    ("#FEF2F2", "#FECACA", "#DC2626"),
    ("#FFF1F2", "#FDA4AF", "#E11D48"),
    ("#FDF2F8", "#FBCFE8", "#DB2777"),
    ("#FDF4FF", "#F0ABFC", "#C026D3"),
    ("#FAF5FF", "#DDD6FE", "#9333EA"),
    ("#EEF2FF", "#C7D2FE", "#4F46E5"),
    ("#F8FAFC", "#CBD5E1", "#475569"),
]


def _valid_hex_color(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    return len(value) == 7 and value.startswith("#") and all(char in "0123456789abcdefABCDEF" for char in value[1:])


def _mix_hex(foreground, background="#FFFFFF", amount=0.88):
    try:
        fg = tuple(int(foreground[index:index + 2], 16) for index in (1, 3, 5))
        bg = tuple(int(background[index:index + 2], 16) for index in (1, 3, 5))
    except (TypeError, ValueError):
        return background
    mixed = tuple(round(fg_part * (1 - amount) + bg_part * amount) for fg_part, bg_part in zip(fg, bg))
    return "#" + "".join(f"{part:02X}" for part in mixed)


def auto_type_style(file_type):
    name = str(file_type or "Other").strip() or "Other"
    try:
        config = file_type_config(name)
    except NameError:
        config = {}
    accent = str(config.get("color", "")).strip()
    if _valid_hex_color(accent):
        return _mix_hex(accent, "#FFFFFF", 0.90), _mix_hex(accent, "#FFFFFF", 0.72), accent
    index = sum(ord(char) for char in name.casefold()) % len(AUTO_TYPE_PALETTE)
    return AUTO_TYPE_PALETTE[index]


def type_style(file_type):
    return TYPE_PALETTE.get(file_type or "Other") or auto_type_style(file_type)


def bytes_label(size):
    try:
        value = float(size or 0)
    except (TypeError, ValueError):
        value = 0.0
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def update_size_label(downloaded, total=None):
    if total and total > 0:
        return f"{bytes_label(downloaded)} / {bytes_label(total)}"
    return f"{bytes_label(downloaded)} downloaded"


from core.flet_constants import (  # noqa: E402
    ACCENT,
    BG,
    BORDER,
    DOING_BG,
    DOING_TEXT,
    DONE_BG,
    DONE_TEXT,
    FILE_TYPES,
    MUTED,
    MUTED_2,
    PRIMARY,
    SCREEN_BOARD,
    SCREEN_BROWSER,
    STATUS_BY_FILTER,
    STATUS_DONE,
    STATUS_LABELS,
    STATUS_PENDING,
    STATUS_PROGRESS,
    TEXT,
    WAITING_BG,
    WAITING_TEXT,
    WHITE,
)
from core.flet_data import (  # noqa: E402
    apply_status_date,
    broken_items,
    create_snapshot,
    create_custom_file_type,
    create_task_from_source,
    create_task_from_tool,
    create_task_from_template,
    create_template_from_source,
    delete_item_target,
    ensure_status_folders,
    file_meta,
    file_type_config,
    infer_type,
    event_occurs_on,
    list_work_items,
    list_work_items_page,
    list_snapshots,
    load_activity_log,
    load_calendar_events as load_persisted_calendar_events,
    load_settings,
    load_tasks,
    load_templates,
    load_undo_stack,
    make_task,
    normalized_file_key,
    open_folder,
    open_target,
    pop_undo,
    push_undo,
    rename_task_target,
    retry_file_operation,
    resolve_add_type,
    restore_snapshot,
    runtime_file_types,
    safe_item_name,
    save_settings,
    save_calendar_events as save_persisted_calendar_events,
    save_tasks,
    save_templates,
    sync_from_work,
    template_folder,
    status_folder,
    type_color_choices,
    unique_target_path,
    update_template_record,
    item_target,
    log_activity,
)
from core.create_tools import CREATE_TOOLS  # noqa: E402
from ui.virtual_list import DEFAULT_BATCH_SIZE, next_visible_limit, visible_slice  # noqa: E402
import core.flet_constants as theme_constants  # noqa: E402
import ui.flet_widgets as widget_theme  # noqa: E402
from ui.flet_widgets import (  # noqa: E402
    CENTER,
    add_destination_header,
    animated_status_pill,
    border_all,
    breathe_glow,
    breathing_badge,
    dropdown,
    nav_button,
    pad_only,
    pad_sym,
    pulse_dot,
    stat_card,
    task_icon,
)


SCREEN_CALENDAR = "calendar"
SCREEN_TEMPLATES = "templates"
SCREEN_SETTINGS = "settings"
SCREEN_HEALTH = "health"


def install_pointer_feedback():
    if getattr(ft, "_sacheck_pointer_feedback", False):
        return
    ft._sacheck_pointer_feedback = True

    def localize_args(args, kwargs, keys=("text", "value", "label", "hint_text", "tooltip")):
        args = list(args)
        if args and isinstance(args[0], str):
            args[0] = localize_text(args[0])
        for key in keys:
            if isinstance(kwargs.get(key), str):
                kwargs[key] = localize_text(kwargs[key])
        return tuple(args), kwargs

    original_text_init = ft.Text.__init__

    def patched_text_init(self, *args, **kwargs):
        args, kwargs = localize_args(args, kwargs, keys=("value",))
        original_text_init(self, *args, **kwargs)

    ft.Text.__init__ = patched_text_init

    def clickable_style(style=None, overlay="#E2E8F0"):
        style = style or ft.ButtonStyle()
        if getattr(style, "mouse_cursor", None) is None:
            style.mouse_cursor = ft.MouseCursor.CLICK
        if getattr(style, "overlay_color", None) is None:
            style.overlay_color = overlay
        if getattr(style, "animation_duration", None) is None:
            style.animation_duration = 120
        return style

    for control_name in ("Button", "TextButton", "PopupMenuButton"):
        control_class = getattr(ft, control_name)
        original_init = control_class.__init__

        def patched_init(self, *args, _original_init=original_init, **kwargs):
            args, kwargs = localize_args(args, kwargs)
            kwargs["style"] = clickable_style(kwargs.get("style"))
            _original_init(self, *args, **kwargs)

        control_class.__init__ = patched_init

    original_icon_init = ft.IconButton.__init__

    def patched_icon_init(self, *args, **kwargs):
        args, kwargs = localize_args(args, kwargs)
        kwargs.setdefault("mouse_cursor", ft.MouseCursor.CLICK)
        kwargs.setdefault("hover_color", "#E2E8F0")
        kwargs.setdefault("splash_color", "#CBD5E1")
        original_icon_init(self, *args, **kwargs)

    ft.IconButton.__init__ = patched_icon_init

    original_text_field_init = ft.TextField.__init__

    def patched_text_field_init(self, *args, **kwargs):
        args, kwargs = localize_args(args, kwargs)
        if DARK_UI:
            kwargs["bgcolor"] = adapt_theme_color(kwargs.get("bgcolor", WHITE))
            kwargs["border_color"] = adapt_theme_color(kwargs.get("border_color", BORDER))
            kwargs["focused_border_color"] = adapt_theme_color(kwargs.get("focused_border_color", PRIMARY))
            kwargs.setdefault("color", TEXT)
            kwargs.setdefault("hint_style", ft.TextStyle(color=MUTED_2))
        original_text_field_init(self, *args, **kwargs)

    ft.TextField.__init__ = patched_text_field_init

    if hasattr(ft, "Dropdown"):
        original_dropdown_init = ft.Dropdown.__init__

        def patched_dropdown_init(self, *args, **kwargs):
            args, kwargs = localize_args(args, kwargs)
            if DARK_UI:
                kwargs["bgcolor"] = adapt_theme_color(kwargs.get("bgcolor", WHITE))
                kwargs["border_color"] = adapt_theme_color(kwargs.get("border_color", BORDER))
                kwargs["focused_border_color"] = adapt_theme_color(kwargs.get("focused_border_color", PRIMARY))
                kwargs.setdefault("color", TEXT)
            original_dropdown_init(self, *args, **kwargs)

        ft.Dropdown.__init__ = patched_dropdown_init

    original_container_init = ft.Container.__init__

    def patched_container_init(self, *args, **kwargs):
        if DARK_UI and "bgcolor" in kwargs:
            kwargs["bgcolor"] = adapt_theme_color(kwargs.get("bgcolor"))
        if kwargs.get("on_click") and kwargs.get("ink") is None:
            content = kwargs.get("content")
            input_controls = (ft.TextField, ft.Dropdown)
            if not isinstance(content, input_controls):
                kwargs["ink"] = True
                kwargs.setdefault("ink_color", "#E2E8F0")
        original_container_init(self, *args, **kwargs)

    ft.Container.__init__ = patched_container_init


def selected_app_theme(settings):
    name = str(settings.get("app_theme_preset") or "Ocean Pro")
    return name if name in APP_THEME_PRESETS else "Ocean Pro"


def adapt_theme_color(color):
    if not DARK_UI or not isinstance(color, str):
        return color
    value = color.strip().lower()
    dark_map = {
        "#ffffff": "#111827",
        "#fff": "#111827",
        "#f8fafc": "#0B1220",
        "#f8fbff": "#111827",
        "#eff6ff": "#172554",
        "#eef2ff": "#1E1B4B",
        "#f1f5f9": "#1F2937",
        "#f0fdf4": "#052E1A",
        "#ecfdf5": "#052E1A",
        "#fffbeb": "#422006",
        "#fff7ed": "#431407",
        "#fef2f2": "#450A0A",
        "#fff1f2": "#4C0519",
        "#fdf2f8": "#500724",
        "#f5f3ff": "#2E1065",
    }
    return dark_map.get(value, color)


def color_luminance(color):
    text = str(color or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(part * 2 for part in text)
    if len(text) != 6:
        return 1.0
    try:
        channels = [int(text[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    except ValueError:
        return 1.0
    adjusted = [value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * adjusted[0] + 0.7152 * adjusted[1] + 0.0722 * adjusted[2]


def contrast_ratio(foreground, background):
    light = max(color_luminance(foreground), color_luminance(background))
    dark = min(color_luminance(foreground), color_luminance(background))
    return (light + 0.05) / (dark + 0.05)


def readable_text_for(background):
    return "#0F172A" if contrast_ratio("#0F172A", background) >= contrast_ratio("#F8FAFC", background) else "#F8FAFC"


def ensure_palette_contrast(palette):
    palette = dict(palette)
    surface = palette.get("surface", "#FFFFFF")
    bg = palette.get("bg", surface)
    if contrast_ratio(palette.get("text", "#0F172A"), surface) < 4.5:
        palette["text"] = readable_text_for(surface)
    if contrast_ratio(palette.get("muted", "#64748B"), surface) < 3.2:
        palette["muted"] = "#CBD5E1" if color_luminance(surface) < 0.35 else "#475569"
    if contrast_ratio(palette.get("muted_2", "#94A3B8"), surface) < 2.6:
        palette["muted_2"] = "#94A3B8" if color_luminance(surface) < 0.35 else "#64748B"
    if contrast_ratio(palette.get("border", "#E2E8F0"), bg) < 1.25:
        palette["border"] = "#334155" if color_luminance(bg) < 0.35 else "#CBD5E1"
    return palette


def apply_app_theme(settings):
    global BG, WHITE, TEXT, MUTED, MUTED_2, BORDER, PRIMARY, NAV_BG, NAV_ACTIVE, DARK_UI
    DARK_UI = settings.get("theme") == "Dark"
    palette = dict(APP_THEME_PRESETS[selected_app_theme(settings)])
    if DARK_UI:
        palette.update(
            {
                "bg": "#0B1220",
                "surface": "#111827",
                "text": "#E5E7EB",
                "muted": "#CBD5E1",
                "muted_2": "#94A3B8",
                "border": "#334155",
                "nav": "#020617",
                "soft": "#172554",
            }
        )
    palette = ensure_palette_contrast(palette)
    BG = palette["bg"]
    WHITE = palette["surface"]
    TEXT = palette["text"]
    MUTED = palette["muted"]
    MUTED_2 = palette["muted_2"]
    BORDER = palette["border"]
    PRIMARY = palette["primary"]
    NAV_BG = palette["nav"]
    NAV_ACTIVE = palette["nav_active"]
    themed_modules = [theme_constants, widget_theme]
    for module_name in (
        "ui.dialogs",
        "ui.screens.board",
        "ui.screens.browser",
        "ui.screens.calendar_screen",
        "ui.screens.health",
        "ui.screens.settings_screen",
        "ui.screens.templates",
    ):
        module = sys.modules.get(module_name)
        if module is not None:
            themed_modules.append(module)
    for module in themed_modules:
        module.BG = BG
        module.WHITE = WHITE
        module.TEXT = TEXT
        module.MUTED = MUTED
        module.MUTED_2 = MUTED_2
        module.BORDER = BORDER
        module.PRIMARY = PRIMARY
    return palette


def app_logo_control(size=44, radius=14):
    return ft.Container(
        width=size,
        height=size,
        border_radius=radius,
        bgcolor="#EEF2FF",
        alignment=CENTER,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Image(src=APP_LOGO_PATH, width=size, height=size, fit=ft.BoxFit.COVER, error_content=ft.Text("SA", size=max(11, size // 3), weight=ft.FontWeight.W_900, color=TEXT)),
    )


def dashboard_main(page: ft.Page, startup_result=None):
    global UI_LANGUAGE
    install_pointer_feedback()
    all_tasks = load_tasks()
    settings = load_settings()
    UI_LANGUAGE = str(settings.get("language") or "en").lower()
    apply_app_theme(settings)
    root_work = work_folder()
    current_browser_path = {"path": root_work}
    startup_manifest = getattr(startup_result, "manifest", None) if startup_result else None
    startup_update_available = bool(getattr(startup_result, "update_available", False)) if startup_result else False
    state = {
        "screen": SCREEN_OVERVIEW,
        "search": "",
        "view": "All work",
        "type": "All types",
        "sort": "Newest",
        "browser_limit": 160,
        "browser_search": "",
        "browser_sort": "Name",
        "browser_desc": False,
        "browser_selected": "",
        "browser_sub_search": {},
        "group_limits": {},
        "board_grouped": True,
        "settings_search": "",
        "last_sync_check": datetime.now().timestamp(),
        "syncing": False,
        "sync_phase": "idle",
        "sync_message": "Waiting for scheduled sync",
        "sync_error": "",
        "sync_state_token": "",
        "refreshing": False,
        "refresh_token": "",
        "closed": False,
        "closing": False,
        "online_status": (
            "online"
            if getattr(startup_result, "online_checked", False)
            else "offline"
            if startup_result and not getattr(startup_result, "online_enabled", False)
            else "checking"
        ),
        "update_manifest": startup_manifest,
        "update_available": startup_update_available,
        "update_checking": False,
        "update_installing": False,
        "last_update_check": time.time() if getattr(startup_result, "online_checked", False) else 0,
        "update_prompted_versions": set(),
        "health_filter": "All",
    }
    shutdown_event = threading.Event()
    sync_lock = threading.Lock()

    def record_runtime_failure(component, exc, **details):
        message = str(exc or "Unknown error").strip() or "Unknown error"
        payload = {
            "component": component,
            "error_type": type(exc).__name__ if exc is not None else "UnknownError",
            "error": message,
            **details,
        }
        trace = traceback.format_exc()
        if trace and "NoneType: None" not in trace:
            payload["traceback"] = trace[-6000:]
        try:
            log_activity(f"{component} failed", message, payload)
        except Exception:
            pass
        return message

    def set_sync_phase(phase, message="", error=None):
        phase = phase if phase in {"idle", "syncing", "success", "error"} else "error"
        token = uuid.uuid4().hex
        state["sync_phase"] = phase
        state["sync_message"] = message or {
            "idle": "Waiting for scheduled sync",
            "syncing": "Synchronizing Work folders",
            "success": "Synchronization complete",
            "error": "Synchronization failed",
        }[phase]
        state["sync_error"] = str(error or "") if phase == "error" else ""
        state["sync_state_token"] = token
        try:
            update_sidebar()
            page.update()
        except (NameError, RuntimeError):
            pass
        if phase == "success":
            def reset_success():
                if shutdown_event.wait(60):
                    return
                if state.get("sync_state_token") == token and state.get("sync_phase") == "success":
                    set_sync_phase("idle", "Waiting for scheduled sync")

            page.run_thread(reset_success)

    def fail_sync(component, exc, **details):
        message = record_runtime_failure(component, exc, **details)
        set_sync_phase("error", f"{component} failed", message)
        return message

    page.title = APP_NAME
    try:
        page.window.icon = APP_ICON_PATH
        page.window.title_bar_hidden = True
        page.window.title_bar_buttons_hidden = True
    except Exception:
        pass
    page.window.width = 1920
    page.window.height = 1080
    page.window.min_width = 1280
    page.window.min_height = 760
    page.window.maximized = True
    page.padding = 0
    page.spacing = 0
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK if settings.get("theme") == "Dark" else ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family="Segoe UI")
    file_picker = ft.FilePicker()
    if hasattr(page, "services"):
        page.services.append(file_picker)
    else:
        page.overlay.append(file_picker)
    page.update()

    def native_directory_picker(title):
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory(title=title)
            root.destroy()
            return selected or ""
        except Exception:
            return ""

    async def pick_directory(title):
        try:
            selected = await file_picker.get_directory_path(dialog_title=title)
            if selected:
                return selected
        except Exception:
            pass
        return native_directory_picker(title)

    def profile_media_path():
        value = str(settings.get("profile_media_path") or "").strip()
        if value and Path(value).exists():
            return value
        return APP_LOGO_PATH

    def app_language():
        value = str(settings.get("language") or "en").lower()
        return value if value in UI_TEXT else "en"

    def t(key):
        lang = app_language()
        return UI_TEXT.get(lang, UI_TEXT["en"]).get(key, UI_TEXT["en"].get(key, key))

    def profile_media_control(size=48):
        source = profile_media_path()
        suffix = Path(source).suffix.lower()
        if suffix in PROFILE_IMAGE_EXTENSIONS:
            return ft.Image(src=source, width=size, height=size, fit=ft.BoxFit.COVER, error_content=ft.Text("SA", size=15, weight=ft.FontWeight.W_900, color=WHITE))
        return ft.Image(src=APP_LOGO_PATH, width=size, height=size, fit=ft.BoxFit.COVER, error_content=ft.Text("SA", size=15, weight=ft.FontWeight.W_900, color=WHITE))

    def set_offline_mode(enabled, render=True):
        settings["offline_mode"] = bool(enabled)
        save_settings(settings)
        state["online_status"] = "offline" if enabled else "checking"
        if render:
            update_sidebar()
            page.update()
        if not enabled:
            check_for_updates(manual=False)

    def confirm_connectivity_change(enabled):
        title = "Turn Online Checks On" if enabled else "Turn Offline Mode On"
        message = (
            "SA CHECK will use internet only for update checks and update downloads. Work files still stay local and offline-first."
            if enabled
            else "SA CHECK will stop checking for updates. Work board, folders, calendar, and local tools keep working offline."
        )

        def apply_choice(_event):
            page.pop_dialog()
            set_offline_mode(not enabled)
            show_message(page, "Connectivity", "Online update checks enabled." if enabled else "Offline mode enabled.")

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.WIFI if enabled else ft.Icons.WIFI_OFF, color=PRIMARY if enabled else "#DC2626"), ft.Text(title, size=20, weight=ft.FontWeight.W_900, color=TEXT)]),
                content=ft.Text(message, size=13, color=MUTED),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), update_sidebar(), page.update())),
                    ft.Button("Confirm", icon=ft.Icons.CHECK, on_click=apply_choice, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        page.update()

    def file_types():
        return runtime_file_types()

    def duplicate_waiting_target(name, source, file_type):
        try:
            resolved_type = resolve_add_type(source, file_type)
            folder = status_folder(STATUS_PENDING, resolved_type)
            safe_name = safe_item_name(name, "Untitled task")
            if str(source).strip().startswith(("http://", "https://")):
                target = folder / f"{safe_name}.url"
            else:
                source_path = Path(source)
                suffix = source_path.suffix if source_path.is_file() else ""
                target = folder / f"{safe_name}{suffix}"
            return target if target.exists() else None
        except Exception:
            return None

    def run_with_duplicate_guard(name, source, file_type, action):
        duplicate = duplicate_waiting_target(name, source, file_type)
        if not duplicate:
            action()
            return

        def continue_copy(_event):
            page.pop_dialog()
            action()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.CONTENT_COPY, color="#D97706"), ft.Text("Duplicate name found", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                content=ft.Column(
                    width=520,
                    height=150,
                    spacing=12,
                    controls=[
                        ft.Text(f"{APP_NAME} found an item with the same name in Waiting. The new copy will be saved with a safe number suffix, so the original file will not be overwritten.", size=13, color=MUTED),
                        ft.Container(border=border_all(1, "#FED7AA"), border_radius=12, bgcolor="#FFFBEB", padding=12, content=ft.Text(str(duplicate), size=12, color="#92400E", selectable=True)),
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Create numbered copy", icon=ft.Icons.ADD_TASK_OUTLINED, on_click=continue_copy, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def sync_interval_seconds():
        try:
            return max(3, int(settings.get("sync_interval_seconds") or 5))
        except (TypeError, ValueError):
            return 5

    def update_check_interval_seconds():
        try:
            minutes = int(settings.get("update_check_interval_minutes") or DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES)
        except (TypeError, ValueError):
            minutes = DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES
        return max(1, minutes) * 60

    header_title = ft.Text("Project Overview", size=24, weight=ft.FontWeight.W_800, color=TEXT)
    header_subtitle = ft.Text(f"{APP_NAME} / Work Board", size=13, weight=ft.FontWeight.W_700, color=MUTED)
    progress_badge = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=PRIMARY)
    main_body = ft.Column(spacing=14, expand=True)
    search_field = ft.TextField(
        hint_text="Search name, note, path, type, status, date...",
        prefix_icon=ft.Icons.SEARCH,
        height=40,
        expand=True,
        border_radius=10,
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor="#F8FAFC",
        text_size=14,
        color=TEXT,
        content_padding=pad_sym(horizontal=14),
    )

    def status_theme(status):
        selected = settings.get("status_theme_preset") or "Classic Blue"
        palette = STATUS_THEME_PRESETS.get(selected, STATUS_THEME_PRESETS["Classic Blue"])
        return palette.get(status, STATUS_THEME_PRESETS["Classic Blue"][status])

    def save_and_render(message=None):
        save_tasks(all_tasks)
        render_current()
        if message:
            show_message(page, APP_NAME, message)

    def set_work_folder_path(selected_path):
        nonlocal root_work
        selected = Path(selected_path).expanduser()
        selected.mkdir(parents=True, exist_ok=True)
        settings["work_folder_path"] = str(selected)
        settings.pop("root_work", None)
        save_settings(settings)
        root_work = work_folder()
        current_browser_path["path"] = root_work
        ensure_status_folders()
        synced_tasks, _synced_templates, _changed = sync_from_work(force=True)
        all_tasks.clear()
        all_tasks.extend(synced_tasks)
        state["last_sync_check"] = datetime.now().timestamp()
        state["group_limits"] = {}
        return root_work

    def remember_task_action(action, task, before):
        push_undo({"kind": "task_restore", "action": action, "task_id": task.get("id"), "before": before, "after": dict(task)})
        log_activity(action, f"{task.get('name', 'Untitled task')} updated.", {"task_id": task.get("id"), "before": before, "after": dict(task)})

    def undo_last(_event=None):
        action = pop_undo()
        if not action:
            show_message(page, "Undo", "Nothing to undo.")
            return
        if action.get("kind") != "task_restore":
            show_message(page, "Undo", "Unsupported undo item.")
            return
        before = action.get("before") or {}
        after = action.get("after") or {}
        task_id = action.get("task_id")
        task = next((item for item in all_tasks if item.get("id") == task_id), None)
        if not task:
            all_tasks.append(before)
            save_and_render("Restored task.")
            return
        before_target = before.get("link") or before.get("shortcut_path") or ""
        after_target = after.get("link") or after.get("shortcut_path") or ""
        try:
            if before_target and after_target and before_target != after_target and Path(after_target).exists() and not before_target.startswith(("http://", "https://")):
                destination = Path(before_target)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    retry_file_operation(lambda: Path(after_target).rename(destination), label=f"Undo move {Path(after_target).name}")
        except Exception as exc:
            show_message(page, "Undo file move failed", str(exc))
        task.clear()
        task.update(before)
        save_tasks(all_tasks)
        log_activity("Undo", f"Reverted {before.get('name', 'task')}.", {"task_id": task_id})
        render_current()
        show_message(page, "Undo", "Last change reverted.")

    def add_or_update_from_path(path):
        path = Path(path)
        key = str(path).casefold()
        if any((task.get("file_key") or task.get("link", "").casefold()) == key for task in all_tasks):
            show_message(page, "Already exists", "This item is already on the board.")
            return
        task = make_task(path.stem if path.is_file() else path.name, str(path), target_kind="folder" if path.is_dir() else "file")
        all_tasks.append(task)
        log_activity("Add to board", f"{task.get('name')} was added from Work Browser.", {"target": str(path)})
        save_and_render("Added to board.")

    def filtered_tasks():
        query = state["search"].strip().casefold()
        raw_tokens = [part for part in query.split() if part]
        tokens = []
        smart_status = None
        smart_type = None
        stale_days = None
        date_filter = None
        smart_search_on = settings.get("smart_search_enabled", True)
        default_stale_days = int(settings.get("stale_doing_days") or 7)
        type_aliases = {item.casefold(): item for item in file_types()}
        status_aliases = {
            "waiting": STATUS_PENDING,
            "wait": STATUS_PENDING,
            "todo": STATUS_PENDING,
            "pending": STATUS_PENDING,
            "doing": STATUS_PROGRESS,
            "active": STATUS_PROGRESS,
            "progress": STATUS_PROGRESS,
            "success": STATUS_DONE,
            "done": STATUS_DONE,
            "complete": STATUS_DONE,
            "completed": STATUS_DONE,
        }
        today_text = date.today().isoformat()
        for token in raw_tokens:
            cleaned = token.strip()
            if smart_search_on and cleaned in status_aliases:
                smart_status = status_aliases[cleaned]
                continue
            if smart_search_on and cleaned in type_aliases:
                smart_type = type_aliases[cleaned]
                continue
            if smart_search_on and cleaned in {"today", "วันนี้"}:
                date_filter = today_text
                continue
            if smart_search_on and cleaned in {"stale", "zombie", "ค้าง", "ค้างนาน"}:
                stale_days = max(stale_days or 0, default_stale_days)
                continue
            if smart_search_on and cleaned.endswith("d") and cleaned[:-1].isdigit():
                stale_days = int(cleaned[:-1])
                continue
            if smart_search_on and cleaned.startswith(">") and cleaned[1:].isdigit():
                stale_days = int(cleaned[1:])
                continue
            tokens.append(cleaned)
        view_status = STATUS_BY_FILTER.get(state["view"])
        selected_type = state["type"]
        items = []
        for task in all_tasks:
            haystack = " ".join(
                str(task.get(key, ""))
                for key in ["name", "type", "detected_type", "note", "link", "shortcut_path", "status", "date_added", "done_date", "project_stack"]
            ).casefold()
            task_type = task.get("type", "Other")
            if tokens and not all(token in haystack for token in tokens):
                continue
            if smart_search_on and smart_status and task.get("status") != smart_status:
                continue
            if smart_search_on and smart_type and task_type != smart_type:
                continue
            if smart_search_on and stale_days is not None:
                try:
                    task_age = (date.today() - datetime.strptime(task_calendar_date(task), "%Y-%m-%d").date()).days
                except ValueError:
                    task_age = 0
                if task_age < stale_days:
                    continue
            if smart_search_on and date_filter and task_calendar_date(task) != date_filter:
                continue
            if view_status and task.get("status") != view_status:
                continue
            if selected_type != "All types" and task_type != selected_type:
                continue
            items.append(task)
        if state["sort"] == "Name":
            items.sort(key=lambda task: task.get("name", "").casefold())
        elif state["sort"] == "Oldest":
            items.sort(key=lambda task: task.get("date_added", ""))
        elif state["sort"] == "Priority":
            items.sort(key=lambda task: task.get("priority", 0) or 0, reverse=True)
        elif state["sort"] == "Progress":
            items.sort(key=lambda task: task.get("progress", 0) or 0, reverse=True)
        else:
            items.sort(key=lambda task: task.get("date_added", ""), reverse=True)
        return items

    def reset_filters(render=True):
        state.update({"search": "", "view": "All work", "type": "All types", "sort": "Newest"})
        state["group_limits"] = {}
        search_field.value = ""
        if render:
            state["screen"] = SCREEN_BOARD
            render_current()

    def breadcrumb_controls():
        try:
            base = root_work.resolve()
            current = current_browser_path["path"].resolve()
        except OSError:
            base = root_work
            current = current_browser_path["path"]
        parts = [("Work", base)]
        if str(current).casefold().startswith(str(base).casefold()):
            relative = current.relative_to(base)
            walker = base
            for part in relative.parts:
                walker = walker / part
                parts.append((part, walker))
        controls = []
        for index, (label, path) in enumerate(parts):
            if index:
                controls.append(ft.Text("/", color=MUTED_2, size=14))
            controls.append(ft.TextButton(label, on_click=lambda _e, p=path: go_to_browser_path(p)))
        return controls

    def go_to_browser_path(path):
        if not Path(path).exists():
            show_message(page, "Folder not found", "This folder may have been moved or deleted.")
            current_browser_path["path"] = root_work
        else:
            current_browser_path["path"] = Path(path)
        state.update({"browser_limit": 160, "browser_selected": ""})
        render_current()

    def work_row(path):
        is_dir = path.is_dir()
        item_type = "Project" if is_dir else infer_type(path)
        icon, icon_color = task_icon(item_type)
        path_key = normalized_file_key(str(path))
        is_selected = state.get("browser_selected") == str(path)
        board_task = next((task for task in all_tasks if task.get("file_key") == path_key or normalized_file_key(task.get("link", "")) == path_key), None)
        meta_text = "Folder" if is_dir else file_meta(path)
        if board_task:
            meta_text = f"On board | {STATUS_LABELS.get(board_task.get('status'), 'Waiting')} | {meta_text}"

        def open_item(_e):
            if not path.exists():
                show_message(page, "Missing item", f"This file or folder was moved/deleted outside {APP_NAME}.")
                state["browser_selected"] = ""
                render_current()
                return
            if is_dir:
                go_to_browser_path(path)
            else:
                os.startfile(str(path))

        def add_to_board(_e):
            if board_task:
                show_message(page, "Already on board", "This item is already tracked.")
                return
            add_or_update_from_path(path)

        def open_detail(_e):
            if not path.exists():
                show_message(page, "Missing item", f"This file or folder was moved/deleted outside {APP_NAME}.")
                state["browser_selected"] = ""
                render_current()
                return
            detail_task = board_task or make_task(path.stem if path.is_file() else path.name, str(path), target_kind="folder" if is_dir else "file", task_type=item_type, note=file_meta(path) if path.is_file() else "Folder")
            show_task_detail(page, detail_task, save_and_render, all_tasks)

        def open_in_explorer(_e):
            if not path.exists():
                show_message(page, "Missing item", f"This file or folder was moved/deleted outside {APP_NAME}.")
                state["browser_selected"] = ""
                render_current()
                return
            os.startfile(str(path if is_dir else path.parent))

        async def copy_path(_e):
            await page.clipboard.set(str(path))
            show_message(page, "Copied", "Path copied.")

        def select_item(_event):
            state["browser_selected"] = str(path)
            render_current()

        return ft.Container(
            height=68,
            bgcolor="#EFF6FF" if is_selected else WHITE,
            border=border_all(1, PRIMARY if is_selected else BORDER),
            border_radius=16,
            padding=pad_only(left=14, right=8),
            on_click=select_item,
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=36, height=36, border_radius=10, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=18, color=icon_color)),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(path.name, size=15, weight=ft.FontWeight.W_600, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(meta_text, size=12, color=MUTED_2, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    row_action_button("Open", ft.Icons.OPEN_IN_NEW, open_item, width=104),
                    row_action_button("Detail", ft.Icons.INFO_OUTLINE, open_detail, width=108),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_size=18,
                        icon_color=MUTED_2,
                        items=[
                            ft.PopupMenuItem(content="Already on board" if board_task else "Add to board", icon=ft.Icons.CHECK_CIRCLE_OUTLINE if board_task else ft.Icons.ADD_CIRCLE_OUTLINE, on_click=add_to_board),
                            ft.PopupMenuItem(content="Folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=open_in_explorer),
                            ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_path),
                        ],
                    ),
                ],
            ),
        )

    def auto_sync_from_work(force=False):
        if state.get("syncing") or not sync_lock.acquire(blocking=False):
            return False
        now = datetime.now().timestamp()
        if not force and now - state.get("last_sync_check", 0) < 2:
            sync_lock.release()
            return False
        state["last_sync_check"] = now
        state["syncing"] = True
        set_sync_phase("syncing", "Scheduled Work-folder sync is running")
        try:
            synced_tasks, _synced_templates, changed = sync_from_work(force=force)
            if changed:
                all_tasks.clear()
                all_tasks.extend(synced_tasks)
            set_sync_phase("success", "Work folders synchronized successfully")
            return changed
        except Exception as exc:
            fail_sync("Scheduled sync", exc, force=bool(force))
            return False
        finally:
            state["syncing"] = False
            sync_lock.release()

    def render_error_view(exc):
        header_title.value = "System Guard"
        header_subtitle.value = f"{APP_NAME} / Recovery"
        progress_badge.value = "Recovery"
        main_body.spacing = 16
        main_body.controls = [
            ft.Container(
                border=border_all(1, "#FECACA"),
                border_radius=18,
                bgcolor="#FEF2F2",
                padding=22,
                content=ft.Column(
                    spacing=14,
                    controls=[
                        ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SHIELD_OUTLINED, color="#DC2626"), ft.Text("Something failed, but the app is still running.", size=20, weight=ft.FontWeight.W_900, color=TEXT)]),
                        ft.Text("This recovery screen prevents one broken page from closing SA CHECK. Try returning to the board or opening Settings.", size=13, color=MUTED),
                        ft.Container(border=border_all(1, "#FCA5A5"), border_radius=12, bgcolor=WHITE, padding=12, content=ft.Text(str(exc), size=12, color="#991B1B", selectable=True)),
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Button("Back to board", icon=ft.Icons.DASHBOARD_OUTLINED, on_click=lambda _e: (state.update({"screen": SCREEN_BOARD}), render_current()), style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                                ft.Button("Open Settings", icon=ft.Icons.SETTINGS_OUTLINED, on_click=lambda _e: (state.update({"screen": SCREEN_SETTINGS}), render_current())),
                                ft.Button("Reload data", icon=ft.Icons.REFRESH, on_click=lambda _e: (all_tasks.clear(), all_tasks.extend(load_tasks()), state.update({"screen": SCREEN_BOARD}), render_current())),
                            ],
                        ),
                    ],
                ),
            )
        ]
        try:
            page.update()
        except Exception:
            pass

    def render_current():
        try:
            update_sidebar()
            try:
                quick_add.visible = state["screen"] == SCREEN_OVERVIEW
            except Exception:
                pass
            ctx = DashboardContext(
                page=page,
                state=state,
                settings=settings,
                all_tasks=all_tasks,
                root_work=root_work,
                header_title=header_title,
                header_subtitle=header_subtitle,
                progress_badge=progress_badge,
                main_body=main_body,
                search_field=search_field,
                file_picker=file_picker,
                current_browser_path=current_browser_path,
                render_current=render_current,
                save_and_render=save_and_render,
                sync_now=sync_now,
                pick_directory=pick_directory,
                show_board=show_board,
                show_browser=show_browser,
                show_settings=show_settings,
                show_health=show_health,
                show_calendar=show_calendar,
                show_calendar_event_dialog=show_calendar_event_dialog,
                show_templates=show_templates,
                update_sidebar=update_sidebar,
                check_for_updates=check_for_updates,
                update_channel_url=update_channel_url,
                apply_app_theme=apply_app_theme,
                set_work_folder=set_work_folder_path,
                reset_filters=reset_filters,
                undo_last=undo_last,
                add_or_update_from_path=add_or_update_from_path,
                run_with_duplicate_guard=run_with_duplicate_guard,
                remember_task_action=remember_task_action,
                show_create_new=show_create_new,
                show_add_files=add_files_dialog,
                show_add_link=lambda *_: add_task_dialog("link"),
                show_inline_type_dialog=show_inline_type_dialog,
                show_about=show_about,
                show_help=show_help,
                show_version_notes=show_version_notes,
                status_theme=status_theme,
                file_types=file_types,
                filtered_tasks=filtered_tasks,
                profile_media_control=profile_media_control,
                t=t,
            )

            if state["screen"] == SCREEN_OVERVIEW:
                render_overview(ctx)
            elif state["screen"] == SCREEN_BROWSER:
                render_browser(ctx)
            elif state["screen"] == SCREEN_CALENDAR:
                render_calendar(ctx)
            elif state["screen"] == SCREEN_TEMPLATES:
                render_templates(ctx)
            elif state["screen"] == SCREEN_SETTINGS:
                render_settings(ctx)
            elif state["screen"] == SCREEN_HEALTH:
                render_health(ctx)
            else:
                render_board(ctx)
        except Exception as exc:
            record_runtime_failure("Screen render", exc, screen=state.get("screen"))
            render_error_view(exc)

    def show_board(_e=None):
        reset_filters(render=False)
        state["screen"] = SCREEN_BOARD
        render_current()

    def show_overview(_e=None):
        state["screen"] = SCREEN_OVERVIEW
        render_current()

    def show_browser(_e=None):
        state["screen"] = SCREEN_BROWSER
        render_current()

    file_drop_receiver = {"callback": None}

    def show_inline_type_dialog(on_created, *, suggested_extension=""):
        name_field = ft.TextField(label="New type name", hint_text="e.g. CAD Drawing", autofocus=True, border_radius=12, border_color=BORDER)
        extension_field = ft.TextField(label="Extensions (optional)", value=suggested_extension, hint_text="e.g. .dwg, .dxf", border_radius=12, border_color=BORDER)
        icon_field = ft.TextField(label="Icon text", hint_text="CAD", width=120, border_radius=12, border_color=BORDER)
        color_field = ft.TextField(label="Color", value="#2563EB", width=130, border_radius=12, border_color=BORDER)
        preview = ft.Container(width=38, height=38, border_radius=11, bgcolor="#2563EB")

        def select_color(color):
            color_field.value = color
            preview.bgcolor = color
            page.update()

        def refresh_color(_event=None):
            value = str(color_field.value or "").strip()
            if len(value) == 7 and value.startswith("#"):
                preview.bgcolor = value
                page.update()

        color_field.on_change = refresh_color

        def save_type(_event=None):
            try:
                item = create_custom_file_type(
                    settings,
                    name_field.value,
                    extensions=extension_field.value,
                    icon=icon_field.value,
                    color=color_field.value,
                )
            except ValueError as exc:
                show_message(page, "Could not add type", str(exc))
                return
            page.pop_dialog()
            on_created(item["name"])
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=PRIMARY), ft.Text("Create a work type", size=20, weight=ft.FontWeight.W_900, color=TEXT)]),
                content=ft.Column(
                    width=500,
                    height=260,
                    spacing=12,
                    controls=[
                        ft.Text("This adds the type without closing your current Add form.", size=12, color=MUTED),
                        name_field,
                        extension_field,
                        ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[preview, color_field, icon_field]),
                        ft.Row(spacing=8, wrap=True, controls=[
                            ft.Container(width=28, height=28, border_radius=99, bgcolor=color, on_click=lambda _e, value=color: select_color(value))
                            for color in type_color_choices[:10]
                        ]),
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Create type", icon=ft.Icons.SAVE_OUTLINED, on_click=save_type, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        page.update()

    def add_task_dialog(kind):
        title = {"file": "Add file", "link": "Add link", "project": "Add project"}[kind]
        is_project = kind == "project"
        is_link = kind == "link"
        name_field = ft.TextField(label="Task name", border_radius=12, border_color=BORDER)
        type_options = list(file_types())
        type_values = type_options if is_project else ["Auto-detect", *type_options]
        type_field = dropdown(300, "Project" if is_project else "Auto-detect", type_values)
        target_field = ft.TextField(
            label="URL link" if is_link else ("Project folder path" if is_project else "Local file path"),
            value="https://" if is_link else "",
            border_radius=12,
            border_color=BORDER,
            expand=True,
        )
        note_field = ft.TextField(label="Note / description", multiline=True, min_lines=3, max_lines=3, border_radius=12, border_color=BORDER)
        detected_label = ft.Text("Folders are added as Project." if is_project else "Type is detected automatically.", size=12, color=MUTED)

        def refresh_detection(_e=None):
            if is_project:
                return
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

        if not is_project:
            target_field.on_change = refresh_detection

        def select_created_type(name):
            values = list(file_types())
            if not is_project:
                values.insert(0, "Auto-detect")
            type_field.options = [ft.dropdown.Option(value) for value in values]
            type_field.value = name
            detected_label.value = f"New type selected: {name}"
            detected_label.color = PRIMARY
            page.update()

        def on_type_select(event):
            if event.control.value != "Other":
                return
            target = str(target_field.value or "").strip()
            suffix = Path(target).suffix.lower() if target and not target.startswith(("http://", "https://")) else ""
            show_inline_type_dialog(select_created_type, suggested_extension=suffix)

        type_field.on_select = on_type_select

        async def browse(_e):
            if is_project:
                path = await pick_directory("Choose project folder")
            else:
                picked = await file_picker.pick_files(dialog_title="Choose file", allow_multiple=False)
                path = picked[0].path if picked else ""
            if path:
                target_field.value = path
                if not name_field.value:
                    name_field.value = Path(path).name if is_project else Path(path).stem
                refresh_detection()
                page.update()

        async def paste_url(_e):
            try:
                value = await page.clipboard.get()
            except Exception:
                value = ""
            if value:
                target_field.value = str(value)
                refresh_detection()
                page.update()

        def effective_type():
            if is_project:
                return type_field.value or "Project"
            return "Other" if type_field.value == "Auto-detect" else type_field.value

        def save(_e):
            target = (target_field.value or "").strip()
            if not target or target == "https://":
                show_message(page, "Missing info", "Please choose a file or enter a link first.")
                return
            chosen_type = effective_type()

            def create_work_item():
                try:
                    task = create_task_from_source(name_field.value, target, file_type=chosen_type, note=note_field.value, status=STATUS_PENDING)
                except Exception as exc:
                    show_message(page, "Add failed", str(exc))
                    return
                all_tasks.append(task)
                page.pop_dialog()
                save_and_render(f"{title} copied to Waiting as {task.get('name', 'Untitled task')}.")
                show_message(page, "Added to Waiting", f"{task.get('name', 'Untitled task')} ({task.get('type', 'Other')})", kind="success")

            run_with_duplicate_guard(name_field.value, target, chosen_type, create_work_item)

        target_row = ft.Row(
            spacing=10,
            controls=[
                target_field,
                ft.Button(
                    "Paste URL" if is_link else ("Browse folder" if is_project else "Browse"),
                    on_click=paste_url if is_link else browse,
                    width=130 if not is_link else 110,
                ),
            ],
        )
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=add_destination_header(
                    f"{title} to Board",
                    "Create a link shortcut" if is_link else "Create a project workspace" if is_project else "Add one file and classify it",
                    ft.Icons.LINK_ROUNDED if is_link else ft.Icons.CREATE_NEW_FOLDER_OUTLINED if is_project else ft.Icons.UPLOAD_FILE_OUTLINED,
                    "Board · Waiting",
                ),
                content=ft.Column(
                    width=560,
                    height=430,
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(
                            padding=12,
                            border_radius=14,
                            bgcolor="#F8FBFF",
                            border=border_all(1, "#DBEAFE"),
                            content=ft.Row(spacing=12, controls=[
                                ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color=PRIMARY),
                                ft.Text(
                                    "Paste a URL, choose its type, and SA CHECK will create a shortcut in Waiting."
                                    if is_link else
                                    "Choose a source and SA CHECK will classify it into the matching Waiting folder.",
                                    size=12,
                                    color=MUTED,
                                    expand=True,
                                ),
                            ]),
                        ),
                        name_field,
                        target_row,
                        ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text("File type" if not is_link else "Link type", size=12, weight=ft.FontWeight.W_700, color=MUTED),
                                ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[type_field, detected_label]),
                            ],
                        ),
                        note_field,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Add link to Waiting" if is_link else "Add to Waiting", icon=ft.Icons.LINK_ROUNDED if is_link else ft.Icons.ADD_TASK_OUTLINED, on_click=save, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=10))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def add_files_dialog(_e=None, initial_paths=None):
        picked_rows = []
        import_state = {"running": False, "cancelled": False}
        list_view = ft.ListView(expand=True, spacing=8)
        summary_text = ft.Text("No files selected yet.", size=12, weight=ft.FontWeight.W_700, color=MUTED)
        note_field = ft.TextField(label="Note for all files (optional)", multiline=True, min_lines=1, max_lines=2, border_radius=12, border_color=BORDER)
        progress_bar = ft.ProgressBar(value=0, color=PRIMARY, bgcolor="#DBEAFE", border_radius=99)
        progress_text = ft.Text("Preparing import...", size=12, weight=ft.FontWeight.W_800, color=TEXT)
        progress_detail = ft.Text("0 of 0", size=11, color=MUTED)
        progress_panel = ft.Container(
            visible=False,
            border=border_all(1, "#BFDBFE"),
            border_radius=12,
            bgcolor="#EFF6FF",
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[progress_text, progress_detail]),
                    progress_bar,
                ],
            ),
        )

        def type_choices():
            return list(file_types())

        def update_summary():
            counts = {}
            for row in picked_rows:
                key = row["type"]
                counts[key] = counts.get(key, 0) + 1
            if picked_rows:
                breakdown = "   ".join(f"{name} {count}" for name, count in counts.items())
                summary_text.value = f"{len(picked_rows)} file(s)  ->  {breakdown}"
                summary_text.color = PRIMARY
            else:
                summary_text.value = "No files selected yet."
                summary_text.color = MUTED
            try:
                summary_text.update()
            except Exception:
                pass

        def remove_row(row):
            if row in picked_rows:
                picked_rows.remove(row)
            rebuild_list()
            update_summary()

        def make_type_field(row):
            def on_type_change(e):
                row["type"] = e.control.value
                update_summary()
                if e.control.value == "Other":
                    def select_created_type(name):
                        row["type"] = name
                        e.control.options = [ft.dropdown.Option(value) for value in type_choices()]
                        e.control.value = name
                        rebuild_list()
                        update_summary()
                        page.update()

                    show_inline_type_dialog(select_created_type, suggested_extension=Path(row["path"]).suffix.lower())
            return dropdown(150, row["type"], type_choices(), on_select=on_type_change)

        def row_control(row):
            icon, icon_color = task_icon(row["type"])
            return ft.Container(
                bgcolor=WHITE,
                border=border_all(1, BORDER),
                border_radius=12,
                padding=pad_sym(horizontal=10, vertical=8),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=32, height=32, border_radius=9, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=17, color=icon_color)),
                        ft.Column(
                            spacing=1,
                            expand=True,
                            controls=[
                                ft.Text(Path(row["path"]).name, size=13, weight=ft.FontWeight.W_700, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(row["path"], size=10, color=MUTED_2, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        make_type_field(row),
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16, icon_color=MUTED, tooltip="Remove", on_click=lambda _e, r=row: remove_row(r)),
                    ],
                ),
            )

        def rebuild_list():
            if picked_rows:
                list_view.controls = [row_control(row) for row in picked_rows]
            else:
                list_view.controls = [ft.Container(alignment=CENTER, padding=30, content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Icon(ft.Icons.UPLOAD_FILE_OUTLINED, size=28, color=MUTED_2), ft.Text("Drag files anywhere onto SA CHECK, or use Browse files.", size=13, color=MUTED_2), ft.Text("Each file is auto-sorted by type before import.", size=11, color=MUTED_2)]))]
            try:
                list_view.update()
            except Exception:
                pass

        def add_path(path):
            cleaned = (path or "").strip().strip('"')
            if not cleaned or any(row["path"] == cleaned for row in picked_rows):
                return False
            if not Path(cleaned).is_file():
                return False
            detected = infer_type(cleaned)
            choices = type_choices()
            picked_rows.append({"path": cleaned, "type": detected if detected in choices else "Other"})
            return True

        def add_dropped_paths(paths):
            added = sum(1 for path in paths if add_path(path))
            rebuild_list()
            update_summary()
            if added:
                summary_text.value = f"Dropped {added} file(s) · " + summary_text.value
            try:
                page.update()
            except Exception:
                pass

        async def browse(_e):
            picked = await file_picker.pick_files(dialog_title="Choose files", allow_multiple=True)
            for file in picked or []:
                add_path(file.path)
            rebuild_list()
            update_summary()
            page.update()

        def cancel_import(_e=None):
            if import_state["running"]:
                import_state["cancelled"] = True
                progress_text.value = "Stopping after the current file..."
                progress_text.color = "#D97706"
                page.update()
                return
            file_drop_receiver["callback"] = None
            page.pop_dialog()
            page.update()

        def save(_e):
            if not picked_rows:
                show_message(page, "No files", "Choose at least one file first.")
                return
            if import_state["running"]:
                return
            rows = [dict(row) for row in picked_rows]
            shared_note = note_field.value or ""
            import_state.update({"running": True, "cancelled": False})
            progress_panel.visible = True
            progress_bar.value = 0
            progress_text.value = "Starting bulk import..."
            progress_text.color = TEXT
            progress_detail.value = f"0 of {len(rows)}"
            save_button.disabled = True
            page.update()

            def update_progress(done, total, label):
                progress_bar.value = done / total if total else 0
                progress_text.value = f"Importing {label}" if done < total else "Finalizing imported work..."
                progress_detail.value = f"{done} of {total}"
                try:
                    page.update()
                except Exception:
                    pass

            def worker():
                result = import_rows(
                    rows,
                    lambda row: create_task_from_source(
                        Path(row["path"]).stem,
                        row["path"],
                        file_type=row["type"],
                        note=shared_note,
                        status=STATUS_PENDING,
                    ),
                    on_progress=update_progress,
                    is_cancelled=lambda: import_state["cancelled"],
                )
                import_state["running"] = False
                file_drop_receiver["callback"] = None
                if result.created:
                    all_tasks.extend(result.created)
                    save_tasks(all_tasks)
                page.pop_dialog()
                render_current()
                created = len(result.created)
                if result.cancelled:
                    show_message(page, "Import stopped", f"Added {created} file(s) before cancellation. Existing imported files were kept.", kind="warning")
                elif result.errors:
                    details = "\n".join(result.errors[:8])
                    extra = len(result.errors) - 8
                    if extra > 0:
                        details += f"\n...and {extra} more"
                    show_message(page, "Bulk import complete", f"Added {created}. Skipped {len(result.errors)}:\n{details}", kind="warning")
                else:
                    show_message(page, "Bulk import complete", f"Added {created} file(s), sorted by type.", kind="success")

            page.run_thread(worker)

        for initial_path in initial_paths or []:
            add_path(initial_path)
        rebuild_list()
        update_summary()
        file_drop_receiver["callback"] = add_dropped_paths
        save_button = ft.Button("Add to Waiting", on_click=save, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=10)))
        cancel_button = ft.TextButton("Cancel", on_click=cancel_import)
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=add_destination_header("Add files to Board", "Bulk import and automatic classification", ft.Icons.UPLOAD_FILE_OUTLINED, "Board · Waiting"),
                content=ft.Column(
                    width=640,
                    height=520,
                    spacing=12,
                    controls=[
                        ft.Container(
                            padding=12,
                            border_radius=14,
                            bgcolor="#F8FBFF",
                            border=border_all(1, "#DBEAFE"),
                            content=ft.Row(spacing=12, controls=[
                                ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, color=PRIMARY),
                                ft.Text("Drop files from Windows Explorer or browse. SA CHECK classifies and copies them into Waiting.", size=12, color=MUTED, expand=True),
                                ft.Button("Browse files", icon=ft.Icons.UPLOAD_FILE_OUTLINED, on_click=browse, height=42, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=10))),
                            ]),
                        ),
                        summary_text,
                        ft.Container(expand=True, border=border_all(1, BORDER), border_radius=14, padding=8, bgcolor="#F8FBFF", content=list_view),
                        note_field,
                        progress_panel,
                    ],
                ),
                actions=[
                    cancel_button,
                    save_button,
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def show_templates(_e=None):
        state["screen"] = SCREEN_TEMPLATES
        render_current()

    def sync_now(_e=None):
        nonlocal root_work, calendar_events
        if state.get("refreshing") or state.get("syncing"):
            show_message(page, "Refresh in progress", "SA CHECK is already refreshing. Please wait a moment.", kind="warning")
            return

        refresh_token = uuid.uuid4().hex
        state["refreshing"] = True
        state["syncing"] = True
        state["refresh_token"] = refresh_token
        set_sync_phase("syncing", "Manual refresh and Work-folder sync is running")
        started = time.perf_counter()

        refresh_icon = ft.Icon(ft.Icons.SYNC_ROUNDED, size=25, color="#2563EB")
        refresh_status = ft.Text("Preparing a safe refresh...", size=14, weight=ft.FontWeight.W_700, color=TEXT)
        refresh_detail = ft.Text("The main window stays open while local data is reloaded.", size=11, color=MUTED)
        refresh_progress = ft.ProgressBar(value=0.06, height=8, color="#2563EB", bgcolor="#DCE7EF", border_radius=99)
        refresh_percent = ft.Text("6%", size=12, weight=ft.FontWeight.W_900, color="#2563EB")
        refresh_steps = [
            ft.Container(width=9, height=9, border_radius=99, bgcolor="#2563EB"),
            ft.Container(width=9, height=9, border_radius=99, bgcolor="#CBD5E1"),
            ft.Container(width=9, height=9, border_radius=99, bgcolor="#CBD5E1"),
            ft.Container(width=9, height=9, border_radius=99, bgcolor="#CBD5E1"),
        ]
        refresh_dialog = ft.AlertDialog(
            modal=True,
            content_padding=0,
            content=ft.Container(
                width=470,
                height=270,
                border_radius=18,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                bgcolor=WHITE,
                content=ft.Column(
                    spacing=0,
                    controls=[
                        ft.Row(spacing=0, controls=[ft.Container(expand=True, height=7, bgcolor=color) for color in ("#2563EB", "#14B8A6", "#F59E0B", "#E11D48")]),
                        ft.Container(
                            expand=True,
                            padding=pad_sym(horizontal=28, vertical=24),
                            content=ft.Column(
                                spacing=14,
                                controls=[
                                    ft.Row(
                                        spacing=12,
                                        controls=[
                                            ft.Container(width=48, height=48, border_radius=14, bgcolor="#EFF6FF", alignment=CENTER, content=refresh_icon),
                                            ft.Column(spacing=3, expand=True, controls=[ft.Text("Refreshing SA CHECK", size=21, weight=ft.FontWeight.W_900, color=TEXT), ft.Text(APP_VERSION, size=11, weight=ft.FontWeight.W_700, color=PRIMARY)]),
                                        ],
                                    ),
                                    ft.Container(
                                        height=62,
                                        padding=pad_sym(horizontal=14, vertical=10),
                                        border_radius=12,
                                        bgcolor="#F8FAFC",
                                        border=border_all(1, BORDER),
                                        content=ft.Column(spacing=3, controls=[refresh_status, refresh_detail]),
                                    ),
                                    ft.Row(spacing=10, controls=[ft.Container(expand=True, content=refresh_progress), refresh_percent]),
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Row(spacing=7, controls=[refresh_steps[0], ft.Text("Prepare", size=10, color=MUTED)]),
                                            ft.Row(spacing=7, controls=[refresh_steps[1], ft.Text("Work", size=10, color=MUTED)]),
                                            ft.Row(spacing=7, controls=[refresh_steps[2], ft.Text("Update", size=10, color=MUTED)]),
                                            ft.Row(spacing=7, controls=[refresh_steps[3], ft.Text("Ready", size=10, color=MUTED)]),
                                        ],
                                    ),
                                    ft.Row(spacing=6, alignment=ft.MainAxisAlignment.CENTER, controls=[ft.Icon(ft.Icons.LOCK_OUTLINE, size=13, color=MUTED), ft.Text("Work folders, settings, and cache are never cleared.", size=10, color=MUTED)]),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            bgcolor=ft.Colors.TRANSPARENT,
        )

        def token_is_active():
            return state.get("refresh_token") == refresh_token and state.get("refreshing")

        def set_refresh_status(message, detail, value, step, *, error=False):
            if not token_is_active():
                return
            refresh_status.value = message
            refresh_detail.value = detail
            refresh_progress.value = value
            refresh_progress.color = "#DC2626" if error else "#16A34A" if value >= 1 else "#2563EB"
            refresh_percent.value = f"{int(value * 100)}%"
            refresh_percent.color = refresh_progress.color
            refresh_icon.icon = ft.Icons.ERROR_OUTLINE if error else ft.Icons.CHECK_CIRCLE_OUTLINE if value >= 1 else ft.Icons.SYNC_ROUNDED
            refresh_icon.color = refresh_progress.color
            for index, dot in enumerate(refresh_steps):
                dot.bgcolor = "#16A34A" if index < step else "#2563EB" if index == step else "#CBD5E1"
            try:
                page.update()
            except Exception:
                pass

        def close_refresh_dialog():
            if getattr(refresh_dialog, "open", False):
                try:
                    page.pop_dialog()
                except Exception:
                    refresh_dialog.open = False
            try:
                page.update()
            except Exception:
                pass

        def finish_refresh(*, changed=False, update_manifest=None, error=None, timed_out=False):
            if state.get("refresh_token") != refresh_token:
                return
            state["refreshing"] = False
            state["syncing"] = bool(timed_out)
            state["refresh_token"] = ""
            close_refresh_dialog()
            if error:
                fail_sync("Manual sync", RuntimeError(str(error)), timed_out=False)
                show_message(page, "Refresh failed", f"The current screen is still safe. {error}", kind="warning")
                return
            if timed_out:
                fail_sync("Manual sync", TimeoutError("Refresh exceeded the 15-second safety timeout."), timed_out=True)
                show_message(page, "Refresh timeout", "The folder scan is taking longer than expected, so the loader was closed. Your current data remains available and the background scan will release itself when finished.", kind="warning")
                return
            set_sync_phase("success", "Manual refresh completed successfully")
            show_message(page, "Refresh complete", "Work data changed and the screen was refreshed." if changed else "Local data is current. The app also checked for updates.", kind="success")
            if update_manifest and is_newer_version(update_manifest.get("version")):
                dismissed = int(settings.get("update_dismiss_count", 0)) if settings.get("last_update_prompt_version") == update_manifest.get("version") else 0
                forced_reason = update_force_reason(update_manifest.get("version"), update_manifest, dismissed)
                auto_start = bool(forced_reason and (update_manifest.get("required") or is_core_platform_update(update_manifest.get("version"))))
                show_update_prompt(update_manifest, forced=bool(forced_reason), auto_start=auto_start)

        def refresh_worker():
            nonlocal root_work, calendar_events
            try:
                set_refresh_status("Protecting the current session...", "Creating a small recovery snapshot before the scan.", 0.14, 0)
                create_snapshot("Before safe in-app refresh")
                if not token_is_active():
                    return

                set_refresh_status("Scanning Work folders...", "Reading Waiting, Doing, Success, and Template items in the background.", 0.36, 1)
                synced_tasks, _synced_templates, changed = sync_from_work(force=True)
                if not token_is_active():
                    return

                set_refresh_status("Reloading local settings...", "Applying the latest local paths, calendar data, and preferences.", 0.64, 1)
                refreshed_settings = load_settings()
                refreshed_root = work_folder()
                all_tasks.clear()
                all_tasks.extend(synced_tasks)
                settings.clear()
                settings.update(refreshed_settings)
                root_work = refreshed_root
                calendar_events = load_persisted_calendar_events()
                current_path = Path(current_browser_path.get("path") or refreshed_root)
                try:
                    current_path.resolve().relative_to(refreshed_root.resolve())
                    path_is_safe = current_path.exists()
                except (OSError, ValueError):
                    path_is_safe = False
                current_browser_path["path"] = current_path if path_is_safe else refreshed_root
                state["last_sync_check"] = datetime.now().timestamp()

                manifest = None
                if not settings.get("offline_mode", False) and settings.get("update_checks_enabled", True):
                    set_refresh_status("Checking for updates...", "Contacting the SA CHECK Git update channel with a short timeout.", 0.82, 2)
                    try:
                        manifest, network = fetch_update_manifest()
                        state["online_status"] = network
                        state["last_update_check"] = time.time()
                        state["update_manifest"] = manifest
                        state["update_available"] = bool(manifest and is_newer_version(manifest.get("version")))
                    except Exception:
                        state["online_status"] = "offline"
                        state["update_available"] = False
                else:
                    state["online_status"] = "offline"

                if not token_is_active():
                    return
                set_refresh_status("Refresh complete", "The app stayed open and the latest local data is ready.", 1.0, 3)
                elapsed = time.perf_counter() - started
                if elapsed < 1.15:
                    time.sleep(1.15 - elapsed)
                if not token_is_active():
                    return
                render_current()
                finish_refresh(changed=changed, update_manifest=manifest)
            except Exception as exc:
                set_refresh_status("Refresh could not finish", "The current app screen and user data were kept intact.", 1.0, 3, error=True)
                time.sleep(0.45)
                finish_refresh(error=str(exc) or "Unknown refresh error")
            finally:
                if state.get("refresh_token") != refresh_token:
                    state["syncing"] = False

        def refresh_watchdog():
            time.sleep(15)
            if token_is_active():
                finish_refresh(timed_out=True)

        page.show_dialog(refresh_dialog)
        page.update()
        page.run_thread(refresh_worker)
        page.run_thread(refresh_watchdog)

    def show_create_new(_e=None):
        name_field = ft.TextField(
            label="Task name",
            hint_text="Leave blank to use the tool name",
            border_radius=12,
            border_color=BORDER,
            height=48,
        )

        def create_with(tool):
            try:
                ensure_status_folders()
                task = create_task_from_tool(tool, name_field.value or "")
                all_tasks.append(task)
                save_tasks(all_tasks)
                page.pop_dialog()
                render_current()
                open_target(task)
            except Exception as exc:
                show_message(page, "Create failed", str(exc))

        def tool_card(tool):
            icon, icon_color = task_icon(tool.get("type", "Other"))
            return ft.Container(
                height=112,
                bgcolor=WHITE,
                border=border_all(1, BORDER),
                border_radius=16,
                padding=14,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(width=34, height=34, border_radius=10, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=18, color=icon_color)),
                                ft.Text(tool.get("name", "New Work"), size=14, weight=ft.FontWeight.W_700, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                            ],
                        ),
                        ft.Text(tool.get("description", ""), size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Button(
                            "Create + Open",
                            on_click=lambda _e, selected=tool: create_with(selected),
                            height=34,
                            style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=10)),
                        ),
                    ],
                ),
            )

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Create New Work", size=24, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Column(
                    width=760,
                    height=540,
                    spacing=16,
                    controls=[
                        ft.Text(f"Pick one tool. {APP_NAME} will create a Waiting task and open it right away.", size=13, color=MUTED),
                        name_field,
                        ft.GridView(
                            expand=True,
                            runs_count=3,
                            max_extent=240,
                            child_aspect_ratio=2.15,
                            spacing=12,
                            run_spacing=12,
                            controls=[tool_card(tool) for tool in CREATE_TOOLS if tool.get("kind") != "folder"],
                        ),
                    ],
                ),
                actions=[ft.TextButton("Close", on_click=lambda _e: (page.pop_dialog(), page.update()))],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def show_settings(_e=None):
        state["screen"] = SCREEN_SETTINGS
        render_current()

    def show_health(_e=None):
        state["screen"] = SCREEN_HEALTH
        render_current()

    def export_report(_e=None):
        report_dir = Path.home() / "Desktop" / "SA_CHECK_REPORTS"
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        csv_path = report_dir / f"SA_CHECK_Report_{stamp}.csv"
        html_path = report_dir / f"SA_CHECK_Report_{stamp}.html"
        rows = []
        for task in all_tasks:
            rows.append(
                {
                    "Name": task.get("name", ""),
                    "Status": STATUS_LABELS.get(task.get("status"), task.get("status", "")),
                    "Type": task.get("type", ""),
                    "Date": task_calendar_date(task),
                    "Done Date": task.get("done_date") or "",
                    "Note": task.get("note", ""),
                    "Target": task.get("link") or task.get("shortcut_path") or "",
                }
            )
        fields = ["Name", "Status", "Type", "Date", "Done Date", "Note", "Target"]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        summary = {
            "Total": len(all_tasks),
            "Waiting": sum(1 for task in all_tasks if task.get("status") == STATUS_PENDING),
            "Doing": sum(1 for task in all_tasks if task.get("status") == STATUS_PROGRESS),
            "Success": sum(1 for task in all_tasks if task.get("status") == STATUS_DONE),
        }
        table_rows = "\n".join(
            "<tr>" + "".join(f"<td>{html.escape(str(row.get(field, '')))}</td>" for field in fields) + "</tr>"
            for row in rows
        )
        summary_cards = "".join(f"<div class='card'><b>{html.escape(k)}</b><span>{v}</span></div>" for k, v in summary.items())
        html_path.write_text(
            f"""<!doctype html>
<html><head><meta charset="utf-8"><title>SA CHECK Report</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;color:#0f172a;background:#f8fafc}}
h1{{margin:0 0 4px}} .muted{{color:#64748b}} .cards{{display:flex;gap:12px;margin:18px 0}}
.card{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;min-width:110px}}
.card span{{display:block;font-size:24px;font-weight:800;margin-top:4px}}
table{{border-collapse:collapse;width:100%;background:white;border:1px solid #e2e8f0}}
th,td{{border-bottom:1px solid #e2e8f0;padding:9px 10px;text-align:left;vertical-align:top;font-size:13px}}
th{{background:#eff6ff;color:#1d4ed8}}
</style></head><body>
<h1>SA CHECK Report</h1><div class="muted">Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
<div class="cards">{summary_cards}</div>
<table><thead><tr>{''.join(f'<th>{html.escape(field)}</th>' for field in fields)}</tr></thead><tbody>{table_rows}</tbody></table>
</body></html>""",
            encoding="utf-8",
        )
        show_message(page, "Report exported", f"Saved CSV and HTML report to {report_dir}", kind="success")
        try:
            os.startfile(str(report_dir))
        except OSError:
            pass

    def show_about(_e=None):
        page.show_dialog(
            ft.AlertDialog(
                modal=False,
                title=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        app_logo_control(52, 16),
                        ft.Column(spacing=2, controls=[ft.Text("SA CHECK", size=24, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Desktop Work Board", size=13, color=MUTED)]),
                    ],
                ),
                content=ft.Container(
                    width=560,
                    height=300,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Container(border=border_all(1, "#DBEAFE"), border_radius=16, bgcolor="#F8FBFF", padding=14, content=ft.Column(spacing=6, controls=[
                                ft.Text("Local-first desktop workspace", size=14, weight=ft.FontWeight.W_900, color=TEXT),
                                ft.Text("Version: " + APP_VERSION + " | Guide: " + MANUAL_VERSION, size=12, color=MUTED, selectable=True),
                            ])),
                            ft.Container(border=border_all(1, BORDER), border_radius=16, bgcolor="#FFFFFF", padding=14, content=ft.Column(spacing=6, controls=[
                                ft.Text(f"App folder: {Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]}", size=12, color=MUTED, selectable=True),
                                ft.Text(f"Data file: {DATA_FILE}", size=12, color=MUTED, selectable=True),
                                ft.Text(f"Work folder: {root_work}", size=12, color=MUTED, selectable=True),
                            ])),
                        ],
                    ),
                ),
                actions=[
                    ft.TextButton("Open Guide", on_click=lambda event: (page.pop_dialog(), show_help())),
                    ft.Button("Close", icon=ft.Icons.CHECK, on_click=lambda event: (page.pop_dialog(), page.update()), style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        page.update()

    def show_version_notes(_e=None):
        def note_row(item, color="#16A34A"):
            return ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color=color), ft.Text(item, size=12, color=MUTED, expand=True)])

        def history_card(entry):
            latest = bool(entry.get("latest"))
            color = "#16A34A" if latest else PRIMARY
            return ft.Container(
                border=border_all(1, "#BBF7D0" if latest else "#DBEAFE"),
                border_radius=14,
                bgcolor="#F0FDF4" if latest else "#F8FBFF",
                padding=12,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.NEW_RELEASES_OUTLINED if latest else ft.Icons.HISTORY, color=color),
                                ft.Text(f"Version {entry.get('version', '-')}", size=16, weight=ft.FontWeight.W_900, color=TEXT, expand=True),
                                ft.Container(visible=latest, padding=pad_sym(horizontal=10, vertical=5), border_radius=999, bgcolor="#DCFCE7", border=border_all(1, "#86EFAC"), content=ft.Text("Latest Remark", size=11, weight=ft.FontWeight.W_900, color="#166534")),
                                ft.Text(str(entry.get("date", "")), size=11, color=MUTED),
                            ],
                        ),
                        *[note_row(item, color) for item in entry.get("items", [])],
                    ],
                ),
            )

        current_items = [history_card(entry) for entry in VERSION_HISTORY]
        manifest = state.get("update_manifest") or {}
        if state.get("update_available") and manifest:
            current_items.append(
                ft.Container(
                    border=border_all(1, "#FED7AA"),
                    border_radius=14,
                    bgcolor="#FFFBEB",
                    padding=12,
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, color="#D97706"), ft.Text(f"Available update {manifest.get('version')}", size=16, weight=ft.FontWeight.W_900, color=TEXT)]),
                            *[ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.ARROW_RIGHT_ALT, size=16, color="#D97706"), ft.Text(item, size=12, color=MUTED, expand=True)]) for item in (manifest.get("notes") or ["Update package is available."])],
                        ],
                    ),
                )
            )
        page.show_dialog(
            ft.AlertDialog(
                modal=False,
                title=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.FACT_CHECK_OUTLINED, color=PRIMARY), ft.Text("Version Notes", size=22, weight=ft.FontWeight.W_900, color=TEXT)]),
                content=ft.Container(width=640, height=420, content=ft.ListView(spacing=12, controls=current_items)),
                actions=[ft.Button("Close", icon=ft.Icons.CHECK, on_click=lambda _event: (page.pop_dialog(), page.update()), style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12)))],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        page.update()

    def show_update_prompt(manifest=None, forced=False, auto_start=False):
        manifest = manifest or state.get("update_manifest") or {}
        version = manifest.get("version", "")
        raw_notes = manifest.get("notes") or ["Update package is available."]
        notes = [
            item
            for item in raw_notes
            if "http://" not in item
            and "https://" not in item
            and "Google Drive" not in item
            and "raw.githubusercontent" not in item
            and len(item.strip()) <= 120
        ][:5]
        if not notes:
            notes = ["Update package is ready.", "App files will be updated only.", "Work folders and user settings stay safe."]
        reason = update_force_reason(version, manifest, int(settings.get("update_dismiss_count", 0))) if version else ""

        def open_update(_event=None):
            if state.get("update_installing"):
                show_message(page, "Update", "Update is already running. Please wait until SA CHECK closes, then open it again manually.", kind="warning")
                return
            state["update_installing"] = True
            url = manifest.get("installer_url") or ""
            settings["last_update_prompt_version"] = version
            settings["update_dismiss_count"] = 0
            save_settings(settings)
            page.pop_dialog()
            page.update()
            if not url:
                state["update_installing"] = False
                show_message(page, "Update", "Update package is not ready yet. Please contact the app publisher.")
                return
            cancel_download = {"value": False}
            progress_bar = ft.ProgressBar(value=0, color=PRIMARY, bgcolor="#DBEAFE")
            percent_text = ft.Text("0%", size=18, weight=ft.FontWeight.W_900, color=TEXT)
            size_text = ft.Text("Preparing download...", size=12, color=MUTED)
            status_text = ft.Text("Connecting to update server...", size=13, color=MUTED)
            file_text = ft.Text(f"SA CHECK {version}", size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
            cancel_button = ft.TextButton("Cancel", on_click=lambda _e: cancel_download.update({"value": True}))

            def update_progress(downloaded=0, total=0, status="Downloading update package...", done=False, error=False):
                try:
                    if total and total > 0:
                        value = min(1, max(0, downloaded / total))
                        progress_bar.value = value
                        percent = int(value * 100)
                        if downloaded > 0 and not done:
                            percent = max(1, percent)
                        percent_text.value = f"{percent}%"
                    else:
                        progress_bar.value = None
                        percent_text.value = "--%"
                    size_text.value = update_size_label(downloaded, total)
                    status_text.value = status
                    status_text.color = "#DC2626" if error else "#16A34A" if done else MUTED
                    cancel_button.disabled = done or error
                    page.update()
                except Exception:
                    pass

            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED, color=PRIMARY), ft.Text("Downloading Update", size=21, weight=ft.FontWeight.W_900, color=TEXT)]),
                    content=ft.Container(
                        width=540,
                        height=235,
                        content=ft.Column(
                            spacing=14,
                            controls=[
                                ft.Container(border=border_all(1, "#DBEAFE"), border_radius=14, bgcolor="#F8FBFF", padding=12, content=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SHIELD_OUTLINED, color=PRIMARY), ft.Text("Only app system files will be replaced. Work folders, settings, and cache stay safe.", size=12, color=MUTED, expand=True)])),
                                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[file_text, percent_text]),
                                progress_bar,
                                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[size_text, status_text]),
                            ],
                        ),
                    ),
                    actions=[cancel_button],
                    bgcolor=WHITE,
                    shape=ft.RoundedRectangleBorder(radius=18),
                )
            )
            page.update()

            def updater_worker():
                part_path = None
                try:
                    download_url = cachebusted_url(direct_download_url(url))
                    temp_dir = Path(tempfile.gettempdir()) / "SACHECK_Update"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    installer_path = temp_dir / f"SA_CHECK_Installer_{version or 'latest'}.exe"
                    part_path = installer_path.with_suffix(installer_path.suffix + ".part")
                    if part_path.exists():
                        part_path.unlink()
                    expected_total = int(manifest.get("installer_size") or 0) or remote_file_size(url)
                    update_progress(0, expected_total, "Checking update package size...")
                    request = urllib.request.Request(download_url, headers={"User-Agent": f"SA-CHECK/{APP_VERSION}"})
                    with urllib.request.urlopen(request, timeout=25) as response:
                        total = int(response.headers.get("content-length") or 0) or expected_total
                        downloaded = 0
                        update_progress(0, total, "Downloading update package...")
                        with part_path.open("wb") as file:
                            while True:
                                if cancel_download["value"]:
                                    raise RuntimeError("Update download was cancelled.")
                                chunk = response.read(64 * 1024)
                                if not chunk:
                                    break
                                file.write(chunk)
                                downloaded += len(chunk)
                                update_progress(downloaded, total, f"Downloading update package... {bytes_label(downloaded)}")
                    if total and downloaded != total:
                        raise RuntimeError("Update package size did not match the server response.")
                    if part_path.stat().st_size < 1024 * 32:
                        raise RuntimeError("Update package was not downloaded correctly.")
                    expected_hash = str(manifest.get("installer_sha256") or "").strip().lower()
                    if expected_hash:
                        if len(expected_hash) != 64:
                            raise RuntimeError("Update package checksum in the release manifest is invalid.")
                        update_progress(downloaded, total or downloaded, "Verifying update package...")
                        digest = hashlib.sha256()
                        with part_path.open("rb") as package_file:
                            for package_chunk in iter(lambda: package_file.read(1024 * 1024), b""):
                                digest.update(package_chunk)
                        if digest.hexdigest().lower() != expected_hash:
                            raise RuntimeError("Update package verification failed. The downloaded file was removed.")
                    if installer_path.exists():
                        installer_path.unlink()
                    part_path.replace(installer_path)
                    update_progress(installer_path.stat().st_size, total or installer_path.stat().st_size, "Download complete. Launching installer...", done=True)
                    silent_args = [
                        str(installer_path),
                        "/VERYSILENT",
                        "/SUPPRESSMSGBOXES",
                        "/NOCANCEL",
                        "/NORESTART",
                        "/CLOSEAPPLICATIONS",
                        "/FORCECLOSEAPPLICATIONS",
                    ]
                    subprocess.Popen(silent_args, cwd=str(temp_dir), close_fds=True)
                    show_message(page, "Update", "Silent installer is running. SA CHECK will close after the update. Please open it again from the shortcut.", kind="success")
                    try:
                        page.pop_dialog()
                        page.update()
                    except Exception:
                        pass
                    time.sleep(1.5)
                    os._exit(0)
                except Exception as exc:
                    state["update_installing"] = False
                    try:
                        if part_path and part_path.exists():
                            part_path.unlink()
                    except OSError:
                        pass
                    update_progress(0, 0, str(exc) or "Could not download the update package.", error=True)
                    show_message(page, "Update", "Could not download the update package. Please try again or contact the app publisher.")

            page.run_thread(updater_worker)

        def skip_update(_event=None):
            if settings.get("last_update_prompt_version") != version:
                settings["update_dismiss_count"] = 0
            settings["last_update_prompt_version"] = version
            settings["update_dismiss_count"] = int(settings.get("update_dismiss_count", 0)) + 1
            save_settings(settings)
            page.pop_dialog()
            update_sidebar()
            page.update()

        actions = [ft.Button("Update now", icon=ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, on_click=open_update, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12)))]
        if not forced:
            actions.insert(0, ft.TextButton("Later", on_click=skip_update))
        page.show_dialog(
            ft.AlertDialog(
                modal=forced,
                title=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, color="#D97706"), ft.Text("Update Ready", size=22, weight=ft.FontWeight.W_900, color=TEXT)]),
                content=ft.Container(
                    width=560,
                    height=330,
                    content=ft.Column(
                        spacing=14,
                        controls=[
                            ft.Row(spacing=10, controls=[
                                ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#ECFDF5", content=ft.Text(f"Installed {APP_VERSION}", size=12, weight=ft.FontWeight.W_800, color="#047857")),
                                ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#FFFBEB", border=border_all(1, "#FED7AA"), content=ft.Text(f"New {version}", size=12, weight=ft.FontWeight.W_900, color="#92400E")),
                            ]),
                            ft.Container(border=border_all(1, "#DBEAFE"), border_radius=14, bgcolor="#F8FBFF", padding=12, content=ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SHIELD_OUTLINED, color=PRIMARY), ft.Text("Updates replace app system files only. Work folders, settings, and cache stay safe.", size=13, color=MUTED, expand=True)])),
                            ft.Container(visible=bool(reason), border=border_all(1, "#FED7AA"), border_radius=14, bgcolor="#FFFBEB", padding=12, content=ft.Text(reason, size=13, weight=ft.FontWeight.W_800, color="#92400E")),
                            ft.Text("What's included", size=13, weight=ft.FontWeight.W_900, color=TEXT),
                            ft.Column(spacing=7, controls=[ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color="#16A34A"), ft.Text(item, size=12, color=MUTED, expand=True)]) for item in notes]),
                        ],
                    ),
                ),
                actions=actions,
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        page.update()
        if auto_start:
            page.run_thread(lambda: (time.sleep(1.2), open_update()))

    def update_channel_url():
        return str(settings.get("update_manifest_url") or DEFAULT_UPDATE_CHANNEL_URL).strip()

    def fetch_update_manifest():
        url = update_channel_url()
        if not url:
            return None, "offline"
        payload = read_update_url(url, max_bytes=1024 * 1024)
        data = json.loads(payload.decode("utf-8-sig"))
        if isinstance(data, dict) and "content" in data and str(data.get("encoding", "")).lower() == "base64":
            decoded = base64.b64decode(str(data.get("content", "")).encode("ascii")).decode("utf-8-sig")
            data = json.loads(decoded)
        manifest = normalize_update_manifest(data)
        return manifest or None, "online"

    def check_for_updates(manual=False):
        if state.get("update_checking"):
            return
        if settings.get("offline_mode", False) or not settings.get("update_checks_enabled", True):
            state["online_status"] = "offline"
            state["update_available"] = False
            update_sidebar()
            if manual:
                show_message(page, "Updates", "Update checks are disabled. Offline mode is active.")
            return
        state["update_checking"] = True
        state["online_status"] = "checking"
        update_sidebar()

        def worker():
            try:
                manifest, network = fetch_update_manifest()
                state["online_status"] = network
                state["last_update_check"] = time.time()
                if manifest and is_newer_version(manifest.get("version")):
                    state["update_manifest"] = manifest
                    state["update_available"] = True
                    dismissed = int(settings.get("update_dismiss_count", 0)) if settings.get("last_update_prompt_version") == manifest.get("version") else 0
                    forced_reason = update_force_reason(manifest.get("version"), manifest, dismissed)
                    auto_start = bool(forced_reason and (manifest.get("required") or is_core_platform_update(manifest.get("version"))))
                    show_update_prompt(manifest, forced=bool(forced_reason), auto_start=auto_start)
                else:
                    state["update_manifest"] = manifest
                    state["update_available"] = False
                    if manual:
                        show_message(page, "Updates", f"{APP_NAME} is up to date ({APP_VERSION}).")
            except (OSError, urllib.error.URLError, TimeoutError):
                state["online_status"] = "offline"
                state["update_available"] = False
                if manual:
                    show_message(page, "Updates", "No internet connection or update channel is unreachable.")
            except Exception as exc:
                state["online_status"] = "offline"
                if manual:
                    show_message(page, "Updates", str(exc))
            finally:
                state["update_checking"] = False
                update_sidebar()
                try:
                    page.update()
                except Exception:
                    pass

        page.run_thread(worker)

    def show_help(_e=None, auto=False):
        def close_manual(_event=None):
            settings["manual_seen_version"] = MANUAL_VERSION
            save_settings(settings)
            page.pop_dialog()
            page.update()

        def open_notes_from_manual(_event=None):
            settings["manual_seen_version"] = MANUAL_VERSION
            save_settings(settings)
            page.pop_dialog()
            page.update()
            show_version_notes()

        GUIDE_SECTION_COLORS = {
            1: ("#2563EB", "#EFF6FF", "#0C447C"),
            2: ("#7C3AED", "#F5F3FF", "#4C1D95"),
            3: ("#D97706", "#FFF7ED", "#854F0B"),
            4: ("#16A34A", "#F0FDF4", "#166534"),
            5: ("#0F766E", "#F0FDFA", "#115E59"),
        }

        def guide_header(number, icon, title, subtitle):
            color, tint, dark = GUIDE_SECTION_COLORS.get(number, (PRIMARY, "#EFF6FF", "#0C447C"))
            return ft.Container(
                data="guide_header",
                bgcolor=tint,
                padding=pad_sym(horizontal=15, vertical=13),
                content=ft.Row(
                    spacing=13,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=34, height=34, border_radius=99, bgcolor=color, alignment=CENTER, content=ft.Text(str(number), size=16, weight=ft.FontWeight.W_900, color=WHITE)),
                        ft.Column(
                            spacing=1,
                            expand=True,
                            controls=[
                                ft.Text(title, size=15, weight=ft.FontWeight.W_900, color=dark),
                                ft.Text(subtitle, size=11, weight=ft.FontWeight.W_700, color=color),
                            ],
                        ),
                        ft.Icon(icon, color=color, size=24),
                    ],
                ),
            )

        def step(icon, title, body, color=PRIMARY, action=None):
            row_controls = [
                ft.Container(width=32, height=32, border_radius=9, bgcolor=color + "18", alignment=CENTER, content=ft.Icon(icon, color=color, size=18)),
                ft.Column(
                    spacing=2,
                    expand=True,
                    controls=[
                        ft.Text(title, size=13, weight=ft.FontWeight.W_800, color=TEXT),
                        ft.Text(body, size=11, color=MUTED, selectable=True),
                    ],
                ),
            ]
            if action:
                row_controls.append(
                    ft.Container(
                        padding=pad_sym(horizontal=9, vertical=5),
                        border_radius=8,
                        bgcolor="#F1F5F9",
                        border=border_all(1, BORDER),
                        content=ft.Text(action, size=11, weight=ft.FontWeight.W_800, color="#334155"),
                    )
                )
            return ft.Container(
                data="guide_step",
                bgcolor=WHITE,
                padding=pad_sym(horizontal=15, vertical=11),
                content=ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=row_controls),
            )

        sections = [
            guide_header(1, ft.Icons.FOLDER_SPECIAL_OUTLINED, "เลือกคลังงาน", "เลือกหรือสร้างโฟลเดอร์ที่เก็บงานของคุณ"),
            step(ft.Icons.SETTINGS_OUTLINED, "เลือก Work folder", "เลือกโฟลเดอร์งาน (Work1, Work2 หรือของทีม)", "#2563EB", "Settings › Work folder"),
            step(ft.Icons.CREATE_NEW_FOLDER_OUTLINED, "สร้างโฟลเดอร์ใหม่", "ยังไม่มีคลังงาน? สร้างใหม่แล้วเลือกเป็น Work folder", "#0F766E", "New folder"),
            step(ft.Icons.SYNC, "Sync เข้าระบบ", "ดึงไฟล์ Waiting / Doing / Success ขึ้นบอร์ด", "#7C3AED", "Sync now"),

            guide_header(2, ft.Icons.ADD_TASK_OUTLINED, "เพิ่มงาน", "ไฟล์ ลิงก์ เทมเพลต — คัดแยกให้อัตโนมัติ"),
            step(ft.Icons.UPLOAD_FILE_OUTLINED, "Add files", "เลือกหลายไฟล์ แอพคัดแยก Word/Excel/PDF เข้า Waiting", "#DC2626", "Add file"),
            step(ft.Icons.LINK_ROUNDED, "Add link", "เก็บ URL (Google Sheet, Figma, Miro) เป็น shortcut", "#0891B2", "Add link"),
            step(ft.Icons.NOTE_ADD_OUTLINED, "Create new work", "สร้างงานเปล่าตามชนิดไฟล์ เข้า Waiting", "#0F766E", "Add work"),
            step(ft.Icons.ARTICLE_OUTLINED, "Templates", "เก็บไฟล์ต้นแบบ กดใช้ซ้ำได้เร็ว", "#D97706", "Templates"),

            guide_header(3, ft.Icons.DASHBOARD_ROUNDED, "ใช้บอร์ด & สถานะ", "ดูงานและเลื่อน Waiting → Doing → Success"),
            step(ft.Icons.PLAY_CIRCLE_OUTLINE, "ย้ายสถานะ", "เมนูงาน หรือ Detail → Move to Waiting/Doing/Success", "#D97706", "Move to…"),
            step(ft.Icons.INFO_OUTLINE, "ดูรายละเอียด", "แก้ชื่อ ชนิด วันที่ note เปิดไฟล์ เปิดโฟลเดอร์", "#2563EB", "Detail"),
            step(ft.Icons.SEARCH, "ค้นหา & กรอง", "ค้นชื่อ note path ประเภท และสถานะได้", "#0F766E", "Search"),

            guide_header(4, ft.Icons.EVENT_OUTLINED, "Calendar, Health & ปลอดภัย", "ตามงาน ตรวจไฟล์หาย ย้อนการแก้ไข"),
            step(ft.Icons.CALENDAR_TODAY_OUTLINED, "Calendar", "เพิ่ม event หรือแก้วันที่ใน Detail เพื่อเตือนงาน", "#7C3AED", "Add Event"),
            step(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "Health", "ดูไฟล์ path หาย, duplicate, snapshot, activity", "#16A34A", "Health"),
            step(ft.Icons.UNDO, "Undo / Snapshot", "ระบบเก็บ snapshot ก่อนแก้สำคัญ ย้อนกลับได้", "#D97706", "Undo"),

            guide_header(5, ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, "ติดตั้ง & อัปเดต", "ลง installer ทับเพื่ออัปเดต งานไม่หาย"),
            step(ft.Icons.INSTALL_DESKTOP_OUTLINED, "ติดตั้ง", "รัน SA_CHECK_Installer.exe ลงที่ C:\\SACHECK", "#2563EB", "Installer"),
            step(ft.Icons.UPDATE, "อัปเดต", "ลง installer ใหม่ทับ — Work folder ไม่โดนลบ", "#0F766E", "Reinstall"),
            step(ft.Icons.DELETE_OUTLINE, "Uninstall", "ลบเฉพาะไฟล์แอพ ไม่ลบงานที่เลือกไว้", "#DC2626", "Uninstall"),
            step(ft.Icons.VERIFIED_USER_OUTLINED, "About", "SA CHECK " + APP_VERSION + " · Local-first desktop workspace", "#0F766E"),
        ]

        guide_groups = []
        current_group = []
        for item in sections:
            if getattr(item, "data", None) == "guide_header" and current_group:
                guide_groups.append(current_group)
                current_group = [item]
            else:
                current_group.append(item)
        if current_group:
            guide_groups.append(current_group)

        guide_controls = []
        for group in guide_groups:
            children = []
            for idx, item in enumerate(group):
                if idx >= 2 and getattr(item, "data", None) == "guide_step":
                    children.append(ft.Container(height=1, bgcolor=BORDER))
                children.append(item)
            guide_controls.append(
                ft.Container(
                    border=border_all(1, BORDER),
                    border_radius=16,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Column(spacing=0, controls=children),
                )
            )

        page.show_dialog(
            ft.AlertDialog(
                modal=auto,
                title=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        app_logo_control(46, 14),
                        ft.Column(spacing=2, controls=[ft.Text("SA CHECK User Guide", size=21, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("คู่มือเริ่มต้นสำหรับผู้ใช้ใหม่ กดปิดได้ทุกเมื่อ และเปิดใหม่ได้จากปุ่ม ? ซ้ายล่าง", size=12, color=MUTED)]),
                    ],
                ),
                content=ft.Container(
                    width=760,
                    height=620,
                    content=ft.ListView(
                        spacing=12,
                        controls=guide_controls,
                    ),
                ),
                actions=[
                    ft.TextButton("Open Settings", on_click=lambda _event: (close_manual(), show_settings())),
                    ft.TextButton("Version notes", on_click=open_notes_from_manual),
                    ft.Button("Got it", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=close_manual, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        page.update()

    def task_day(task):
        return task_calendar_date(task)

    calendar_state = {"year": date.today().year, "month": date.today().month, "selected": date.today(), "status": "All"}
    calendar_events = load_persisted_calendar_events()
    settings.setdefault("calendar_event_alerts", {})

    def save_calendar_events():
        save_persisted_calendar_events(calendar_events)
        settings.setdefault("calendar_event_alerts", {})
        save_settings(settings)

    def event_date_value(event):
        try:
            return datetime.strptime(str(event.get("date", ""))[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def events_for_day(day):
        return [event for event in calendar_events if event_date_value(event) == day]

    def show_calendar_event_dialog(event=None, selected_date=None):
        editing = event is not None
        source = event or {}
        title_field = ft.TextField(label="Event name", value=source.get("title", ""), height=48, border_radius=12, border_color=BORDER)
        try:
            picker_date = datetime.strptime(str(source.get("date") or (selected_date or calendar_state["selected"]).isoformat())[:10], "%Y-%m-%d").date()
        except ValueError:
            picker_date = selected_date or calendar_state["selected"] or date.today()
        try:
            picker_time = datetime.strptime(str(source.get("time") or "09:00")[:5], "%H:%M").time()
        except ValueError:
            picker_time = datetime.strptime("09:00", "%H:%M").time()
        picker_state = {"date": picker_date, "hour": picker_time.hour, "minute": picker_time.minute}
        date_field = ft.TextField(
            label="Selected date",
            value=picker_state["date"].isoformat(),
            height=50,
            hint_text="YYYY-MM-DD",
            border_radius=14,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            prefix_icon=ft.Icons.EVENT_OUTLINED,
        )
        time_field = ft.TextField(
            label="Selected time",
            value=f"{picker_state['hour']:02d}:{picker_state['minute']:02d}",
            height=50,
            width=180,
            hint_text="HH:MM",
            border_radius=14,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            prefix_icon=ft.Icons.ACCESS_TIME,
        )
        kind_field = dropdown(190, source.get("kind", "Event"), ["Event", "Holiday", "Meeting", "Deadline", "Note"])
        remind_options = {"At event time": 0, "5 minutes before": 5, "10 minutes before": 10, "30 minutes before": 30, "1 hour before": 60}
        try:
            current_lead = max(0, int(source.get("remind_before") or 0))
        except (TypeError, ValueError):
            current_lead = 0
        remind_label = next((label for label, minutes in remind_options.items() if minutes == current_lead), "At event time")
        remind_field = dropdown(200, remind_label, list(remind_options.keys()))

        no_link_label = "(No linked work)"
        task_label_to_id = {}
        task_options = [no_link_label]
        for linked in sorted(all_tasks, key=lambda item: item.get("name", "").casefold()):
            base_label = linked.get("name") or "Untitled"
            label = base_label
            counter = 2
            while label in task_label_to_id:
                label = f"{base_label} #{counter}"
                counter += 1
            task_label_to_id[label] = linked.get("id")
            task_options.append(label)
        current_link_label = next((label for label, tid in task_label_to_id.items() if tid == source.get("task_id")), no_link_label)
        task_field = dropdown(320, current_link_label, task_options)

        def open_linked_task(_e):
            linked_task = next((item for item in all_tasks if item.get("id") == source.get("task_id")), None)
            if linked_task and open_target(linked_task):
                return
            show_message(page, "Cannot open", "The linked work item was not found on the board.")

        recurrence_options = {"Does not repeat": "none", "Every day": "daily", "Every week": "weekly", "Every month": "monthly"}
        current_recurrence = str(source.get("recurrence") or "none").lower()
        recurrence_label = next((label for label, value in recurrence_options.items() if value == current_recurrence), "Does not repeat")
        recurrence_field = dropdown(220, recurrence_label, list(recurrence_options.keys()))
        until_field = ft.TextField(label="Repeat until (optional)", value=str(source.get("recurrence_until") or "")[:10], width=200, hint_text="YYYY-MM-DD", border_radius=12, border_color=BORDER)

        selected_color = {"value": calendar_event_style(source)[0]}
        color_preview = ft.Container(width=34, height=34, border_radius=12, bgcolor=selected_color["value"], border=border_all(1, BORDER))
        notify_switch = ft.Switch(label="Daily summary at 09:00", value=bool(source.get("notify", True)))
        alarm_switch = ft.Switch(label="Alarm again at event time", value=bool(source.get("alarm", True)))
        note_field = ft.TextField(label="Note", value=source.get("note", ""), multiline=True, min_lines=2, max_lines=2, border_radius=12, border_color=BORDER)
        color_choices = list(CALENDAR_EVENT_COLOR_CHOICES)

        def update_picker_fields():
            date_field.value = picker_state["date"].isoformat()
            time_field.value = f"{picker_state['hour']:02d}:{picker_state['minute']:02d}"
            page.update()

        update_picker_fields()

        def pick_event_color(color):
            selected_color["value"] = color
            color_preview.bgcolor = color
            for swatch in color_swatch_controls:
                is_selected = swatch.data == color
                swatch.border = border_all(3, TEXT if is_selected else WHITE)
                swatch.content = ft.Icon(ft.Icons.CHECK, size=14, color=WHITE) if is_selected else None
            page.update()

        def event_color_swatch(color):
            return ft.Container(
                width=24,
                height=24,
                border_radius=999,
                bgcolor=color,
                data=color,
                alignment=CENTER,
                border=border_all(3, TEXT if color == selected_color["value"] else WHITE),
                content=ft.Icon(ft.Icons.CHECK, size=13, color=WHITE) if color == selected_color["value"] else None,
                on_click=lambda _e, value=color: pick_event_color(value),
            )

        color_swatch_controls = [event_color_swatch(color) for color in color_choices]

        def clear_event_alert_keys(event_id):
            alerts = settings.setdefault("calendar_event_alerts", {})
            for key in list(alerts.keys()):
                if f":{event_id}:" in key or key.endswith(f":{event_id}"):
                    alerts.pop(key, None)

        def save_event(_event):
            title = (title_field.value or "").strip()
            if not title:
                show_message(page, "Missing event name", "Please enter an event name.")
                return
            date_text = str(date_field.value or "").strip()
            time_text = str(time_field.value or "").strip()
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
                show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-22.")
                return
            if not re.fullmatch(r"\d{2}:\d{2}", time_text):
                show_message(page, "Invalid time", "Use 24-hour HH:MM, for example 09:00 or 13:30.")
                return
            try:
                parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            except ValueError:
                show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-22.")
                return
            try:
                parsed_time = datetime.strptime(time_text, "%H:%M").time()
            except ValueError:
                show_message(page, "Invalid time", "Use 24-hour HH:MM, for example 09:00 or 13:30.")
                return
            picker_state["date"] = parsed_date
            picker_state["hour"] = parsed_time.hour
            picker_state["minute"] = parsed_time.minute
            parsed = parsed_date.isoformat()
            event_time = f"{parsed_time.hour:02d}:{parsed_time.minute:02d}"
            event_id = source.get("id") or str(uuid.uuid4())
            linked_task_id = task_label_to_id.get(task_field.value)
            linked_task = next((item for item in all_tasks if item.get("id") == linked_task_id), None) if linked_task_id else None
            payload = {
                "id": event_id,
                "title": title,
                "date": parsed,
                "time": event_time,
                "kind": kind_field.value or "Event",
                "color": selected_color["value"] or "#7C3AED",
                "notify": bool(notify_switch.value),
                "alarm": bool(alarm_switch.value),
                "remind_before": remind_options.get(remind_field.value, 0),
                "task_id": linked_task_id,
                "task_name": linked_task.get("name", "") if linked_task else "",
                "recurrence": recurrence_options.get(recurrence_field.value, "none"),
                "recurrence_until": (until_field.value or "").strip()[:10],
                "note": note_field.value or "",
                "created_at": source.get("created_at") or datetime.now().isoformat(timespec="seconds"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            try:
                clear_event_alert_keys(event_id)
                merged = [event for event in load_persisted_calendar_events() if event.get("id") != event_id]
                merged.append(payload)
                calendar_events[:] = merged
                save_calendar_events()
            except Exception as exc:
                show_message(page, "Calendar save failed", f"Could not save this event. {exc}")
                return
            page.pop_dialog()
            render_current()
            show_message(page, "Calendar event", "Event saved.")

        def delete_event(_event):
            if editing:
                try:
                    calendar_events[:] = [event for event in load_persisted_calendar_events() if event.get("id") != source.get("id")]
                    save_calendar_events()
                except Exception as exc:
                    show_message(page, "Calendar delete failed", f"Could not delete this event. {exc}")
                    return
                page.pop_dialog()
                render_current()
                show_message(page, "Calendar event", "Event deleted.")

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    spacing=12,
                    controls=[
                        ft.Container(width=42, height=42, border_radius=14, bgcolor=selected_color["value"] + "22", alignment=CENTER, content=ft.Icon(ft.Icons.CELEBRATION_OUTLINED, color=selected_color["value"])),
                        ft.Column(spacing=2, controls=[ft.Text("Edit calendar event" if editing else "Add calendar event", size=22, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Events can have a daily 09:00 summary and their own alarm time.", size=12, color=MUTED)]),
                    ],
                ),
                content=ft.Column(
                    width=680,
                    height=400,
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        title_field,
                        ft.Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.LINK_ROUNDED, size=18, color=MUTED),
                                ft.Text("Linked work", size=12, weight=ft.FontWeight.W_700, color=MUTED),
                                ft.Container(expand=True, content=task_field),
                                ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, tooltip="Open linked work", icon_color=PRIMARY, on_click=open_linked_task, visible=bool(source.get("task_id"))),
                            ],
                        ),
                        ft.Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.REPEAT_ROUNDED, size=18, color=MUTED),
                                ft.Text("Repeat", size=12, weight=ft.FontWeight.W_700, color=MUTED),
                                recurrence_field,
                                ft.Container(expand=True),
                                until_field,
                            ],
                        ),
                        ft.Container(
                            padding=pad_sym(horizontal=12, vertical=10),
                            border_radius=16,
                            bgcolor="#F8FAFC",
                            border=border_all(1, BORDER),
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Row(
                                        spacing=10,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Container(expand=True, content=date_field),
                                            time_field,
                                            kind_field,
                                        ],
                                    ),
                                    ft.Text("Stable mode: enter date as YYYY-MM-DD and time as 24-hour HH:MM.", size=10, color=MUTED),
                                ],
                            ),
                        ),
                        ft.Container(
                            padding=pad_sym(horizontal=12, vertical=10),
                            border_radius=16,
                            bgcolor="#F8FAFC",
                            border=border_all(1, BORDER),
                            content=ft.Column(
                                spacing=7,
                                controls=[
                                    ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[color_preview, ft.Text("Event color", size=13, weight=ft.FontWeight.W_900, color=TEXT)]),
                                    ft.Row(spacing=7, controls=color_swatch_controls[:17]),
                                    ft.Row(spacing=7, controls=color_swatch_controls[17:]),
                                ],
                            ),
                        ),
                        ft.Row(
                            spacing=14,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[notify_switch, alarm_switch, ft.Container(expand=True), ft.Text("Remind", size=12, weight=ft.FontWeight.W_700, color=MUTED), remind_field],
                        ),
                        note_field,
                    ],
                ),
                actions=[
                    ft.TextButton("Delete", on_click=delete_event, visible=editing, style=ft.ButtonStyle(color="#DC2626")),
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Save event", icon=ft.Icons.SAVE_OUTLINED, on_click=save_event, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def show_event_detail_dialog(event):
        color, bg = calendar_event_style(event)
        event_time = event.get("time", "09:00")
        note_text = event.get("note") or "No note for this event."

        def edit_from_detail(_event):
            page.pop_dialog()
            show_calendar_event_dialog(event)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    spacing=16,
                    controls=[
                        ft.Container(width=64, height=64, border_radius=20, bgcolor=bg, border=border_all(1, color + "66"), alignment=CENTER, content=ft.Icon(ft.Icons.CELEBRATION_OUTLINED, size=34, color=color)),
                        ft.Column(
                            spacing=5,
                            expand=True,
                            controls=[
                                ft.Text(event.get("title", "Event"), size=28, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Container(padding=pad_sym(horizontal=10, vertical=5), border_radius=999, bgcolor=bg, content=ft.Text(event.get("kind", "Event"), size=12, weight=ft.FontWeight.W_900, color=color)),
                                        ft.Container(padding=pad_sym(horizontal=10, vertical=5), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(event.get("date", "-"), size=12, weight=ft.FontWeight.W_800, color=MUTED)),
                                        ft.Container(padding=pad_sym(horizontal=10, vertical=5), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(event_time, size=12, weight=ft.FontWeight.W_800, color=MUTED)),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                content=ft.Column(
                    width=680,
                    height=360,
                    spacing=16,
                    controls=[
                        ft.Container(
                            bgcolor=bg,
                            border=border_all(1, color + "55"),
                            border_radius=18,
                            padding=16,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, color=color), ft.Text("Alerts", size=16, weight=ft.FontWeight.W_900, color=TEXT)]),
                                    ft.Text(("Daily summary at 09:00" if event.get("notify", True) else "Daily summary off") + (" | Event-time alarm on" if event.get("alarm", True) else " | Event-time alarm off"), size=13, color=MUTED),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            bgcolor="#F8FAFC",
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=16,
                            content=ft.Column(
                                spacing=10,
                                controls=[
                                    ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.NOTES_OUTLINED, color=MUTED), ft.Text("Event Note", size=16, weight=ft.FontWeight.W_900, color=TEXT)]),
                                    ft.Text(note_text, size=14, color=TEXT, selectable=True),
                                ],
                            ),
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Edit Event", icon=ft.Icons.EDIT_OUTLINED, on_click=edit_from_detail, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        page.update()

    def calendar_task_menu(task, after_move=None):
        def move_to(status_value):
            before = dict(task)
            create_snapshot("Before calendar status move")
            if settings.get("move_files_on_status", True):
                try:
                    rename_task_target(task, task.get("name", "Untitled task"), task.get("link", ""), new_file_type=task.get("type", "Other"), new_status=status_value)
                except Exception as exc:
                    show_message(page, "Move failed", str(exc))
                    return
            else:
                apply_status_date(task, status_value)
            remember_task_action("Move status", task, before)
            save_tasks(all_tasks)
            if after_move:
                after_move()
            else:
                render_current()
            show_message(page, APP_NAME, "Status updated.")

        return [
            ft.PopupMenuItem(content="Open", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _e: open_target(task)),
            ft.PopupMenuItem(content="Details", icon=ft.Icons.INFO_OUTLINE, on_click=lambda _e: show_task_detail(page, task, save_and_render, all_tasks)),
            ft.PopupMenuItem(content="Edit date", icon=ft.Icons.EVENT_OUTLINED, on_click=lambda _e: show_task_date_dialog(page, task, save_and_render, all_tasks)),
            ft.PopupMenuItem(content="Folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e: open_folder(task)),
            ft.PopupMenuItem(content="Move to Waiting", icon=ft.Icons.RADIO_BUTTON_UNCHECKED, on_click=lambda _e: move_to(STATUS_PENDING)),
            ft.PopupMenuItem(content="Move to Doing", icon=ft.Icons.PLAY_CIRCLE_OUTLINE, on_click=lambda _e: move_to(STATUS_PROGRESS)),
            ft.PopupMenuItem(content="Move to Success", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda _e: move_to(STATUS_DONE)),
        ]

    def show_calendar(_e=None):
        state["screen"] = SCREEN_CALENDAR
        render_current()

    search_debounce = {"timer": None}

    def on_search(event):
        state["search"] = event.control.value or ""
        state["group_limits"] = {}
        existing = search_debounce.get("timer")
        if existing is not None:
            existing.cancel()
        timer = threading.Timer(0.28, render_current)
        search_debounce["timer"] = timer
        timer.start()

    search_field.on_change = on_search

    def build_sidebar_controls():
        online_state = state.get("online_status", "checking")
        status_color = "#16A34A" if online_state == "online" else "#D97706" if online_state == "checking" else "#DC2626"
        status_text = "Online" if online_state == "online" else "Checking" if online_state == "checking" else "Offline"
        online_enabled = not settings.get("offline_mode", False)
        ACTIVE_BG = "#CCFBF1"
        ACTIVE_FG = "#0F766E"
        HOVER_BG = "#F1F5F9"
        IDLE_FG = "#334155"

        def nav_item(icon, label, screen_key, on_click):
            active = state.get("screen") == screen_key
            item = ft.Container(
                on_click=on_click,
                height=44,
                border_radius=10,
                bgcolor=ACTIVE_BG if active else None,
                padding=pad_only(left=12, right=12),
                animate=ft.Animation(110, ft.AnimationCurve.EASE_OUT),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, size=20, color=ACTIVE_FG if active else MUTED),
                        ft.Text(label, size=14, weight=ft.FontWeight.W_800 if active else ft.FontWeight.W_600, color=ACTIVE_FG if active else IDLE_FG),
                    ],
                ),
            )
            if not active:
                def on_hover(e, control=item):
                    control.bgcolor = HOVER_BG if e.data == "true" else None
                    try:
                        control.update()
                    except Exception:
                        pass
                item.on_hover = on_hover
            return item

        sync_phase = state.get("sync_phase", "idle")
        sync_visuals = {
            "idle": ("#94A3B8", "#F1F5F9", ft.Icons.SYNC_OUTLINED, "Sync idle"),
            "syncing": ("#F59E0B", "#FFFBEB", ft.Icons.SYNC_ROUNDED, "Syncing now"),
            "success": ("#22C55E", "#F0FDF4", ft.Icons.CHECK_CIRCLE_OUTLINE, "Sync successful"),
            "error": ("#EF4444", "#FEF2F2", ft.Icons.ERROR_OUTLINE, "Sync failed"),
        }
        sync_color, sync_bg, sync_icon, sync_label = sync_visuals.get(sync_phase, sync_visuals["error"])
        sync_glyph = (
            breathing_badge(page, sync_icon, sync_color, sync_bg, size=34, radius=11, icon_size=18, ping=True)
            if sync_phase == "syncing"
            else ft.Container(width=40, height=40, border_radius=12, bgcolor=sync_bg, alignment=CENTER, content=ft.Icon(sync_icon, size=19, color=sync_color))
        )
        sync_indicator = ft.Container(
            width=42,
            height=42,
            border_radius=12,
            border=border_all(1, sync_color),
            alignment=CENTER,
            tooltip=f"{sync_label}: {state.get('sync_error') or state.get('sync_message') or ''}",
            on_click=sync_now,
            content=sync_glyph,
        )

        brand = ft.Row(
            spacing=11,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                app_logo_control(38, 11),
                ft.Column(
                    spacing=0,
                    expand=True,
                    controls=[
                        ft.Text(APP_NAME, size=16, weight=ft.FontWeight.W_900, color=TEXT),
                        ft.Text(APP_VERSION, size=10, weight=ft.FontWeight.W_700, color=MUTED_2),
                    ],
                ),
                sync_indicator,
            ],
        )

        signal_color = "#5EEAD4" if online_state == "online" else "#FBBF24" if online_state == "checking" else "#FB7185"
        signal_label = "LIVE SYNC" if online_state == "online" else "CONNECTING" if online_state == "checking" else "OFFLINE"
        signal_icon = ft.Icons.CLOUD_DONE_OUTLINED if online_state == "online" else ft.Icons.SYNC_ROUNDED if online_state == "checking" else ft.Icons.CLOUD_OFF_OUTLINED
        signal_badge = breathing_badge(
            page,
            signal_icon,
            signal_color,
            "#20FFFFFF",
            size=38,
            radius=12,
            icon_size=19,
            ping=online_state == "online",
        ) if online_state != "offline" else ft.Container(width=44, height=44, border_radius=13, bgcolor="#16FFFFFF", alignment=CENTER, content=ft.Icon(signal_icon, size=19, color=signal_color))
        activity_bars = ft.Row(
            spacing=3,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[
                ft.Container(width=4, height=height, border_radius=99, bgcolor=signal_color if online_state != "offline" else "#475569")
                for height in (7, 12, 18, 10, 15)
            ],
        )
        live_dot = pulse_dot(page, signal_color, size=6) if online_state != "offline" else ft.Container(width=8, height=8, border_radius=99, bgcolor=signal_color)
        status_card = ft.Container(
            border_radius=18,
            gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=["#071426", "#0F2A3D", "#0F766E"] if online_state != "offline" else ["#111827", "#1F2937", "#3F1D2E"]),
            border=border_all(1, "#335EEAD4" if online_state != "offline" else "#33FB7185"),
            padding=pad_sym(horizontal=13, vertical=12),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=18, color="#280F766E" if online_state != "offline" else "#18000000", offset=ft.Offset(0, 7)),
            animate=ft.Animation(700, ft.AnimationCurve.EASE_IN_OUT),
            content=ft.Column(
                spacing=11,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Stack(
                                width=43,
                                height=43,
                                controls=[
                                    ft.Container(width=43, height=43, border_radius=13, bgcolor="#0F172A", alignment=CENTER, clip_behavior=ft.ClipBehavior.ANTI_ALIAS, content=profile_media_control(37)),
                                    ft.Container(width=13, height=13, border_radius=99, bgcolor=signal_color, border=border_all(2, "#0F172A"), right=0, bottom=0),
                                ],
                            ),
                            ft.Column(
                                spacing=3,
                                expand=True,
                                controls=[
                                    ft.Row(spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[live_dot, ft.Text(signal_label, size=10, weight=ft.FontWeight.W_900, color=signal_color)]),
                                    ft.Text("SA CHECK NETWORK", size=11, weight=ft.FontWeight.W_900, color=WHITE),
                                    ft.Text("Local-first · protected", size=9, color="#94A3B8"),
                                ],
                            ),
                            signal_badge,
                        ],
                    ),
                    ft.Container(height=1, bgcolor="#20FFFFFF"),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(spacing=2, controls=[
                                ft.Text("ONLINE MODE", size=9, weight=ft.FontWeight.W_900, color="#94A3B8"),
                                ft.Row(spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[activity_bars, ft.Text(status_text, size=11, weight=ft.FontWeight.W_800, color=WHITE)]),
                            ]),
                            ft.Switch(value=online_enabled, scale=0.7, active_color="#2DD4BF", active_track_color="#134E4A", inactive_thumb_color="#94A3B8", inactive_track_color="#334155", on_change=lambda e: confirm_connectivity_change(bool(e.control.value))),
                        ],
                    ),
                ],
            ),
        )
        if online_state != "offline":
            breathe_glow(page, status_card, signal_color, base_blur=14, peak_blur=26, base_alpha="18", peak_alpha="40", period=1.2)

        extras = []
        if state.get("update_available"):
            manifest = state.get("update_manifest") or {}
            extras.append(
                ft.Container(
                    on_click=lambda _e: show_update_prompt(manifest),
                    height=48,
                    border_radius=10,
                    bgcolor="#EFF6FF",
                    border=border_all(1, "#BFDBFE"),
                    padding=pad_only(left=12, right=12),
                    content=ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED, size=20, color="#2563EB"),
                            ft.Column(spacing=0, expand=True, controls=[
                                ft.Text("Update ready", size=13, weight=ft.FontWeight.W_800, color="#1D4ED8"),
                                ft.Text(str(manifest.get("version") or ""), size=10, color="#3B82F6", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ]),
                        ],
                    ),
                )
            )

        def open_updater(_event=None):
            if state.get("update_available") and state.get("update_manifest"):
                show_update_prompt(state.get("update_manifest"))
                return
            check_for_updates(manual=True)

        updater_label = (
            f"Update {str((state.get('update_manifest') or {}).get('version') or '').strip()} ready"
            if state.get("update_available")
            else "Checking updates..."
            if state.get("update_checking") or online_state == "checking"
            else "App updater"
        )

        return [
            brand,
            ft.Container(height=14),
            ft.Text("MENU", size=10, weight=ft.FontWeight.W_900, color=MUTED_2),
            ft.Container(height=4),
            nav_item(ft.Icons.SPACE_DASHBOARD_OUTLINED, "Home", SCREEN_OVERVIEW, show_overview),
            nav_item(ft.Icons.DASHBOARD_ROUNDED, "Board", SCREEN_BOARD, show_board),
            nav_item(ft.Icons.FOLDER_OUTLINED, "Files", SCREEN_BROWSER, show_browser),
            nav_item(ft.Icons.CALENDAR_TODAY_OUTLINED, "Calendar", SCREEN_CALENDAR, show_calendar),
            nav_item(ft.Icons.ARTICLE_OUTLINED, "Templates", SCREEN_TEMPLATES, show_templates),
            nav_item(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "Health", SCREEN_HEALTH, show_health),
            nav_item(ft.Icons.SETTINGS_OUTLINED, "Settings", SCREEN_SETTINGS, show_settings),
            nav_item(ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, updater_label, "__updater__", open_updater),
            ft.Container(expand=True),
            *extras,
            nav_item(ft.Icons.HELP_OUTLINE, "Help & guide", "__help__", show_help),
            ft.Container(height=6),
            status_card,
        ]

    def update_sidebar():
        try:
            sidebar.content.controls = build_sidebar_controls()
        except NameError:
            pass

    sidebar = ft.Container(
        width=236,
        bgcolor=WHITE,
        border=ft.Border(right=ft.BorderSide(1, BORDER)),
        padding=pad_sym(horizontal=16, vertical=20),
        content=ft.Column(
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=build_sidebar_controls(),
        ),
    )

    quick_add = ft.PopupMenuButton(
        content=ft.Container(
            height=46,
            padding=pad_sym(horizontal=18),
            border_radius=14,
            bgcolor=TEXT,
            alignment=CENTER,
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=18, color=WHITE), ft.Text("+ Quick Add", size=15, weight=ft.FontWeight.W_700, color=WHITE)],
            ),
        ),
        items=[
            ft.PopupMenuItem(content="Create new work", icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=show_create_new),
            ft.PopupMenuItem(content="Add files", icon=ft.Icons.UPLOAD_FILE_OUTLINED, on_click=add_files_dialog),
            ft.PopupMenuItem(content="Add link", icon=ft.Icons.LINK_ROUNDED, on_click=lambda _e: add_task_dialog("link")),
            ft.PopupMenuItem(content="Calendar event", icon=ft.Icons.ADD_ALERT_OUTLINED, on_click=lambda _e: show_calendar_event_dialog(selected_date=calendar_state["selected"])),
            ft.PopupMenuItem(content="Templates", icon=ft.Icons.ARTICLE_OUTLINED, on_click=show_templates),
            ft.PopupMenuItem(content="Export report", icon=ft.Icons.IOS_SHARE_OUTLINED, on_click=export_report),
            ft.PopupMenuItem(content="About SA CHECK", icon=ft.Icons.INFO_OUTLINED, on_click=show_about),
            ft.PopupMenuItem(content="Sync now", icon=ft.Icons.SYNC, on_click=sync_now),
        ],
    )

    sync_button = ft.IconButton(icon=ft.Icons.SYNC, tooltip="Refresh app, reload Work data, and check for updates", icon_color=MUTED, on_click=sync_now)
    export_button = ft.IconButton(icon=ft.Icons.IOS_SHARE_OUTLINED, tooltip="Export report", icon_color=MUTED, on_click=export_report)
    about_button = ft.IconButton(icon=ft.Icons.INFO_OUTLINED, tooltip="About SA CHECK", icon_color=MUTED, on_click=show_about)

    palette_button = ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Search or jump (Ctrl+K)", icon_color=MUTED, on_click=lambda _e: open_command_palette())

    live_work_dot = ft.Container(width=8, height=8, border_radius=99, bgcolor="#94A3B8")
    live_work_text = ft.Text("No active Doing work", size=12, weight=ft.FontWeight.W_800, color=MUTED, max_lines=1)
    live_work_time = ft.Text("--:--", size=12, weight=ft.FontWeight.W_900, color="#D97706")
    live_work_strip = ft.Container(
        expand=True,
        height=46,
        margin=pad_sym(horizontal=20),
        padding=pad_sym(horizontal=14),
        border_radius=14,
        bgcolor="#FFFBEB",
        border=border_all(1, "#FDE68A"),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                live_work_dot,
                ft.Text("Doing ·", size=11, weight=ft.FontWeight.W_900, color="#B45309"),
                ft.Container(width=1, height=22, bgcolor="#FDE68A"),
                ft.Container(expand=True, clip_behavior=ft.ClipBehavior.HARD_EDGE, content=live_work_text),
                ft.Container(width=1, height=22, bgcolor="#FDE68A"),
                ft.Icon(ft.Icons.SCHEDULE_OUTLINED, size=15, color="#D97706"),
                live_work_time,
            ],
        ),
    )

    def doing_time(task):
        raw = str(task.get("status_changed_at") or task.get("date_added") or "")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed.strftime("%H:%M") if "T" in raw or " " in raw else "--:--"
        except (TypeError, ValueError):
            match = re.search(r"\b(\d{1,2}):(\d{2})\b", raw)
            return f"{int(match.group(1)):02d}:{match.group(2)}" if match else "--:--"

    async def live_work_loop():
        offset = 0
        last_task_id = None
        while not shutdown_event.is_set():
            doing = [task for task in list(all_tasks) if isinstance(task, dict) and task.get("status") == STATUS_PROGRESS]
            if doing:
                def safe_priority(item):
                    try:
                        return int(item.get("priority") or 0)
                    except (TypeError, ValueError):
                        return 0

                doing.sort(key=lambda item: (safe_priority(item), str(item.get("status_changed_at") or item.get("date_added") or "")), reverse=True)
                task = doing[int(time.time() // 8) % len(doing)]
                task_id = task.get("id") or task.get("name")
                name = str(task.get("name") or "Untitled task").strip()
                if task_id != last_task_id:
                    offset = 0
                    last_task_id = task_id
                if len(name) > 48:
                    lane = name + "     •     "
                    shown = (lane + lane)[offset : offset + 48]
                    offset = (offset + 1) % len(lane)
                else:
                    shown = name
                    offset = 0
                live_work_text.value = shown
                live_work_text.color = TEXT
                live_work_time.value = doing_time(task)
                live_work_dot.bgcolor = "#F59E0B"
            else:
                last_task_id = None
                offset = 0
                live_work_text.value = "No active Doing work"
                live_work_text.color = MUTED
                live_work_time.value = "--:--"
                live_work_dot.bgcolor = "#94A3B8"
            try:
                live_work_text.update()
                live_work_time.update()
                live_work_dot.update()
            except Exception:
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.28)

    header = ft.Container(
        height=96,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=22,
        padding=pad_sym(horizontal=22, vertical=16),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=18, color="#10000000", offset=ft.Offset(0, 6)),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=5,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        header_subtitle,
                        ft.Row(
                            spacing=14,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[header_title, ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#EFF6FF", content=progress_badge)],
                        ),
                    ],
                ),
                live_work_strip,
                ft.Row(spacing=10, controls=[palette_button, about_button, export_button, sync_button, quick_add]),
            ],
        ),
    )

    content = ft.Container(
        expand=True,
        padding=pad_only(left=24, right=24, top=26, bottom=24),
        content=ft.Column(spacing=22, expand=True, controls=[header, main_body]),
    )

    def _minimize(_e):
        try:
            page.window.minimized = True
        except Exception:
            pass

    def _toggle_max(_e):
        try:
            page.window.maximized = not page.window.maximized
            page.update()
        except Exception:
            pass

    def mark_closed(_e=None):
        state["closed"] = True
        shutdown_event.set()

    def _close(_e):
        if state.get("closing"):
            return
        state["closing"] = True
        mark_closed()
        try:
            save_settings(settings)
        finally:
            # The embedded Flutter runner can keep the native process alive
            # after Window.close(). Explicit exit is deterministic and safe
            # because task/calendar writes are persisted at mutation time.
            os._exit(0)

    def window_button(icon, on_click, danger=False, tooltip=""):
        return ft.IconButton(
            icon=icon,
            on_click=on_click,
            tooltip=tooltip,
            width=46,
            height=38,
            padding=0,
            alignment=CENTER,
            icon_size=15,
            icon_color=MUTED,
            hover_color="#EF4444" if danger else "#EEF2F7",
            highlight_color="#DC2626" if danger else "#E2E8F0",
            splash_radius=20,
        )

    title_bar = ft.Container(
        height=38,
        bgcolor=WHITE,
        border=ft.Border(bottom=ft.BorderSide(1, BORDER)),
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.WindowDragArea(
                    ft.Container(
                        height=38,
                        padding=pad_only(left=16),
                        alignment=ft.Alignment(-1, 0),
                        content=ft.Text(APP_NAME, size=12, weight=ft.FontWeight.W_700, color=MUTED_2),
                    ),
                    expand=True,
                    maximizable=True,
                ),
                window_button(ft.Icons.REMOVE, _minimize, tooltip="Minimize"),
                window_button(ft.Icons.CROP_SQUARE, _toggle_max, tooltip="Restore / maximize"),
                window_button(ft.Icons.CLOSE, _close, danger=True, tooltip="Close SA CHECK"),
            ],
        ),
    )

    def open_command_palette(_e=None):
        if state.get("cmd_palette_open"):
            return
        nav_commands = [
            ("Board", ft.Icons.DASHBOARD_ROUNDED, show_board),
            ("Browser", ft.Icons.FOLDER_OUTLINED, show_browser),
            ("Calendar", ft.Icons.CALENDAR_TODAY_OUTLINED, show_calendar),
            ("Templates", ft.Icons.ARTICLE_OUTLINED, show_templates),
            ("Health", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, show_health),
            ("Settings", ft.Icons.SETTINGS_OUTLINED, show_settings),
            ("Create new work", ft.Icons.ADD_CIRCLE_OUTLINE, show_create_new),
            ("Sync now", ft.Icons.SYNC, sync_now),
        ]
        results = ft.ListView(spacing=4, height=330)

        def close(_event=None):
            if not state.get("cmd_palette_open"):
                return
            state["cmd_palette_open"] = False
            page.pop_dialog()
            page.update()

        def run_cmd(handler):
            close()
            try:
                handler()
            except Exception as exc:
                record_runtime_failure("Command palette", exc)
                show_message(page, "Command failed", str(exc), kind="danger")

        def open_task(task):
            close()
            show_task_detail(page, task, save_and_render, all_tasks)

        def result_row(icon, title, subtitle, on_click, color=None):
            accent = color or PRIMARY
            return ft.Container(
                on_click=lambda _e: on_click(),
                border_radius=10,
                padding=pad_sym(horizontal=10, vertical=8),
                content=ft.Row(
                    spacing=11,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=30, height=30, border_radius=8, bgcolor=accent + "1A", alignment=CENTER, content=ft.Icon(icon, size=16, color=accent)),
                        ft.Column(spacing=0, expand=True, controls=[
                            ft.Text(title, size=13, weight=ft.FontWeight.W_700, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(subtitle, size=10, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ]),
                        ft.Icon(ft.Icons.KEYBOARD_RETURN, size=13, color=MUTED_2),
                    ],
                ),
            )

        def render(query):
            q = (query or "").strip().casefold()
            rows = []
            for label, icon, handler in nav_commands:
                if not q or q in label.casefold():
                    rows.append(result_row(icon, label, "Command", lambda h=handler: run_cmd(h)))
            if q:
                matched = []
                for task in all_tasks:
                    haystack = f"{task.get('name', '')} {task.get('type', '')} {task.get('note', '')}".casefold()
                    if q in haystack:
                        matched.append(task)
                    if len(matched) >= 8:
                        break
                for task in matched:
                    task_ic, task_color = task_icon(task.get("type", "Other"))
                    rows.append(result_row(task_ic, task.get("name", "Untitled task"), f"{task.get('type', 'Other')} work", lambda t=task: open_task(t), color=task_color))
            if not rows:
                rows.append(ft.Container(padding=16, alignment=CENTER, content=ft.Text("No matches", size=12, color=MUTED_2)))
            results.controls = rows
            try:
                page.update()
            except Exception:
                pass

        query_field = ft.TextField(
            hint_text="Jump to a screen or search work...",
            autofocus=True,
            border_radius=10,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            bgcolor=WHITE,
            text_size=14,
            prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: render(e.control.value),
        )
        render("")
        state["cmd_palette_open"] = True
        page.show_dialog(
            ft.AlertDialog(
                modal=False,
                content=ft.Container(
                    width=560,
                    content=ft.Column(
                        spacing=12,
                        tight=True,
                        controls=[
                            query_field,
                            results,
                            ft.Text("Ctrl+K open  ·  Esc close", size=10, color=MUTED_2),
                        ],
                    ),
                ),
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
                on_dismiss=lambda _e: state.update({"cmd_palette_open": False}),
            )
        )
        page.update()

    def on_global_key(event):
        try:
            key = str(getattr(event, "key", "")).lower()
            if (getattr(event, "ctrl", False) or getattr(event, "meta", False)) and key == "k":
                open_command_palette()
            elif key == "escape" and state.get("cmd_palette_open"):
                state["cmd_palette_open"] = False
                page.pop_dialog()
                page.update()
        except Exception:
            pass

    page.on_keyboard_event = on_global_key
    page.on_disconnect = mark_closed
    page.on_close = mark_closed

    page.add(
        ft.Column(
            spacing=0,
            expand=True,
            controls=[
                title_bar,
                ft.Row(spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH, controls=[sidebar, content]),
            ],
        )
    )
    try:
        page.run_task(live_work_loop)
    except Exception as exc:
        record_runtime_failure("Live work strip", exc)
    render_current()
    if state.get("update_available") and state.get("update_manifest"):
        manifest = state["update_manifest"]
        dismissed = int(settings.get("update_dismiss_count", 0)) if settings.get("last_update_prompt_version") == manifest.get("version") else 0
        forced_reason = update_force_reason(manifest.get("version"), manifest, dismissed)
        auto_start = bool(forced_reason and (manifest.get("required") or is_core_platform_update(manifest.get("version"))))
        show_update_prompt(manifest, forced=bool(forced_reason), auto_start=auto_start)
    elif settings.get("manual_seen_version") != MANUAL_VERSION:
        show_help(auto=True)
    if startup_result is None or (
        getattr(startup_result, "warning", "")
        and getattr(startup_result, "online_enabled", False)
    ):
        check_for_updates(manual=False)
    elif getattr(startup_result, "health_issues", None):
        show_message(page, "Startup health", "Some app files need attention. Open Health Center for details.", kind="warning")

    def show_event_reminder_popup(events, reminder_day, title="Today's reminders", alert_time="09:00"):
        if not events:
            return
        show_windows_toast(f"{APP_NAME} Calendar", f"{len(events)} reminder(s) for {reminder_day.strftime('%d %b %Y')}")
        show_message(page, "Calendar reminder", f"{len(events)} event(s) due now.", kind="warning")

        def event_line(event):
            color, bg = calendar_event_style(event)
            event_time = event.get("time", alert_time)
            linked_task = next((item for item in all_tasks if item.get("id") == event.get("task_id")), None) if event.get("task_id") else None
            subtitle = event.get("note") or event.get("kind", "Event")
            if linked_task or event.get("task_name"):
                subtitle = f"Linked: {linked_task.get('name') if linked_task else event.get('task_name')}"

            def open_linked(_e, task=linked_task):
                if task and open_target(task):
                    return
                show_message(page, "Cannot open", "The linked work item was not found.")

            return ft.Container(
                bgcolor=bg,
                border=border_all(1, color + "55"),
                border_radius=12,
                padding=pad_sym(horizontal=12, vertical=9),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.LINK_ROUNDED if linked_task else ft.Icons.CELEBRATION_OUTLINED, size=18, color=color),
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(event.get("title", "Event"), size=14, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(subtitle, size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        ft.IconButton(icon=ft.Icons.OPEN_IN_NEW, icon_size=16, tooltip="Open linked work", icon_color=color, on_click=open_linked, visible=bool(linked_task)),
                        ft.Text(event_time, size=12, weight=ft.FontWeight.W_900, color=color),
                    ],
                ),
            )

        def open_calendar_day(_event):
            calendar_state.update({"year": reminder_day.year, "month": reminder_day.month, "selected": reminder_day})
            page.pop_dialog()
            show_calendar()

        page.show_dialog(
            ft.AlertDialog(
                modal=False,
                title=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, color="#D97706"),
                        ft.Text(title, size=20, weight=ft.FontWeight.W_900, color=TEXT),
                    ],
                ),
                content=ft.Column(
                    width=520,
                    height=min(300, 78 * len(events) + 26),
                    spacing=10,
                    controls=[
                        ft.Text(reminder_day.strftime("%A, %d %B %Y"), size=13, weight=ft.FontWeight.W_700, color=MUTED),
                        ft.ListView(spacing=8, expand=True, controls=[event_line(event) for event in events]),
                    ],
                ),
                actions=[
                    ft.TextButton("Close", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Open Calendar", icon=ft.Icons.CALENDAR_TODAY_OUTLINED, on_click=open_calendar_day, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def event_alarm_datetime(event, day_key):
        try:
            base = datetime.strptime(f"{day_key} {event.get('time', '09:00')}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None
        try:
            lead = max(0, int(event.get("remind_before") or 0))
        except (TypeError, ValueError):
            lead = 0
        return base - timedelta(minutes=lead)

    def check_calendar_event_reminders():
        calendar_events[:] = load_persisted_calendar_events()
        now = datetime.now()
        today_key = now.date().isoformat()
        now_hm = now.strftime("%H:%M")
        notified = settings.setdefault("calendar_event_alerts", {})
        for stale_key in [key for key in notified if not (key.startswith(f"daily:{today_key}:") or key.startswith(f"alarm:{today_key}:"))]:
            notified.pop(stale_key, None)
        last_check = None
        last_check_raw = settings.get("calendar_last_check")
        if last_check_raw:
            try:
                last_check = datetime.fromisoformat(last_check_raw)
            except ValueError:
                last_check = None
        today = now.date()
        due_daily = []
        due_alarm = []
        due_missed = []
        for event in calendar_events:
            event_id = event.get("id") or event.get("title", "")
            if not event_occurs_on(event, today):
                continue
            if event.get("notify", True) and now_hm >= "09:00":
                daily_key = f"daily:{today_key}:{event_id}:09:00"
                if not notified.get(daily_key):
                    due_daily.append(event)
                    notified[daily_key] = now.isoformat(timespec="seconds")
            alarm_dt = event_alarm_datetime(event, today_key)
            if event.get("alarm", True) and alarm_dt and now >= alarm_dt:
                alarm_key = f"alarm:{today_key}:{event_id}:{event.get('time', '09:00')}"
                if not notified.get(alarm_key):
                    due_alarm.append(event)
                    notified[alarm_key] = now.isoformat(timespec="seconds")
        if last_check:
            cursor = max(last_check.date(), today - timedelta(days=14))
            while cursor < today:
                for event in calendar_events:
                    if not event.get("alarm", True) or not event_occurs_on(event, cursor):
                        continue
                    alarm_dt = event_alarm_datetime(event, cursor.isoformat())
                    if alarm_dt and last_check < alarm_dt <= now:
                        due_missed.append(event)
                cursor += timedelta(days=1)
        settings["calendar_last_check"] = now.isoformat(timespec="seconds")
        if due_daily or due_alarm or due_missed:
            save_calendar_events()
            combined = []
            seen = set()
            for item in [*due_alarm, *due_missed, *due_daily]:
                key = item.get("id") or item.get("title", "")
                if key in seen:
                    continue
                seen.add(key)
                combined.append(item)
            popup_title = "Missed reminders" if due_missed else "Event-time alarm" if due_alarm else "Today's reminders"
            show_event_reminder_popup(combined, now.date(), popup_title, now_hm)
        elif last_check_raw is None:
            save_settings(settings)

    def realtime_sync_loop():
        while not shutdown_event.wait(sync_interval_seconds()):
            try:
                check_calendar_event_reminders()
                if settings.get("realtime_sync_enabled", True) and auto_sync_from_work():
                    render_current()
                now = datetime.now()
                update_day_key = now.date().isoformat()
                if now.strftime("%H:%M") >= "09:00" and settings.get("last_0900_update_check") != update_day_key and not settings.get("offline_mode", False):
                    settings["last_0900_update_check"] = update_day_key
                    save_settings(settings)
                    check_for_updates(manual=False)
                if time.time() - float(state.get("last_update_check") or 0) > update_check_interval_seconds():
                    check_for_updates(manual=False)
            except Exception as exc:
                state["syncing"] = False
                fail_sync("Realtime sync loop", exc)

    page.run_thread(realtime_sync_loop)
    page.run_thread(lambda: (time.sleep(2), check_calendar_event_reminders()))
    state["native_drop_bridge"] = install_native_file_drop(
        APP_NAME,
        lambda paths: page.run_thread(
            lambda: file_drop_receiver["callback"](paths)
            if file_drop_receiver.get("callback")
            else add_files_dialog(initial_paths=paths)
        ),
    )


def task_calendar_date(task):
    if task.get("status") == STATUS_DONE and task.get("done_date"):
        return str(task.get("done_date"))[:10]
    return str(task.get("status_date") or task.get("date_added") or datetime.now().date().isoformat())[:10]


def set_task_calendar_date(task, date_text):
    parsed = datetime.strptime((date_text or "").strip(), "%Y-%m-%d").date().isoformat()
    task["status_date"] = parsed
    if task.get("status") == STATUS_DONE:
        task["done_date"] = parsed
    else:
        task["done_date"] = None
    return parsed


def show_task_date_dialog(page, task, save_and_render, all_tasks=None):
    date_field = ft.TextField(
        label="Calendar date",
        hint_text="YYYY-MM-DD",
        value=task_calendar_date(task),
        border_radius=12,
        border_color=BORDER,
        prefix_icon=ft.Icons.EVENT_OUTLINED,
    )
    status_label = STATUS_LABELS.get(task.get("status"), "Waiting")

    def save_date(_event):
        before = dict(task)
        try:
            new_date = set_task_calendar_date(task, date_field.value)
        except ValueError:
            show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-15.")
            return
        create_snapshot("Before task date edit")
        if all_tasks is not None:
            push_undo({"kind": "task_restore", "action": "Edit calendar date", "task_id": task.get("id"), "before": before, "after": dict(task)})
        log_activity("Edit calendar date", f"{task.get('name', 'Untitled task')} set to {new_date}.", {"task_id": task.get("id"), "before": before, "after": dict(task)})
        page.pop_dialog()
        save_and_render("Calendar date updated.")

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit calendar date", size=20, weight=ft.FontWeight.W_800, color=TEXT),
            content=ft.Column(
                width=420,
                height=150,
                spacing=12,
                controls=[
                    ft.Text(task.get("name", "Untitled task"), size=15, weight=ft.FontWeight.W_700, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"Status: {status_label}", size=13, color=MUTED),
                    date_field,
                ],
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                ft.Button("Save date", icon=ft.Icons.SAVE_OUTLINED, on_click=save_date, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
            ],
            bgcolor=WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )
    page.update()


def show_task_detail(page, task, save_and_render, all_tasks, is_template=False, template_to_work=None, template_records=None):
    icon, icon_color = task_icon(task.get("type", "Other"))
    status_label = STATUS_LABELS.get(task.get("status"), "Template" if is_template else "Waiting")
    target = task.get("link", "") or task.get("shortcut_path", "")
    note = task.get("note") or "No note"
    current_status_label = STATUS_LABELS.get(task.get("status"), "Waiting")
    status_options = ["Waiting", "Doing", "Success"]
    status_lookup = {"Waiting": STATUS_PENDING, "Doing": STATUS_PROGRESS, "Success": STATUS_DONE}
    is_untracked_browser_item = bool(all_tasks is not None and not is_template and task not in all_tasks)

    def status_style(status):
        if status == STATUS_PROGRESS or status == "Doing":
            return "Doing", DOING_TEXT, DOING_BG
        if status == STATUS_DONE or status == "Success":
            return "Success", DONE_TEXT, DONE_BG
        if status == "Template":
            return "Template", PRIMARY, "#EFF6FF"
        return "Waiting", WAITING_TEXT, WAITING_BG

    def status_pill(status, label=None):
        resolved_label, color, bg = status_style(status)
        return animated_status_pill(
            page,
            label or resolved_label,
            color,
            bg,
            pulse=(status == STATUS_PROGRESS or status == "Doing"),
        )

    def set_status(status):
        before = dict(task)
        create_snapshot("Before detail status move")
        if load_settings().get("move_files_on_status", True):
            try:
                rename_task_target(task, task.get("name", "Untitled task"), task.get("link", ""), new_file_type=task.get("type", "Other"), new_status=status)
            except Exception as exc:
                show_message(page, "Move failed", str(exc))
                return
        else:
            apply_status_date(task, status)
        push_undo({"kind": "task_restore", "action": "Move status", "task_id": task.get("id"), "before": before, "after": dict(task)})
        log_activity("Move status", f"{task.get('name', 'Untitled task')} moved.", {"task_id": task.get("id"), "before": before, "after": dict(task)})
        page.pop_dialog()
        save_and_render("Status updated.")

    def delete_task(_event):
        def confirm_delete(_confirm_event):
            before = dict(task)
            create_snapshot("Before task delete")
            try:
                delete_item_target(task)
            except Exception as exc:
                show_message(page, "Delete failed", str(exc))
                return
            if task in all_tasks:
                all_tasks.remove(task)
            push_undo({"kind": "task_restore", "action": "Delete task", "task_id": task.get("id"), "before": before, "after": {}})
            log_activity("Delete task", f"{before.get('name', 'Untitled task')} removed from board.", {"task_id": before.get("id")})
            page.pop_dialog()
            save_and_render("Task deleted.")

        page.pop_dialog()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Delete task?", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Container(
                    border=border_all(1, "#FECACA"),
                    border_radius=14,
                    bgcolor="#FEF2F2",
                    padding=pad_sym(horizontal=14, vertical=12),
                    content=ft.Row(
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#DC2626", size=22),
                            ft.Text(f"This removes the {APP_NAME} record and deletes the Work file/shortcut when it is inside the Work folder.", size=14, color="#991B1B"),
                        ],
                    ),
                ),
                actions=[
                    ft.TextButton("No", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button(
                        "Yes, delete",
                        on_click=confirm_delete,
                        style=ft.ButtonStyle(color=WHITE, bgcolor="#DC2626", overlay_color="#B91C1C", shape=ft.RoundedRectangleBorder(radius=10)),
                    ),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def edit_task(_event):
        name_field = ft.TextField(label="Task name", value=task.get("name", ""), border_radius=12, border_color=BORDER)
        type_field = dropdown(520, task.get("type", "Other"), runtime_file_types())
        status_field = dropdown(520, current_status_label, status_options)
        target_field = ft.TextField(label="Target path / URL", value=target, border_radius=12, border_color=BORDER)
        date_field = ft.TextField(label="Calendar date", value=task_calendar_date(task), hint_text="YYYY-MM-DD", border_radius=12, border_color=BORDER, prefix_icon=ft.Icons.EVENT_OUTLINED)
        note_field = ft.TextField(label="Note / description", value=task.get("note", ""), multiline=True, min_lines=10, max_lines=10, border_radius=12, border_color=BORDER)

        def save_edit(_save_event):
            new_target = target_field.value.strip()
            new_type = type_field.value or task.get("type", "Other")
            new_status = status_lookup.get(status_field.value, task.get("status", STATUS_PENDING))
            before = dict(task)
            try:
                parsed_date = datetime.strptime((date_field.value or "").strip(), "%Y-%m-%d").date().isoformat()
            except ValueError:
                show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-15.")
                return
            create_snapshot("Before task edit")
            try:
                rename_task_target(
                    task,
                    name_field.value.strip() or task.get("name", "Untitled task"),
                    new_target,
                    new_file_type=new_type,
                    new_status=new_status,
                )
            except Exception as exc:
                show_message(page, "Rename failed", str(exc))
                return
            task["type"] = new_type
            task["detected_type"] = task.get("detected_type") or task["type"]
            task["note"] = note_field.value.strip()
            set_task_calendar_date(task, parsed_date)
            push_undo({"kind": "task_restore", "action": "Edit task", "task_id": task.get("id"), "before": before, "after": dict(task)})
            log_activity("Edit task", f"{task.get('name', 'Untitled task')} edited.", {"task_id": task.get("id"), "before": before, "after": dict(task)})
            page.pop_dialog()
            save_and_render("Task updated.")

        page.pop_dialog()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    spacing=16,
                    controls=[
                        ft.Container(width=58, height=58, border_radius=16, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=32, color=icon_color)),
                        ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(f"Edit Task: {task.get('name', 'Untitled task')}", size=20, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(modified_text(), size=13, color=MUTED),
                            ],
                        ),
                    ],
                ),
                content=ft.Row(
                    width=980,
                    height=520,
                    spacing=24,
                    controls=[
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=22,
                            content=ft.Column(
                                spacing=16,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=MUTED), ft.Text("Core Details", size=18, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    name_field,
                                    ft.Column(spacing=8, controls=[ft.Text("File type", size=13, weight=ft.FontWeight.W_800, color=TEXT), type_field]),
                                    ft.Column(spacing=8, controls=[ft.Text("Status", size=13, weight=ft.FontWeight.W_800, color=TEXT), status_field]),
                                    date_field,
                                    ft.Column(spacing=8, controls=[ft.Text("Target Path / URL", size=13, weight=ft.FontWeight.W_800, color=TEXT), target_field]),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=22,
                            content=ft.Column(
                                spacing=16,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, color=MUTED), ft.Text("Detailed Notes", size=18, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    note_field,
                                ],
                            ),
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Save Changes", icon=ft.Icons.SAVE_OUTLINED, on_click=save_edit, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def edit_template(_event):
        if not is_template:
            edit_task(_event)
            return
        name_field = ft.TextField(label="Template name", value=task.get("name", ""), border_radius=12, border_color=BORDER)
        type_field = dropdown(520, task.get("type", "Other"), runtime_file_types())
        target_field = ft.TextField(label="Template file / URL", value=target, border_radius=12, border_color=BORDER)
        date_field = ft.TextField(label="Template date", value=str(task.get("date_added") or datetime.now().strftime("%Y-%m-%d"))[:10], hint_text="YYYY-MM-DD", border_radius=12, border_color=BORDER, prefix_icon=ft.Icons.EVENT_OUTLINED)
        note_field = ft.TextField(label="Note / description", value=task.get("note", ""), multiline=True, min_lines=8, max_lines=8, border_radius=12, border_color=BORDER)

        def save_template_edit(_save_event):
            new_name = safe_item_name(name_field.value, task.get("name", "Template"))
            new_type = type_field.value or task.get("type", "Other")
            new_target = (target_field.value or target).strip()
            try:
                parsed_date = datetime.strptime((date_field.value or "").strip(), "%Y-%m-%d").date().strftime("%Y-%m-%d")
            except ValueError:
                show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-15.")
                return
            if not new_target:
                show_message(page, "Missing target", "Choose a template file or URL.")
                return
            before = dict(task)
            create_snapshot("Before template edit")
            try:
                update_template_record(task, new_name, file_type=new_type, target=new_target, note=note_field.value or "", date_added=parsed_date)
                task["id"] = before.get("id") or task.get("id")
                task["usage_count"] = before.get("usage_count", task.get("usage_count", 0))
                task["last_used"] = before.get("last_used", task.get("last_used", ""))
                if template_records is not None and task not in template_records:
                    template_records.append(task)
                save_templates(template_records if template_records is not None else load_templates())
            except Exception as exc:
                show_message(page, "Template edit failed", str(exc))
                return
            log_activity("Edit template", f"{task.get('name', 'Template')} updated.", {"before": before, "after": dict(task)})
            page.pop_dialog()
            save_and_render("Template updated.")

        page.pop_dialog()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    spacing=16,
                    controls=[
                        ft.Container(width=58, height=58, border_radius=16, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=32, color=icon_color)),
                        ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(f"Edit Template: {task.get('name', 'Template')}", size=24, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text("No work status here. Templates only store name, type, date, target, and note.", size=13, color=MUTED),
                            ],
                        ),
                    ],
                ),
                content=ft.Row(
                    width=900,
                    height=440,
                    spacing=22,
                    controls=[
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=20,
                            content=ft.Column(
                                spacing=14,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.ARTICLE_OUTLINED, color=MUTED), ft.Text("Template Details", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    name_field,
                                    ft.Column(spacing=8, controls=[ft.Text("Template type", size=13, weight=ft.FontWeight.W_800, color=TEXT), type_field]),
                                    date_field,
                                    target_field,
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=20,
                            content=ft.Column(
                                spacing=14,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, color=MUTED), ft.Text("Template Note", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    note_field,
                                ],
                            ),
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Save Template", icon=ft.Icons.SAVE_OUTLINED, on_click=save_template_edit, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def modified_text():
        try:
            path = Path(target)
            if path.exists():
                return datetime.fromtimestamp(path.stat().st_mtime).strftime("Last modified: %A, %B %d, %Y, %H:%M")
        except OSError:
            pass
        return f"Added: {task.get('date_added', '-')}"

    async def copy_target(_event):
        await page.clipboard.set(target)
        show_message(page, "Copied", "Path copied.")

    def copy_to_waiting(_event):
        if not target:
            show_message(page, "Copy failed", "No target path or URL to copy.")
            return

        def create_copy():
            try:
                create_snapshot("Before copy task to Waiting")
                copied = create_task_from_source(
                    task.get("name", "Untitled task"),
                    target,
                    file_type=task.get("type", "Other"),
                    note=task.get("note", ""),
                    status=STATUS_PENDING,
                )
            except Exception as exc:
                show_message(page, "Copy failed", str(exc), kind="danger")
                return
            all_tasks.append(copied)
            push_undo({"kind": "task_restore", "action": "Copy to Waiting", "task_id": copied.get("id"), "before": {}, "after": dict(copied)})
            log_activity("Copy to Waiting", f"{task.get('name', 'Untitled task')} copied to Waiting.", {"source_task_id": task.get("id"), "task_id": copied.get("id")})
            page.pop_dialog()
            save_and_render(f"Copied to Waiting as {copied.get('name', 'Untitled task')}.")
            show_message(page, "Copied to Waiting", copied.get("name", "Untitled task"), kind="success")

        run_with_duplicate_guard(task.get("name", "Untitled task"), target, task.get("type", "Other"), create_copy)

    def add_detail_item_to_board(_event):
        if not is_untracked_browser_item:
            return
        try:
            create_snapshot("Before add browser detail to board")
            task["id"] = task.get("id") or str(uuid.uuid4())
            task["status"] = task.get("status") or STATUS_PENDING
            set_task_calendar_date(task, task_calendar_date(task))
            all_tasks.append(task)
            push_undo({"kind": "task_restore", "action": "Add browser item", "task_id": task.get("id"), "before": {}, "after": dict(task)})
            log_activity("Add browser item", f"{task.get('name', 'Untitled task')} added to board from detail.", {"task_id": task.get("id")})
            page.pop_dialog()
            save_and_render("Added to board.")
        except Exception as exc:
            show_message(page, "Add failed", str(exc))

    def template_to_work_action(_event):
        if template_to_work:
            page.pop_dialog()
            template_to_work(_event)
        else:
            show_message(page, "Template", "Open the Template page to create work from this item.")

    def action_button(label, icon_name, on_click, primary=False, danger=False, disabled=False):
        bg = "#2563EB" if primary else "#FEF2F2" if danger else "#F8FAFC"
        fg = WHITE if primary else "#DC2626" if danger else TEXT
        side_color = "#2563EB" if primary else "#FECACA" if danger else BORDER
        hover = "#1D4ED8" if primary else "#FEE2E2" if danger else "#E2E8F0"
        return ft.Button(
            label,
            icon=icon_name,
            on_click=on_click,
            expand=True,
            disabled=disabled,
            height=48,
            style=ft.ButtonStyle(
                bgcolor=bg,
                color=fg,
                overlay_color=hover,
                side=ft.BorderSide(1, side_color),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

    meta_controls = [
        ft.Container(padding=pad_sym(horizontal=10, vertical=6), border_radius=9, bgcolor="#F1F5F9", content=ft.Text(f"{task.get('type', 'Other')} File", size=13, color=TEXT)),
        ft.Text("|", size=14, color=MUTED_2),
        ft.Container(padding=pad_sym(horizontal=10, vertical=6), border_radius=9, bgcolor="#F1F5F9", content=ft.Text(task.get("target_kind", "file").title(), size=13, color=TEXT)),
    ]
    if is_template:
        meta_controls.extend(
            [
                ft.Text("|", size=14, color=MUTED_2),
                ft.Container(padding=pad_sym(horizontal=10, vertical=6), border_radius=9, bgcolor="#F1F5F9", content=ft.Text("System Template", size=13, color=TEXT)),
            ]
        )
    else:
        meta_controls.extend(
            [
                ft.Text("|", size=14, color=MUTED_2),
                status_pill(task.get("status", STATUS_PENDING)),
                dropdown(170, current_status_label, status_options, lambda e: set_status(status_lookup.get(e.control.value, STATUS_PENDING))),
            ]
        )

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=24,
                controls=[
                    ft.Container(width=78, height=78, border_radius=22, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=42, color=icon_color)),
                    ft.Column(
                        spacing=8,
                        expand=True,
                        controls=[
                            ft.Text(task.get("name", "Untitled task"), size=22, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=meta_controls,
                            ),
                        ],
                    ),
                ],
            ),
            content=ft.Column(
                width=1020,
                height=540,
                spacing=16,
                controls=[
                    ft.Row(
                        spacing=20,
                        expand=True,
                        controls=[
                            ft.Container(
                                expand=True,
                                border=border_all(1, BORDER),
                                border_radius=18,
                                padding=18,
                                content=ft.Column(
                                    spacing=12,
                                    controls=[
                                        ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.ROUTE_OUTLINED, color=MUTED), ft.Text("Target Location", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                        ft.Container(
                                            height=128,
                                            border=border_all(1, BORDER),
                                            border_radius=14,
                                            bgcolor="#F8FAFC",
                                            padding=16,
                                            content=ft.Text(target or "No target", size=14, color=TEXT, selectable=True),
                                        ),
                                        ft.Button("Copy Path", icon=ft.Icons.CONTENT_COPY, on_click=copy_target, width=170, height=42),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                border=border_all(1, BORDER),
                                border_radius=18,
                                padding=18,
                                content=ft.Column(
                                    spacing=12,
                                    controls=[
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            controls=[
                                                ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, color=MUTED), ft.Text("Item Notes", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                                ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip="Edit details", on_click=edit_template if is_template else edit_task, disabled=is_untracked_browser_item),
                                            ],
                                        ),
                                        ft.Container(
                                            expand=True,
                                            border=border_all(1, BORDER),
                                            border_radius=14,
                                            bgcolor="#F8FAFC",
                                            padding=16,
                                            content=ft.Text(note if note != "No note" else "No note currently available for this item.", size=14, color=TEXT, selectable=True),
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=14,
                        controls=(
                            [
                                action_button("To Work", ft.Icons.ADD_TASK_OUTLINED, template_to_work_action, primary=True),
                                action_button("Edit Template", ft.Icons.EDIT_OUTLINED, edit_template),
                                action_button("Open Template", ft.Icons.OPEN_IN_NEW, lambda _e: open_target(task)),
                                action_button("Copy Path", ft.Icons.CONTENT_COPY, copy_target),
                                action_button("Show in Folder", ft.Icons.FOLDER_OPEN_OUTLINED, lambda _e: open_folder(task)),
                            ]
                            if is_template
                            else [
                                action_button("Open", ft.Icons.OPEN_IN_NEW, lambda _e: open_target(task), primary=not is_untracked_browser_item),
                                action_button("Add to Board", ft.Icons.ADD_TASK_OUTLINED, add_detail_item_to_board, primary=True) if is_untracked_browser_item else action_button("Edit", ft.Icons.EDIT_OUTLINED, edit_task),
                                action_button("Date", ft.Icons.EVENT_OUTLINED, lambda _e: show_task_date_dialog(page, task, save_and_render, all_tasks), disabled=is_untracked_browser_item),
                                action_button("Copy", ft.Icons.CONTENT_COPY, copy_to_waiting, disabled=is_untracked_browser_item),
                                action_button("Show in Folder", ft.Icons.FOLDER_OPEN_OUTLINED, lambda _e: open_folder(task)),
                                action_button("Delete", ft.Icons.DELETE_OUTLINE, delete_task, danger=True, disabled=is_untracked_browser_item),
                            ]
                        ),
                    ),
                    ft.Container(alignment=ft.Alignment(1, 0), content=ft.Text(modified_text(), size=13, color=MUTED_2)),
                ],
            ),
            actions=[ft.TextButton("Close", on_click=lambda _e: (page.pop_dialog(), page.update()))],
            bgcolor=WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )
    page.update()


def main(page: ft.Page):
    from ui.startup import show_startup_loader

    startup_settings = load_settings()
    startup_manifest_url = str(startup_settings.get("update_manifest_url") or DEFAULT_UPDATE_CHANNEL_URL).strip()
    show_startup_loader(
        page,
        dashboard_main=dashboard_main,
        settings=startup_settings,
        app_name=APP_NAME,
        app_version=APP_VERSION,
        app_logo=APP_LOGO_PATH,
        app_root=app_folder(),
        manifest_url=startup_manifest_url,
    )


if __name__ == "__main__":
    ft.run(main)
