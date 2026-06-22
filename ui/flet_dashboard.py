import json
import os
import shutil
import subprocess
import sys
import uuid
import urllib.error
import urllib.request
import webbrowser
import calendar
import csv
import html
import time
import re
import tempfile
import base64
from datetime import date, datetime, timedelta
from pathlib import Path

import flet as ft

from core.app_paths import APP_SETTINGS_FILE, DATA_FILE, TEMPLATE_FILE, work_folder


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
APP_VERSION = "1.0.7.6 Calendar Dialog Fit"
MANUAL_VERSION = "2026-06-18-user-guide"
DEFAULT_UPDATE_CHANNEL_URL = "https://api.github.com/repos/spirmx/SACHECK/contents/sacheck_update.json?ref=main"
UPDATE_MANIFEST_FILE = "sacheck_update.json"
DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES = 1
VERSION_HISTORY = [
    {
        "version": "1.0.7.6 Calendar Dialog Fit",
        "date": "2026-06-22",
        "latest": True,
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
    "Developer / Creator: HOYTURBRO": "ผู้พัฒนา / ผู้สร้าง: HOYTURBRO",
    "Publisher: HOYTURBRO": "ผู้เผยแพร่: HOYTURBRO",
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


def load_json(path, fallback):
    if not path.exists():
        return fallback
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, type(fallback)) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


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


def is_forced_platform_update(candidate, current=APP_VERSION):
    target = parse_version(candidate)
    installed = parse_version(current)
    if target[:2] > installed[:2]:
        return True
    if target[:2] == installed[:2] and target[2] - installed[2] >= 2:
        return True
    if target[:3] == installed[:3] and target[3] - installed[3] >= 3:
        return True
    return False


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
    return {
        "version": version,
        "installer_url": str(raw.get("installer_url") or raw.get("download_url") or raw.get("url") or "").strip(),
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


def load_tasks():
    return load_json(DATA_FILE, [])


def save_tasks(tasks):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=2)


def load_templates():
    return load_json(TEMPLATE_FILE, [])


def load_settings():
    return load_json(APP_SETTINGS_FILE, {})


def save_settings(settings):
    APP_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with APP_SETTINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)


def infer_type(target):
    text = str(target).lower()
    if text.startswith(("http://", "https://")):
        if "docs.google.com/spreadsheets" in text:
            return "Google Sheet"
        if "miro.com" in text:
            return "Miro"
        return "Web"
    suffix = Path(target).suffix.lower()
    if suffix in {".doc", ".docx", ".odt", ".rtf"}:
        return "Word"
    if suffix in {".xls", ".xlsx", ".csv"}:
        return "Excel"
    if suffix in {".url", ".html", ".htm"}:
        return "Web"
    if Path(target).is_dir():
        return "Project"
    return "Other"


def make_task(name, target, target_kind=None, task_type=None, note="", status=STATUS_PENDING):
    target_text = str(target).strip()
    kind = target_kind or ("url" if target_text.startswith(("http://", "https://")) else ("folder" if Path(target_text).is_dir() else "file"))
    resolved_type = task_type or infer_type(target_text)
    return {
        "id": str(uuid.uuid4()),
        "name": name.strip() or Path(target_text).stem or "Untitled task",
        "type": resolved_type,
        "detected_type": resolved_type,
        "link": target_text,
        "target_kind": kind,
        "shortcut_path": None,
        "note": note.strip(),
        "status": status,
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "done_date": datetime.now().date().isoformat() if status == STATUS_DONE else None,
        "source": "flet_quick_add",
        "file_key": target_text.casefold(),
        "project_stack": "",
        "category_mismatch": False,
    }


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


def soft_shadow():
    return ft.BoxShadow(spread_radius=0, blur_radius=10, color="#16000000", offset=ft.Offset(0, 3))


NAV_BG = "#08111F"
NAV_ACTIVE = "#1D4ED8"


def nav_button(icon, active=False):
    return ft.Container(
        width=48,
        height=48,
        border_radius=12,
        bgcolor=NAV_ACTIVE if active else "#0F1B2D",
        border=border_all(1, "#93C5FD" if active else "#263449"),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#24000000", offset=ft.Offset(0, 3)) if active else None,
        alignment=CENTER,
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=4, height=26, border_radius=999, bgcolor="#FFFFFF" if active else "#0F1B2D"),
                ft.Container(width=42, alignment=CENTER, content=ft.Icon(icon, size=22, color=WHITE if active else "#C3CEE0")),
            ],
        ),
    )


def stat_card(title, value):
    return ft.Container(
        expand=True,
        height=108,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=14,
        padding=pad_sym(horizontal=24, vertical=20),
        shadow=soft_shadow(),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Text(title, size=12, weight=ft.FontWeight.W_900, color=MUTED),
                ft.Text(str(value), size=34, weight=ft.FontWeight.W_900, color=TEXT),
            ],
        ),
    )


def dropdown(width, value, options, on_select=None, menu_height=None):
    return ft.Dropdown(
        width=width,
        height=48,
        value=value,
        options=[ft.dropdown.Option(option) for option in options],
        border_radius=14,
        border_color=BORDER,
        focused_border_color="#CBD5E1",
        bgcolor="#F8FAFC",
        text_size=14,
        color=TEXT,
        content_padding=pad_sym(horizontal=12),
        menu_height=menu_height,
        on_select=on_select,
    )


def open_target(task):
    target = task.get("link") or task.get("shortcut_path") or ""
    if not target:
        return False
    if target.startswith(("http://", "https://")):
        webbrowser.open(target)
        return True
    if Path(target).exists():
        os.startfile(target)
        return True
    return False


def open_folder(task):
    for target in [task.get("link"), task.get("shortcut_path")]:
        if not target:
            continue
        path = Path(target)
        if path.is_dir():
            os.startfile(str(path))
            return True
        if path.exists():
            os.startfile(str(path.parent))
            return True
    return False


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


def status_style_values(status, fallback_type="Other"):
    if status == STATUS_PENDING:
        return WAITING_BG, "#BFDBFE", WAITING_TEXT
    if status == STATUS_PROGRESS:
        return DOING_BG, "#FED7AA", DOING_TEXT
    if status == STATUS_DONE:
        return DONE_BG, "#BBF7D0", DONE_TEXT
    return type_style(fallback_type)


def file_meta(path):
    try:
        stat = path.stat()
        size = stat.st_size
        if size >= 1024 * 1024:
            size_text = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_text = f"{size / 1024:.1f} KB"
        else:
            size_text = f"{size} B"
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        return f"{modified}  |  {size_text}"
    except OSError:
        return "Unavailable"


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


def list_work_items(path):
    items = []
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                entry_path = Path(entry.path)
                items.append((entry.is_dir(), entry.name.casefold(), entry_path))
    except OSError:
        return []
    items.sort(key=lambda item: (not item[0], item[1]))
    return [item[2] for item in items[:250]]


from core.flet_constants import (  # noqa: E402
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
    create_task_from_source,
    create_task_from_tool,
    create_task_from_template,
    create_template_from_source,
    delete_item_target,
    ensure_status_folders,
    file_meta,
    file_type_config,
    infer_type,
    list_work_items,
    list_work_items_page,
    list_snapshots,
    load_activity_log,
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
    save_tasks,
    save_templates,
    sync_from_work,
    template_folder,
    status_folder,
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
    border_all,
    dropdown,
    nav_button,
    pad_only,
    pad_sym,
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
    for module in (theme_constants, widget_theme):
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


def main(page: ft.Page):
    global UI_LANGUAGE
    install_pointer_feedback()
    all_tasks = load_tasks()
    settings = load_settings()
    UI_LANGUAGE = str(settings.get("language") or "en").lower()
    apply_app_theme(settings)
    root_work = work_folder()
    current_browser_path = {"path": root_work}
    state = {
        "screen": SCREEN_BOARD,
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
        "settings_search": "",
        "last_sync_check": datetime.now().timestamp(),
        "syncing": False,
        "closed": False,
        "online_status": "checking",
        "update_manifest": None,
        "update_available": False,
        "update_checking": False,
        "update_installing": False,
        "last_update_check": 0,
        "update_prompted_versions": set(),
        "health_filter": "All",
    }

    page.title = APP_NAME
    try:
        page.window.icon = APP_ICON_PATH
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

    header_title = ft.Text("Project Overview", size=34, weight=ft.FontWeight.W_800, color=TEXT)
    header_subtitle = ft.Text(f"{APP_NAME} / Work Board", size=13, weight=ft.FontWeight.W_700, color=MUTED)
    progress_badge = ft.Text("", size=13, weight=ft.FontWeight.W_700, color=PRIMARY)
    main_body = ft.Column(spacing=22, expand=True)
    search_field = ft.TextField(
        hint_text="Search name, note, path, type, status, date...",
        prefix_icon=ft.Icons.SEARCH,
        height=48,
        expand=True,
        border_radius=14,
        border_color=BORDER,
        focused_border_color="#CBD5E1",
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

    def render_board():
        header_title.value = "Project Overview"
        header_subtitle.value = f"{APP_NAME} / Work Board"
        visible = filtered_tasks()
        waiting = [task for task in visible if task.get("status") == STATUS_PENDING]
        doing = [task for task in visible if task.get("status") == STATUS_PROGRESS]
        done = [task for task in visible if task.get("status") == STATUS_DONE]
        total_all = len(all_tasks)
        done_all = sum(1 for task in all_tasks if task.get("status") == STATUS_DONE)
        progress_badge.value = f"{int((done_all / total_all) * 100) if total_all else 0}% Complete"
        stats = ft.Row(
            spacing=18,
            controls=[
                stat_card("TOTAL", total_all),
                stat_card("WAITING", sum(1 for task in all_tasks if task.get("status") == STATUS_PENDING)),
                stat_card("DOING", sum(1 for task in all_tasks if task.get("status") == STATUS_PROGRESS)),
                stat_card("COMPLETED", done_all),
            ],
        )
        filters = ft.Container(
            height=58,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=14,
            padding=pad_sym(horizontal=14, vertical=7),
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#0A000000", offset=ft.Offset(0, 2)),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    search_field,
                    dropdown(170, state["view"], ["All work", "Waiting", "Doing", "Completed"], lambda e: (state.update({"view": e.control.value, "group_limits": {}}), render_current())),
                    dropdown(170, state["type"], ["All types", *file_types()], lambda e: (state.update({"type": e.control.value, "group_limits": {}}), render_current())),
                    dropdown(160, state["sort"], ["Newest", "Oldest", "Name"], lambda e: (state.update({"sort": e.control.value, "group_limits": {}}), render_current())),
                    ft.Container(padding=pad_sym(horizontal=11, vertical=8), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(f"{len(visible)} shown", size=12, weight=ft.FontWeight.W_800, color=MUTED)),
                    ft.Button("Reset", icon=ft.Icons.RESTART_ALT, on_click=lambda _e: reset_filters(), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                ],
            ),
        )
        board = ft.Row(
            spacing=18,
            expand=True,
            controls=[
                kanban_column(page, "Waiting List", waiting, *status_theme(STATUS_PENDING), save_and_render, all_tasks, grouped=True, group_limits=state["group_limits"], on_more=render_current),
                kanban_column(page, "Active Work", doing, *status_theme(STATUS_PROGRESS), save_and_render, all_tasks, grouped=True, group_limits=state["group_limits"], on_more=render_current),
                kanban_column(page, "Complete", done, *status_theme(STATUS_DONE), save_and_render, all_tasks, grouped=True, group_limits=state["group_limits"], on_more=render_current),
            ],
        )
        smart_help = ft.Container(
            height=36,
            bgcolor="#F8FBFF",
            border=border_all(1, "#DBEAFE"),
            border_radius=14,
            padding=pad_sym(horizontal=14, vertical=6),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.TIPS_AND_UPDATES_OUTLINED, size=16, color=PRIMARY),
                    ft.Text("Smart Search:", size=12, weight=ft.FontWeight.W_900, color=TEXT),
                    ft.Text("try `doing word`, `success today`, `zombie`, `>7`, `miro waiting`", size=12, color=MUTED),
                ],
            ),
        )
        main_body.spacing = 18
        main_body.controls = [stats, filters, *([smart_help] if settings.get("smart_search_enabled", True) else []), board]
        page.update()

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

        def copy_path(_e):
            page.clipboard.set(str(path))
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

    def render_browser():
        header_title.value = "Work Browser & File Organizer"
        header_subtitle.value = f"{APP_NAME} / Work"
        current = current_browser_path["path"]
        browser_limit = max(80, min(400, int(state.get("browser_limit", 160) or 160)))
        all_items, total_raw = list_work_items_page(current, 0, browser_limit)
        query = state.get("browser_search", "").strip().casefold()
        all_items = [path for path in all_items if not query or query in path.name.casefold() or query in path.suffix.casefold() or query in str(path).casefold()]
        sort_key = state.get("browser_sort", "Name")

        def item_sort_value(path):
            try:
                stat = path.stat()
            except OSError:
                stat = None
            if sort_key == "Modified":
                return stat.st_mtime if stat else 0
            if sort_key == "Size":
                return stat.st_size if stat else 0
            if sort_key == "Type":
                return ("Folder" if path.is_dir() else path.suffix.lower(), path.name.casefold())
            return path.name.casefold()

        all_items.sort(key=item_sort_value, reverse=bool(state.get("browser_desc")))
        task_by_key = {}
        for task in all_tasks:
            for target in [task.get("shortcut_path"), task.get("link")]:
                if not target or str(target).startswith(("http://", "https://")):
                    continue
                task_by_key[normalized_file_key(str(target))] = task

        visible_records = []
        selected_key = state.get("browser_selected", "")

        def folder_label(path):
            if path.name == "Template":
                return "TEMPLATE"
            status_by_folder = {"Waiting": "WAITING", "Doing": "DOING", "Success": "SUCCESS"}
            return status_by_folder.get(path.name, "FOLDER")

        def browser_folder_style(path, record=None):
            name = path.name
            parent_name = path.parent.name
            status_colors = {
                "Waiting": (WAITING_BG, "#BFDBFE", WAITING_TEXT),
                "Doing": (DOING_BG, "#FED7AA", DOING_TEXT),
                "Success": (DONE_BG, "#BBF7D0", DONE_TEXT),
                "Template": ("#EEF2FF", "#A5B4FC", "#4F46E5"),
            }
            if name in status_colors:
                return status_colors[name]
            if parent_name in file_types() and name.casefold() in {"template", "waiting", "doing", "success"}:
                return status_colors.get(name, type_style(parent_name))
            if name in file_types():
                return type_style(name)
            if record and record.get("type") and record.get("type") not in {"Project", "Other"}:
                return type_style(record.get("type"))
            semantic_colors = {
                "Project": ("#F5F3FF", "#C4B5FD", "#7C3AED"),
                "Canva": ("#F0FDFA", "#5EEAD4", "#0F766E"),
                "Diagram": ("#FAF5FF", "#D8B4FE", "#9333EA"),
                "Archive": ("#F8FAFC", "#CBD5E1", "#475569"),
                "Image": ("#FDF2F8", "#F9A8D4", "#DB2777"),
                "Video": ("#FFF1F2", "#FDA4AF", "#E11D48"),
                "Code": ("#ECFEFF", "#67E8F9", "#0891B2"),
                "Data": ("#F0FDF4", "#86EFAC", "#16A34A"),
            }
            return semantic_colors.get(name, ("#F8FAFC", "#CBD5E1", "#64748B"))

        def record_for_path(path):
            key = normalized_file_key(str(path))
            task = task_by_key.get(key)
            
            # Enhanced type/status inference for browser folders
            if path.is_dir():
                # Folders directly under Work root are Type folders
                if path.parent.resolve() == root_work.resolve():
                    path_type = path.name
                # Folders inside Type folders like "Waiting", "Doing", "Success"
                elif path.name in {"Waiting", "Doing", "Success", "Template"}:
                    path_type = path.parent.name
                else:
                    path_type = "Project"
            else:
                path_type = infer_type(path)

            if task:
                return {"kind": "task", "task": task, "path": path, "type": task.get("type", path_type), "status": task.get("status", STATUS_PENDING), "key": task.get("id") or key}
            
            # Untracked folders that represent statuses should use status colors
            status = "folder" if path.is_dir() else "untracked"
            if path.is_dir():
                if path.name == "Waiting":
                    status = STATUS_PENDING
                elif path.name == "Doing":
                    status = STATUS_PROGRESS
                elif path.name == "Success":
                    status = STATUS_DONE

            return {"kind": "folder" if path.is_dir() else "file", "task": None, "path": path, "type": path_type, "status": status, "key": key}

        def children_for(path, limit=60):
            children, _total = list_work_items_page(path, 0, limit)
            if query:
                children = [child for child in children if query in child.name.casefold() or query in str(child).casefold()]
            children.sort(key=item_sort_value, reverse=bool(state.get("browser_desc")))
            return children

        total_items = len(all_items)
        progress_badge.value = "Synced (Realtime)" if settings.get("realtime_sync_enabled", True) else "Manual sync"
        selected_record = None
        preview_slot = {"control": None}

        def load_more(_event):
            state["browser_limit"] = min(total_raw, state.get("browser_limit", 160) + 160)
            render_current()

        def set_selected(record):
            state["browser_selected"] = record["key"]
            if preview_slot.get("control") is not None:
                preview_slot["control"].content = preview_panel(record)
                page.update()
            else:
                render_current()

        def move_record(record, status_value):
            task = record.get("task")
            if not task:
                add_or_update_from_path(record["path"])
                task = next((item for item in all_tasks if normalized_file_key(item.get("link", "")) == normalized_file_key(str(record["path"]))), None)
                if not task:
                    return
            before = dict(task)
            create_snapshot("Before browser status move")
            try:
                rename_task_target(task, task.get("name", "Untitled task"), task.get("link", ""), new_file_type=task.get("type", record.get("type", "Other")), new_status=status_value)
            except Exception as exc:
                show_message(page, "Move failed", str(exc))
                return
            remember_task_action("Browser status move", task, before)
            save_tasks(all_tasks)
            show_message(page, APP_NAME, f"Moved to {STATUS_LABELS.get(status_value)}.")
            render_current()

        def status_badge(record):
            status = record.get("status")
            if status == STATUS_PENDING:
                label, color, bg, badge_border = "WAITING", WAITING_TEXT, WAITING_BG, "#BFDBFE"
            elif status == STATUS_PROGRESS:
                label, color, bg, badge_border = "DOING", DOING_TEXT, DOING_BG, "#FED7AA"
            elif status == STATUS_DONE:
                label, color, bg, badge_border = "SUCCESS", DONE_TEXT, DONE_BG, "#BBF7D0"
            elif record.get("kind") == "folder":
                label = folder_label(record["path"])
                bg, badge_border, color = browser_folder_style(record["path"], record)
            else:
                label, color, bg, badge_border = "FILE", MUTED, "#F1F5F9", BORDER
            if record.get("kind") == "folder" and not record.get("task"):
                return ft.Container(
                    height=28,
                    padding=pad_sym(horizontal=10),
                    border_radius=999,
                    bgcolor=bg,
                    border=border_all(1, badge_border),
                    alignment=CENTER,
                    content=ft.Text(label, size=10, weight=ft.FontWeight.W_900, color=color),
                )
            return ft.PopupMenuButton(
                content=ft.Container(
                    height=28,
                    padding=pad_sym(horizontal=10),
                    border_radius=999,
                    bgcolor=bg,
                    border=border_all(1, color),
                    alignment=CENTER,
                    content=ft.Row(spacing=5, controls=[ft.Text(label, size=10, weight=ft.FontWeight.W_900, color=color), ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=13, color=color)]),
                ),
                items=[
                    ft.PopupMenuItem(content="Move to Waiting", icon=ft.Icons.RADIO_BUTTON_UNCHECKED, on_click=lambda _e, r=record: move_record(r, STATUS_PENDING)),
                    ft.PopupMenuItem(content="Move to Doing", icon=ft.Icons.PLAY_CIRCLE_OUTLINE, on_click=lambda _e, r=record: move_record(r, STATUS_PROGRESS)),
                    ft.PopupMenuItem(content="Move to Success", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda _e, r=record: move_record(r, STATUS_DONE)),
                ],
            )

        def record_row(record, compact=False):
            if not any(item["key"] == record["key"] for item in visible_records):
                visible_records.append(record)
            path = record["path"]
            task = record.get("task")
            icon, icon_color = task_icon(record["type"])
            is_selected = state.get("browser_selected") == record["key"]
            location = path.parent.name
            row_bg, row_border, row_accent = status_style_values(record.get("status"), record.get("type", "Other"))
            type_bg, _type_border, _type_accent = type_style(record.get("type", "Other"))
            if record.get("kind") == "folder" and not task:
                row_bg, row_border, row_accent = browser_folder_style(path, record)
                type_bg = "#FFFFFF"
                icon = ft.Icons.FOLDER_OUTLINED
                icon_color = row_accent

            def open_record(_event):
                if path.is_dir():
                    go_to_browser_path(path)
                else:
                    os.startfile(str(path))

            def detail_record(_event):
                detail_task = task or make_task(path.stem if path.is_file() else path.name, str(path), target_kind="folder" if path.is_dir() else "file", task_type=record["type"], note=file_meta(path) if path.is_file() else "Folder")
                show_task_detail(page, detail_task, save_and_render, all_tasks)

            def copy_record(_event):
                page.clipboard.set(str(path))
                show_message(page, "Copied", "Path copied.")

            return ft.Container(
                height=52 if compact else 58,
                bgcolor="#EFF6FF" if is_selected else row_bg if compact else WHITE,
                border=border_all(1.5 if is_selected else 1, PRIMARY if is_selected else row_border if compact else BORDER),
                border_radius=14,
                padding=pad_only(left=10, right=4),
                on_click=lambda _e, r=record: set_selected(r),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=5, height=34, border_radius=999, bgcolor=row_accent),
                        ft.Container(width=34, height=34, border_radius=10, bgcolor=type_bg, border=border_all(1, row_border), alignment=CENTER, content=ft.Icon(icon, size=17, color=icon_color)),
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(task.get("name", path.stem if path.is_file() else path.name) if task else path.name, size=14, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Row(
                                    spacing=6,
                                    controls=[
                                        ft.Text(f"Location: /{location}", size=11, color=MUTED_2, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Container(padding=pad_sym(horizontal=7, vertical=2), border_radius=999, bgcolor=type_bg, content=ft.Text(record.get("type", "Other"), size=10, weight=ft.FontWeight.W_800, color=icon_color)),
                                    ],
                                ),
                            ],
                        ),
                        status_badge(record),
                        row_action_button("Open", ft.Icons.OPEN_IN_NEW, open_record, width=96),
                        row_action_button("Detail", ft.Icons.INFO_OUTLINE, detail_record, width=100),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            icon_size=18,
                            icon_color=MUTED_2,
                            items=[
                                ft.PopupMenuItem(content="Add to board" if not task else "Already on board", icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda _e, p=path: add_or_update_from_path(p)),
                                ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_record),
                                ft.PopupMenuItem(content="Show in folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e, p=path: os.startfile(str(p if p.is_dir() else p.parent))),
                            ],
                        ),
                    ],
                ),
            )

        def folder_card(path, level=0):
            record = record_for_path(path)
            visible_records.append(record)
            child_paths = children_for(path, 28 if level == 0 else 0) if path.is_dir() else []
            child_controls = []
            if path.is_dir():
                for child in child_paths:
                    child_controls.append(record_row(record_for_path(child), compact=True))
                if not child_controls:
                    child_controls.append(ft.Container(height=44, alignment=CENTER, content=ft.Text("Empty folder", size=12, color=MUTED_2)))
            icon, icon_color = task_icon(record["type"])
            title_text = path.name
            subtitle = f"{len(child_paths)} items" if path.is_dir() else file_meta(path)
            if record.get("task"):
                subtitle = f"Tracked | {STATUS_LABELS.get(record.get('status'), 'Waiting')} | {subtitle}"
            if not path.is_dir():
                return record_row(record)
            group_bg, group_border, group_accent = browser_folder_style(path, record)
            icon_bg = "#FFFFFF"
            icon = ft.Icons.FOLDER_OUTLINED
            icon_color = group_accent
            return ft.Container(
                bgcolor=group_bg,
                border=border_all(1, group_border),
                border_radius=16,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#0A000000", offset=ft.Offset(0, 4)) if level == 0 else None,
                content=ft.ExpansionTile(
                    expanded=False,
                    maintain_state=True,
                    tile_padding=pad_only(left=12, right=8),
                    controls_padding=pad_only(left=10, right=10, bottom=10),
                    title=ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(width=5, height=34, border_radius=999, bgcolor=group_accent),
                            ft.Container(width=34, height=34, border_radius=10, bgcolor=icon_bg, border=border_all(1, group_border), alignment=CENTER, content=ft.Icon(icon, size=17, color=icon_color)),
                            ft.Column(spacing=1, expand=True, controls=[ft.Text(title_text, size=14, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(subtitle, size=11, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)]),
                            status_badge(record),
                            row_action_button("Open", ft.Icons.FOLDER_OPEN_OUTLINED, lambda _e, p=path: go_to_browser_path(p), width=96),
                            row_action_button("Detail", ft.Icons.INFO_OUTLINE, lambda _e, r=record: set_selected(r), width=98),
                        ],
                    ),
                    controls=[ft.Column(spacing=8, controls=child_controls)],
                ),
            )

        organizer_controls = [folder_card(path) for path in all_items]
        if total_raw > len(all_items):
            organizer_controls.append(
                ft.Container(
                    height=52,
                    alignment=CENTER,
                    content=ft.Button(
                        f"Load more ({total_raw - len(all_items)} left)",
                        icon=ft.Icons.EXPAND_MORE,
                        on_click=load_more,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                    ),
                )
            )
        selected_record = next((record for record in visible_records if record["key"] == selected_key or str(record["path"]) == selected_key), None)
        if not selected_record and visible_records:
            selected_record = visible_records[0]
        state["browser_selected"] = selected_record["key"] if selected_record else ""
        toolbar = ft.Container(
            height=118,
            bgcolor="#F8FBFF",
            border=border_all(1, "#BFDBFE"),
            border_radius=18,
            padding=pad_sym(horizontal=18, vertical=10),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=MUTED, on_click=lambda _e: go_to_browser_path(current.parent if current != root_work else root_work)),
                            ft.Row(spacing=4, controls=breadcrumb_controls(), expand=True),
                            ft.Button("Open in Explorer", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e: os.startfile(str(current)) if current.exists() else show_message(page, "Folder not found", "This folder may have been moved or deleted."), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                            ft.Button("Refresh", icon=ft.Icons.REFRESH, on_click=lambda _e: render_current(), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.TextField(
                                hint_text="Search this folder...",
                                prefix_icon=ft.Icons.SEARCH,
                                value=state.get("browser_search", ""),
                                height=44,
                                expand=True,
                                border_radius=14,
                                border_color=BORDER,
                                bgcolor="#F8FAFC",
                                on_change=lambda e: (state.update({"browser_search": e.control.value or "", "browser_limit": 160, "browser_selected": ""}), render_current()),
                            ),
                            dropdown(160, state.get("browser_sort", "Name"), ["Name", "Modified", "Type", "Size"], lambda e: (state.update({"browser_sort": e.control.value, "browser_selected": ""}), render_current())),
                            ft.IconButton(icon=ft.Icons.SOUTH if state.get("browser_desc") else ft.Icons.NORTH, tooltip="Toggle sort direction", on_click=lambda _e: (state.update({"browser_desc": not state.get("browser_desc"), "browser_selected": ""}), render_current())),
                            ft.PopupMenuButton(
                                content=ft.Container(height=42, padding=pad_sym(horizontal=14), border_radius=12, bgcolor="#F8FAFC", alignment=CENTER, content=ft.Row(spacing=7, controls=[ft.Icon(ft.Icons.TRAVEL_EXPLORE, size=17, color=MUTED), ft.Text("Jump", size=13, weight=ft.FontWeight.W_800, color=TEXT)])),
                                items=[
                                    ft.PopupMenuItem(content="Work root", icon=ft.Icons.HOME_OUTLINED, on_click=lambda _e: go_to_browser_path(root_work)),
                                    *[ft.PopupMenuItem(content=file_type, icon=ft.Icons.FOLDER_OUTLINED, on_click=lambda _e, p=root_work / file_type: go_to_browser_path(p)) for file_type in file_types()[:18]],
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        )
        listing = ft.Container(
            expand=True,
            bgcolor="#F8FBFF",
            border=border_all(1, "#DBEAFE"),
            border_radius=22,
            padding=18,
            content=ft.ListView(
                expand=True,
                spacing=10,
                controls=organizer_controls if organizer_controls else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No files found", color=MUTED_2, size=15))],
            ),
        )

        def preview_panel(record):
            if not record:
                return ft.Container(width=380, bgcolor=WHITE, border=border_all(1, BORDER), border_radius=22, padding=22, alignment=CENTER, content=ft.Text("Select a file to preview", color=MUTED_2))
            path = record["path"]
            task = record.get("task")
            is_dir = path.is_dir()
            item_type = record.get("type") or ("Project" if is_dir else infer_type(path))
            icon, icon_color = task_icon(item_type)
            preview_bg, preview_border, preview_accent = status_style_values(record.get("status"), item_type)
            type_bg, _type_border, _type_accent = type_style(item_type)
            board_task = task
            try:
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                size = "Folder" if is_dir else file_meta(path).split("  |  ")[-1]
            except OSError:
                modified = "-"
                size = "-"

            sub_items = []
            sub_total = 0
            sub_raw_total = 0
            sub_key = normalized_file_key(str(path))
            sub_query = str(state.setdefault("browser_sub_search", {}).get(sub_key, "") or "").strip().casefold()
            if is_dir:
                try:
                    all_sub_items = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
                    sub_raw_total = len(all_sub_items)
                    if sub_query:
                        all_sub_items = [item for item in all_sub_items if sub_query in item.name.casefold() or sub_query in str(item).casefold()]
                    sub_total = len(all_sub_items)
                    sub_items = all_sub_items[:80]
                except OSError:
                    sub_items = []
                    sub_total = 0
                    sub_raw_total = 0

            def open_selected(_event):
                if not path.exists():
                    show_message(page, "Missing item", f"This file or folder was moved/deleted outside {APP_NAME}.")
                    state["browser_selected"] = ""
                    render_current()
                    return
                if is_dir:
                    go_to_browser_path(path)
                else:
                    os.startfile(str(path))

            def detail_selected(_event):
                if not path.exists():
                    show_message(page, "Missing item", f"This file or folder was moved/deleted outside {APP_NAME}.")
                    state["browser_selected"] = ""
                    render_current()
                    return
                detail_task = board_task or make_task(path.stem if path.is_file() else path.name, str(path), target_kind="folder" if is_dir else "file", task_type=item_type, note=file_meta(path) if path.is_file() else "Folder")
                show_task_detail(page, detail_task, save_and_render, all_tasks)

            def copy_selected_path(_event):
                page.clipboard.set(str(path))
                show_message(page, "Copied", "Path copied.")

            def rename_selected(_event):
                if board_task:
                    show_task_detail(page, board_task, save_and_render, all_tasks)
                else:
                    show_message(page, "Rename", "Add this item to the board first to rename safely.")

            status_text = STATUS_LABELS.get(board_task.get("status"), "Untracked") if board_task else "Untracked"
            board_text = board_task.get("name", path.name) if board_task else "Not on board"
            sub_list_height = min(220, max(88, 36 * min(len(sub_items), 5) + 22))

            def open_sub_item(item):
                def handler(_event):
                    if item.exists():
                        os.startfile(str(item))
                    else:
                        show_message(page, "Missing item", "This sub-item was moved or deleted.")
                return handler

            def sub_item_row(item):
                return ft.Container(
                    height=32,
                    border_radius=10,
                    padding=pad_sym(horizontal=8),
                    on_click=open_sub_item(item),
                    content=ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.FOLDER_OUTLINED if item.is_dir() else ft.Icons.INSERT_DRIVE_FILE_OUTLINED, size=14, color=MUTED),
                            ft.Text(item.name, size=12, color=MUTED, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Icon(ft.Icons.OPEN_IN_NEW, size=13, color=MUTED_2),
                        ],
                    ),
                )

            def update_sub_search(event):
                state.setdefault("browser_sub_search", {})[sub_key] = event.control.value or ""
                if preview_slot.get("control") is not None:
                    preview_slot["control"].content = preview_panel(record)
                    page.update()

            return ft.Container(
                width=380,
                bgcolor=preview_bg,
                border=border_all(1, preview_border),
                border_radius=22,
                padding=22,
                content=ft.Column(
                    spacing=16,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(width=6, height=58, border_radius=999, bgcolor=preview_accent),
                                ft.Container(width=58, height=58, border_radius=16, bgcolor=type_bg, border=border_all(1, preview_border), alignment=CENTER, content=ft.Icon(icon, size=30, color=icon_color)),
                                ft.Column(
                                    expand=True,
                                    spacing=4,
                                    controls=[
                                        ft.Text(board_task.get("name", path.name) if board_task else path.name, size=18, weight=ft.FontWeight.W_800, color=TEXT, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(item_type, size=12, color=MUTED),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(spacing=8, controls=[ft.Text("Current status:", size=12, weight=ft.FontWeight.W_800, color=MUTED), status_badge(record)]),
                        ft.Container(padding=pad_sym(horizontal=12, vertical=10), border_radius=14, bgcolor=WHITE, border=border_all(1, preview_border), content=ft.Text(str(path), size=12, color=MUTED, selectable=True)),
                        ft.Column(spacing=8, controls=[
                            ft.Text(f"Modified: {modified}", size=13, color=MUTED),
                            ft.Text(f"Size: {size}", size=13, color=MUTED),
                            ft.Text(f"Board task: {board_text}", size=13, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"Board status: {status_text}", size=13, color=MUTED),
                        ]),
                        ft.Container(
                            visible=bool(sub_items),
                            padding=pad_sym(horizontal=12, vertical=10),
                            border_radius=14,
                            bgcolor="#F8FAFC",
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Text("Sub-items", size=12, weight=ft.FontWeight.W_900, color=TEXT, expand=True),
                                            ft.Text(f"{sub_total}/{sub_raw_total} items" if sub_query else f"{sub_total} items", size=11, weight=ft.FontWeight.W_800, color=MUTED_2),
                                        ],
                                    ),
                                    ft.TextField(
                                        hint_text="Find sub-item...",
                                        prefix_icon=ft.Icons.SEARCH,
                                        value=state.setdefault("browser_sub_search", {}).get(sub_key, ""),
                                        height=38,
                                        border_radius=12,
                                        border_color=BORDER,
                                        bgcolor=WHITE,
                                        text_size=12,
                                        on_change=update_sub_search,
                                    ),
                                    ft.Container(
                                        height=sub_list_height,
                                        content=ft.ListView(
                                            spacing=4,
                                            controls=[sub_item_row(item) for item in sub_items] if sub_items else [ft.Container(height=36, alignment=CENTER, content=ft.Text("No sub-items match", size=11, color=MUTED_2))],
                                        ),
                                    ),
                                    ft.Text(f"Showing first {len(sub_items)}. Open folder for all items.", size=10, color=MUTED_2, visible=sub_total > len(sub_items)),
                                ],
                            ),
                        ),
                        ft.Row(spacing=10, controls=[row_action_button("Open", ft.Icons.OPEN_IN_NEW, open_selected, width=104, primary=True), row_action_button("Detail", ft.Icons.INFO_OUTLINE, detail_selected, width=108)]),
                        ft.Row(spacing=10, controls=[ft.Button("Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_selected_path, expand=True, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))), ft.Button("Rename", icon=ft.Icons.EDIT_OUTLINED, on_click=rename_selected, expand=True, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))]),
                    ],
                ),
            )

        preview_host = ft.Container(content=preview_panel(selected_record))
        preview_slot["control"] = preview_host
        main_body.controls = [toolbar, ft.Row(spacing=18, expand=True, controls=[listing, preview_host])]
        page.update()

    def auto_sync_from_work(force=False):
        if state.get("syncing"):
            return False
        now = datetime.now().timestamp()
        if not force and now - state.get("last_sync_check", 0) < 2:
            return False
        state["last_sync_check"] = now
        state["syncing"] = True
        try:
            synced_tasks, _synced_templates, changed = sync_from_work(force=force)
            if changed:
                all_tasks.clear()
                all_tasks.extend(synced_tasks)
            return changed
        finally:
            state["syncing"] = False

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
            if state["screen"] == SCREEN_BROWSER:
                render_browser()
            elif state["screen"] == SCREEN_CALENDAR:
                render_calendar()
            elif state["screen"] == SCREEN_TEMPLATES:
                render_templates()
            elif state["screen"] == SCREEN_SETTINGS:
                render_settings()
            elif state["screen"] == SCREEN_HEALTH:
                render_health()
            else:
                render_board()
        except Exception as exc:
            try:
                log_activity("System guard", str(exc), {"screen": state.get("screen")})
            except Exception:
                pass
            render_error_view(exc)

    def show_board(_e=None):
        reset_filters(render=False)
        state["screen"] = SCREEN_BOARD
        render_current()

    def show_browser(_e=None):
        state["screen"] = SCREEN_BROWSER
        render_current()

    def add_task_dialog(kind):
        title = {"file": "Add file", "link": "Add link", "project": "Add project"}[kind]
        name_field = ft.TextField(label="Task name", border_radius=12, border_color=BORDER)
        type_value = "Project" if kind == "project" else "Other"
        type_field = dropdown(520, type_value, file_types())
        target_field = ft.TextField(label="URL link" if kind == "link" else ("Project folder path" if kind == "project" else "Local file path"), value="https://" if kind == "link" else "", border_radius=12, border_color=BORDER)
        note_field = ft.TextField(label="Note / description", multiline=True, min_lines=3, max_lines=3, border_radius=12, border_color=BORDER)

        async def browse(_e):
            if kind == "project":
                path = await pick_directory("Choose project folder")
            else:
                picked = await file_picker.pick_files(dialog_title="Choose file", allow_multiple=False)
                path = picked[0].path if picked else ""
            if path:
                target_field.value = path
                if not name_field.value:
                    name_field.value = Path(path).name if kind == "project" else Path(path).stem
                if kind != "project":
                    type_field.value = infer_type(path)
                page.update()

        def paste_url(_e):
            try:
                value = page.clipboard.get()
            except Exception:
                value = ""
            if value:
                target_field.value = str(value)
                page.update()

        def save(_e):
            target = target_field.value.strip()
            if not target or target == "https://":
                return

            def create_work_item():
                try:
                    task = create_task_from_source(name_field.value, target, file_type=type_field.value, note=note_field.value, status=STATUS_PENDING)
                except Exception as exc:
                    show_message(page, "Add failed", str(exc))
                    return
                all_tasks.append(task)
                page.pop_dialog()
                save_and_render(f"{title} copied to Waiting as {task.get('name', 'Untitled task')}.")
                show_message(page, "Added to Waiting", task.get("name", "Untitled task"), kind="success")

            run_with_duplicate_guard(name_field.value, target, type_field.value, create_work_item)

        target_row = ft.Row(
            spacing=10,
            controls=[
                target_field,
                ft.Button(
                    "Paste URL" if kind == "link" else ("Browse folder" if kind == "project" else "Browse"),
                    on_click=paste_url if kind == "link" else browse,
                    width=130 if kind != "link" else 110,
                ),
            ],
        )
        target_field.expand = True
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(title, size=24, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Column(
                    width=540,
                    height=410,
                    spacing=12,
                    controls=[
                        name_field,
                        ft.Column(spacing=6, controls=[ft.Text("File type" if kind != "link" else "Link type", size=12, weight=ft.FontWeight.W_700, color=MUTED), type_field]),
                        target_row,
                        note_field,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Save link" if kind == "link" else "Save", on_click=save, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=10))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def render_templates():
        header_title.value = "Templates"
        header_subtitle.value = f"{APP_NAME} / Template Library"
        templates = load_templates()
        selected_template_type = {"value": "All template types"}
        template_query = {"value": ""}
        template_list = ft.ListView(expand=True, spacing=14)

        def template_row(template):
            icon, icon_color = task_icon(template.get("type", "Other"))
            target = item_target(template)
            pseudo_task = {"name": template.get("name", ""), "type": template.get("type", "Other"), "link": target, "shortcut_path": template.get("shortcut_path", ""), "target_kind": template.get("target_kind", "file"), "note": template.get("note", ""), "date_added": template.get("date_added", "")}

            def mark_used():
                template["usage_count"] = int(template.get("usage_count") or 0) + 1
                template["last_used"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_templates(templates)

            def use_template(_event):
                def create_from_template():
                    try:
                        ensure_status_folders()
                        task = create_task_from_template(template)
                        all_tasks.append(task)
                        save_tasks(all_tasks)
                        mark_used()
                        state.update({"screen": SCREEN_BOARD, "view": "Waiting", "type": task.get("type", "All types"), "sort": "Newest", "group_limits": {}})
                        search_field.value = ""
                        render_current()
                        target_path = task.get("shortcut_path") or task.get("link") or ""
                        show_message(page, "Template used", f"Copied to Waiting: {target_path}", kind="success")
                    except Exception as exc:
                        show_message(page, "Template failed", str(exc), kind="danger")

                run_with_duplicate_guard(template.get("name", "Untitled task"), item_target(template), template.get("type", "Other"), create_from_template)

            def open_template(_event):
                if open_target(pseudo_task):
                    mark_used()
                else:
                    show_message(page, "Cannot open", "Template target was not found.")

            def open_detail(_event):
                show_task_detail(page, template, lambda _m=None: (save_templates(templates), render_current()), [], is_template=True, template_to_work=use_template, template_records=templates)

            def copy_template_target(_event):
                page.clipboard.set(target)
                show_message(page, "Copied", "Template path copied.")

            def delete_template(_event):
                def confirm_delete(_confirm_event):
                    create_snapshot("Before template delete")
                    try:
                        delete_item_target(template)
                    except Exception as exc:
                        show_message(page, "Delete failed", str(exc))
                        return
                    template_id = template.get("id")
                    template_key = template.get("file_key") or normalized_file_key(template.get("shortcut_path") or template.get("link") or "")
                    templates[:] = [
                        item
                        for item in templates
                        if not (
                            (template_id and item.get("id") == template_id)
                            or (template_key and (item.get("file_key") or normalized_file_key(item.get("shortcut_path") or item.get("link") or "")) == template_key)
                        )
                    ]
                    save_templates(templates)
                    page.pop_dialog()
                    render_current()
                    show_message(page, "Template deleted", "Template file and record were removed.")

                page.show_dialog(
                    ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Delete template?", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                        content=ft.Container(
                            border=border_all(1, "#FECACA"),
                            border_radius=14,
                            bgcolor="#FEF2F2",
                            padding=pad_sym(horizontal=14, vertical=12),
                            content=ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#DC2626", size=22),
                                    ft.Text("This deletes the template record and the template file/shortcut inside Work.", size=14, color="#991B1B"),
                                ],
                            ),
                        ),
                        actions=[
                            ft.TextButton("No", on_click=lambda _e: (page.pop_dialog(), page.update())),
                            ft.Button("Yes, delete", on_click=confirm_delete, style=ft.ButtonStyle(color=WHITE, bgcolor="#DC2626", overlay_color="#B91C1C", shape=ft.RoundedRectangleBorder(radius=10))),
                        ],
                        bgcolor=WHITE,
                        shape=ft.RoundedRectangleBorder(radius=16),
                    )
                )
                page.update()

            meta = template.get("date_added", "")
            usage = int(template.get("usage_count") or 0)
            row_bg, row_border, row_accent = type_style(template.get("type", "Other"))

            return ft.Container(
                height=66,
                bgcolor=row_bg,
                border=border_all(1, row_border),
                border_radius=16,
                padding=pad_only(left=14, right=8),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=5, height=42, border_radius=999, bgcolor=row_accent),
                        ft.Container(width=42, height=42, border_radius=12, bgcolor=WHITE, border=border_all(1, row_border), alignment=CENTER, content=ft.Icon(icon, size=20, color=icon_color)),
                        ft.Column(
                            spacing=3,
                            expand=True,
                            controls=[
                                ft.Text(template.get("name", "Untitled template"), size=15, weight=ft.FontWeight.W_700, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"{template.get('type', 'Other')}  |  {meta}{'  |  used ' + str(usage) if usage else ''}", size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        row_action_button("To Work", ft.Icons.ADD_TASK_OUTLINED, use_template, width=112, primary=True),
                        row_action_button("Detail", ft.Icons.INFO_OUTLINE, open_detail, width=108),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            icon_size=18,
                            icon_color=MUTED_2,
                            items=[
                                ft.PopupMenuItem(content="Open template", icon=ft.Icons.OPEN_IN_NEW, on_click=open_template),
                                ft.PopupMenuItem(content="Folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e: open_folder(pseudo_task)),
                                ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_template_target),
                                ft.PopupMenuItem(content="Delete template", icon=ft.Icons.DELETE_OUTLINE, on_click=delete_template),
                            ],
                        ),
                    ],
                ),
            )

        def filtered_templates():
            query = template_query["value"].strip().casefold()
            selected = selected_template_type["value"]
            active_types = {task.get("type", "Other") for task in all_tasks if task.get("status") in {STATUS_PENDING, STATUS_PROGRESS}}

            def template_rank(template):
                if not settings.get("template_ranking_enabled", True):
                    return int(template.get("usage_count") or 0) * 20
                usage = int(template.get("usage_count") or 0)
                recent = 0
                last_used = template.get("last_used") or template.get("date_added") or ""
                try:
                    recent_days = (datetime.now() - datetime.strptime(str(last_used)[:16], "%Y-%m-%d %H:%M")).days
                    recent = max(0, 30 - recent_days)
                except ValueError:
                    recent = 0
                type_boost = 8 if template.get("type", "Other") in active_types else 0
                return usage * 20 + recent + type_boost

            items = []
            for template in templates:
                name = template.get("name", "")
                file_type = template.get("type", "Other")
                target = item_target(template)
                if selected != "All template types" and file_type != selected:
                    continue
                if query and query not in name.casefold() and query not in file_type.casefold() and query not in target.casefold():
                    continue
                items.append(template)
            items.sort(key=lambda item: (-template_rank(item), item.get("type", ""), item.get("name", "").casefold()))
            return items

        def grouped_visible_templates(items):
            grouped = {}
            for template in items:
                grouped.setdefault(template.get("type", "Other"), []).append(template)
            ordered = [file_type for file_type in file_types() if file_type in grouped]
            ordered.extend(sorted(file_type for file_type in grouped if file_type not in ordered))
            return grouped, ordered

        def template_group(file_type, rows, expanded=False):
            icon, icon_color = task_icon(file_type)
            folder = root_work / file_type / "Template"
            group_bg, group_border, group_accent = type_style(file_type)
            return ft.Container(
                bgcolor=group_bg,
                border=border_all(1, group_border),
                border_radius=18,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=14, color="#12000000", offset=ft.Offset(0, 4)),
                content=ft.ExpansionTile(
                    expanded=expanded,
                    maintain_state=True,
                    tile_padding=pad_only(left=16, right=14),
                    controls_padding=pad_only(left=16, right=16, bottom=16),
                    title=ft.Row(
                        spacing=14,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(width=6, height=44, border_radius=999, bgcolor=group_accent),
                            ft.Container(width=44, height=44, border_radius=13, bgcolor=WHITE, border=border_all(1, group_border), alignment=CENTER, content=ft.Icon(icon, size=22, color=icon_color)),
                            ft.Text(file_type, size=20, weight=ft.FontWeight.W_800, color=TEXT, expand=True),
                            ft.Text(f"Work\\{file_type}\\Template", size=14, color=MUTED),
                            ft.Container(padding=pad_sym(horizontal=11, vertical=6), border_radius=999, bgcolor=WHITE, border=border_all(1, group_border), content=ft.Text(str(len(rows)), size=13, weight=ft.FontWeight.W_800, color=group_accent)),
                            ft.IconButton(icon=ft.Icons.FOLDER_OPEN_OUTLINED, tooltip="Open template folder", icon_color=MUTED, on_click=lambda _e, p=folder: os.startfile(str(p)) if p.exists() else show_message(page, "Folder missing", str(p))),
                        ],
                    ),
                    controls=[ft.Column(spacing=10, controls=[template_row(template) for template in rows[:120]])],
                ),
            )

        def render_template_list():
            visible = filtered_templates()
            grouped, ordered_types = grouped_visible_templates(visible)
            progress_badge.value = f"{len(visible)} shown"
            if not visible:
                template_list.controls = [
                    ft.Container(
                        height=220,
                        border=border_all(1, BORDER),
                        border_radius=18,
                        alignment=CENTER,
                        content=ft.Text("No templates found", size=16, color=MUTED),
                    )
                ]
            else:
                template_list.controls = [template_group(file_type, grouped[file_type], expanded=False) for file_type in ordered_types]

        def on_template_type_change(event):
            selected_template_type["value"] = event.control.value
            render_template_list()
            page.update()

        def on_template_search(event):
            template_query["value"] = event.control.value or ""
            render_template_list()
            page.update()

        def add_template_dialog(kind):
            is_link = kind == "link"
            title = "Add Link Template" if is_link else "Add File Template"
            name_field = ft.TextField(label="Template name", border_radius=12, border_color=BORDER)
            type_field = dropdown(460, "Link" if is_link else "Other", file_types())
            target_field = ft.TextField(
                label="URL link" if is_link else "Local file path",
                value="https://" if is_link else "",
                border_radius=12,
                border_color=BORDER,
            )
            note_field = ft.TextField(label="Note / description", multiline=True, min_lines=4, max_lines=4, border_radius=12, border_color=BORDER)

            async def browse_file(_event):
                picked = await file_picker.pick_files(dialog_title="Choose template file", allow_multiple=False)
                if not picked:
                    return
                path = picked[0].path
                target_field.value = path
                if not name_field.value:
                    name_field.value = Path(path).stem
                type_field.value = infer_type(path)
                page.update()

            def save_template(_event):
                source = (target_field.value or "").strip()
                if not source or source == "https://":
                    show_message(page, "Missing target", "Choose a file or enter a URL.")
                    return
                file_type = type_field.value or ("Link" if is_link else infer_type(source))
                template_name = (name_field.value or (Path(source).stem if not is_link else "Link template")).strip()
                try:
                    template = create_template_from_source(template_name, source, file_type=file_type, note=note_field.value or "")
                except Exception as exc:
                    show_message(page, "Template failed", str(exc))
                    return

                templates.append(template)
                save_templates(templates)
                page.pop_dialog()
                render_current()
                show_message(page, "Template added", "Saved to the template library.")

            target_field.expand = True
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text(title, size=24, weight=ft.FontWeight.W_800, color=TEXT),
                    content=ft.Column(
                        width=540,
                        height=420,
                        spacing=12,
                        controls=[
                            name_field,
                            ft.Column(spacing=6, controls=[ft.Text("Template type", size=12, weight=ft.FontWeight.W_700, color=MUTED), type_field]),
                            ft.Row(
                                spacing=10,
                                controls=[
                                    target_field,
                                    ft.Button("Paste URL" if is_link else "Browse", on_click=(lambda _e: (target_field.__setattr__("value", str(page.clipboard.get() or "")), page.update())) if is_link else browse_file, width=116),
                                ],
                            ),
                            note_field,
                        ],
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                        ft.Button("Save template", icon=ft.Icons.SAVE_OUTLINED, on_click=save_template, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                    bgcolor=WHITE,
                    shape=ft.RoundedRectangleBorder(radius=16),
                )
            )
            page.update()

        grouped_all, ordered_template_types = grouped_visible_templates(templates)
        search_templates = ft.TextField(
            hint_text="Search templates...",
            prefix_icon=ft.Icons.SEARCH,
            height=48,
            width=360,
            border_radius=14,
            border_color=BORDER,
            focused_border_color="#CBD5E1",
            bgcolor="#F8FAFC",
            text_size=14,
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
                    ft.IconButton(icon=ft.Icons.SYNC, tooltip="Sync templates", icon_color=MUTED, on_click=sync_now),
                ],
            ),
        )
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
        main_body.controls = [toolbar, summary, library]
        page.update()

    def show_templates(_e=None):
        state["screen"] = SCREEN_TEMPLATES
        render_current()

    def sync_now(_e=None):
        create_snapshot("Before manual sync")
        synced_tasks, _synced_templates, changed = sync_from_work(force=True)
        state["last_sync_check"] = datetime.now().timestamp()
        all_tasks.clear()
        all_tasks.extend(synced_tasks)
        render_current()
        show_message(page, "Sync complete", "Work folders and templates were scanned." if changed else "Everything is already in sync.")

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
                            controls=[tool_card(tool) for tool in CREATE_TOOLS],
                        ),
                    ],
                ),
                actions=[ft.TextButton("Close", on_click=lambda _e: (page.pop_dialog(), page.update()))],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def render_settings():
        header_title.value = t("settings")
        header_subtitle.value = f"{APP_NAME} / {t('system_setup')}"
        progress_badge.value = f"{len(file_types())} file types"

        custom_types = settings.setdefault("custom_file_types", [])
        if not isinstance(custom_types, list):
            custom_types = []
            settings["custom_file_types"] = custom_types

        theme_switch = ft.Switch(label="Dark mode", value=settings.get("theme") == "Dark")
        language_select = dropdown(170, app_language(), list(LANGUAGE_LABELS.keys()))
        app_theme_select = dropdown(220, selected_app_theme(settings), list(APP_THEME_PRESETS.keys()))
        status_theme_select = dropdown(220, settings.get("status_theme_preset") or "Classic Blue", list(STATUS_THEME_PRESETS.keys()))
        realtime_switch = ft.Switch(label="Realtime sync", value=settings.get("realtime_sync_enabled", True))
        move_files_switch = ft.Switch(label="Move files when status changes", value=settings.get("move_files_on_status", True))
        confirm_switch = ft.Switch(label="Confirm risky actions", value=settings.get("confirm_risky_actions", True))
        smart_search_switch = ft.Switch(label="Smart Search parser", value=settings.get("smart_search_enabled", True))
        smart_health_switch = ft.Switch(label="Smart Health insights", value=settings.get("smart_health_enabled", True))
        workload_switch = ft.Switch(label="Workload & zombie hints", value=settings.get("workload_hints_enabled", True))
        template_rank_switch = ft.Switch(label="Smart Template ranking", value=settings.get("template_ranking_enabled", True))
        update_checks_switch = ft.Switch(label="Online update checks", value=settings.get("update_checks_enabled", True))
        offline_mode_switch = ft.Switch(label="Offline mode", value=settings.get("offline_mode", False))
        update_interval_select = dropdown(170, str(settings.get("update_check_interval_minutes", DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES)), ["1", "5", "15", "30", "60"])
        interval_select = dropdown(150, str(settings.get("sync_interval_seconds", 5)), ["3", "5", "10", "30", "60"])
        snapshot_select = dropdown(150, str(settings.get("snapshot_retention", 25)), ["10", "25", "50", "100"])
        stale_select = dropdown(150, str(settings.get("stale_doing_days", 7)), ["3", "7", "14", "30"])
        zombie_select = dropdown(150, str(settings.get("zombie_waiting_days", 30)), ["14", "30", "45", "60", "90"])
        overload_doing_select = dropdown(150, str(settings.get("overload_doing_limit", 4)), ["2", "3", "4", "5", "8"])
        overload_total_select = dropdown(150, str(settings.get("overload_total_limit", 10)), ["5", "8", "10", "15", "20"])
        settings_search = ft.TextField(
            hint_text="Search settings, file types, thresholds...",
            value=state.get("settings_search", ""),
            prefix_icon=ft.Icons.SEARCH,
            height=46,
            border_radius=14,
            border_color=BORDER,
            focused_border_color="#CBD5E1",
            bgcolor="#F8FAFC",
            text_size=13,
            color=TEXT,
            on_change=lambda e: (state.update({"settings_search": e.control.value or ""}), render_current()),
        )
        type_name = ft.TextField(label="Type name", hint_text="Example: CAD", height=48, border_radius=12, border_color=BORDER)
        type_icon = ft.TextField(label="Icon text", hint_text="CAD", height=48, width=150, border_radius=12, border_color=BORDER)
        type_color = ft.TextField(label="Color", hint_text="#2563EB", value="#2563EB", height=48, width=150, border_radius=12, border_color=BORDER)
        type_ext = ft.TextField(label="Extensions", hint_text=".dwg, .dxf, .step", height=48, expand=True, border_radius=12, border_color=BORDER)
        type_action = dropdown(170, "Open", ["Open", "Detail", "Folder"])
        icon_file = {"value": ""}
        type_color_choices = [
            "#2563EB",
            "#16A34A",
            "#D97706",
            "#7C3AED",
            "#DC2626",
            "#0891B2",
            "#DB2777",
            "#EA580C",
            "#0F766E",
            "#334155",
            "#A16207",
            "#14B8A6",
        ]
        color_preview = ft.Container(width=44, height=44, border_radius=12, bgcolor=type_color.value, border=border_all(1, BORDER))

        def app_theme_preview():
            palette = APP_THEME_PRESETS.get(app_theme_select.value or "Ocean Pro", APP_THEME_PRESETS["Ocean Pro"])
            return ft.Row(
                spacing=8,
                controls=[
                    ft.Container(width=30, height=30, border_radius=999, bgcolor=palette["bg"], border=border_all(1, palette["border"])),
                    ft.Container(width=30, height=30, border_radius=999, bgcolor=palette["surface"], border=border_all(1, palette["border"])),
                    ft.Container(width=30, height=30, border_radius=999, bgcolor=palette["primary"], border=border_all(1, palette["primary"])),
                    ft.Container(width=30, height=30, border_radius=999, bgcolor=palette["nav"], border=border_all(1, palette["nav_active"])),
                    ft.Container(width=30, height=30, border_radius=999, bgcolor=palette["nav_active"], border=border_all(1, palette["nav_active"])),
                    ft.Text("Preview", size=12, weight=ft.FontWeight.W_800, color=MUTED),
                ],
            )

        def app_theme_mockup():
            palette = APP_THEME_PRESETS.get(app_theme_select.value or "Ocean Pro", APP_THEME_PRESETS["Ocean Pro"])
            return ft.Container(
                width=210,
                height=118,
                border_radius=16,
                border=border_all(1, palette["border"]),
                bgcolor=palette["bg"],
                padding=8,
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Container(width=34, border_radius=12, bgcolor=palette["nav"], content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, controls=[
                            ft.Container(width=22, height=22, border_radius=8, bgcolor=palette["nav_active"]),
                            ft.Container(width=22, height=22, border_radius=8, bgcolor=palette["surface"]),
                            ft.Container(width=22, height=22, border_radius=8, bgcolor=palette["surface"]),
                        ])),
                        ft.Column(expand=True, spacing=8, controls=[
                            ft.Container(height=20, border_radius=8, bgcolor=palette["surface"], border=border_all(1, palette["border"])),
                            ft.Row(spacing=6, controls=[
                                ft.Container(expand=True, height=56, border_radius=10, bgcolor=palette["soft"], border=border_all(1, palette["primary"])),
                                ft.Container(expand=True, height=56, border_radius=10, bgcolor=palette["surface"], border=border_all(1, palette["border"])),
                            ]),
                        ]),
                    ],
                ),
            )

        async def choose_icon(_event):
            picked = await file_picker.pick_files(dialog_title="Choose icon image", allow_multiple=False)
            if picked:
                icon_file["value"] = picked[0].path
                show_message(page, "Icon selected", Path(picked[0].path).name)

        async def choose_profile_media(_event):
            picked = await file_picker.pick_files(dialog_title="Choose profile image or GIF", allow_multiple=False)
            if not picked:
                return
            source = Path(picked[0].path)
            suffix = source.suffix.lower()
            if suffix in PROFILE_VIDEO_EXTENSIONS:
                show_message(page, "Video profile", "This Flet runtime does not include video playback/cut support yet. Use PNG, JPG, WEBP, or animated GIF for now.")
                return
            if suffix not in PROFILE_IMAGE_EXTENSIONS:
                show_message(page, "Unsupported media", "Use PNG, JPG, JPEG, WEBP, BMP, or animated GIF.")
                return
            try:
                PROFILE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
                target = PROFILE_MEDIA_DIR / f"profile{suffix}"
                shutil.copy2(str(source), str(target))
                settings["profile_media_path"] = str(target)
                save_settings(settings)
                show_message(page, "Profile media updated", source.name, kind="success")
                render_current()
            except OSError as exc:
                show_message(page, "Profile media failed", str(exc))

        async def choose_work_folder(_event):
            nonlocal root_work
            selected = await pick_directory("Choose Work folder")
            if not selected:
                show_message(page, "No folder selected", "Work folder was not changed.")
                return
            selected_path = Path(selected)
            try:
                selected_path.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                show_message(page, "Folder not ready", str(exc))
                return

            create_snapshot("Before Work folder switch")
            settings["work_folder_path"] = str(selected_path)
            settings.pop("work_signature", None)
            settings["last_work_folder_switched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_settings(settings)
            root_work = selected_path
            current_browser_path["path"] = root_work
            state.update({"browser_selected": "", "browser_search": "", "browser_limit": 160, "group_limits": {}})

            save_tasks([])
            save_templates([])
            ensure_status_folders()
            synced_tasks, _synced_templates, _changed = sync_from_work(force=True)
            all_tasks.clear()
            all_tasks.extend(synced_tasks)
            show_message(page, "Work folder changed", f"Now reading: {root_work}")
            render_current()

        def pick_type_color(color):
            type_color.value = color
            color_preview.bgcolor = color
            page.update()

        def color_swatch(color):
            return ft.Container(
                width=30,
                height=30,
                border_radius=999,
                bgcolor=color,
                border=border_all(2, "#0F172A" if color == type_color.value else "#FFFFFF"),
                on_click=lambda _e, value=color: pick_type_color(value),
            )

        def save_theme(_event):
            global UI_LANGUAGE
            settings["theme"] = "Dark" if theme_switch.value else "Light"
            settings["language"] = language_select.value or "en"
            UI_LANGUAGE = settings["language"]
            settings["app_theme_preset"] = app_theme_select.value or "Ocean Pro"
            settings["status_theme_preset"] = status_theme_select.value or "Classic Blue"
            save_settings(settings)
            apply_app_theme(settings)
            page.bgcolor = BG
            page.theme_mode = ft.ThemeMode.DARK if theme_switch.value else ft.ThemeMode.LIGHT
            render_current()
            show_message(page, "Settings", "Theme saved.")

        def save_policy(_event):
            settings["realtime_sync_enabled"] = bool(realtime_switch.value)
            settings["move_files_on_status"] = bool(move_files_switch.value)
            settings["confirm_risky_actions"] = bool(confirm_switch.value)
            settings["smart_search_enabled"] = bool(smart_search_switch.value)
            settings["smart_health_enabled"] = bool(smart_health_switch.value)
            settings["workload_hints_enabled"] = bool(workload_switch.value)
            settings["template_ranking_enabled"] = bool(template_rank_switch.value)
            settings["update_checks_enabled"] = bool(update_checks_switch.value)
            settings["offline_mode"] = bool(offline_mode_switch.value)
            settings["update_check_interval_minutes"] = int(update_interval_select.value or DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES)
            settings["sync_interval_seconds"] = int(interval_select.value or 5)
            settings["snapshot_retention"] = int(snapshot_select.value or 25)
            settings["stale_doing_days"] = int(stale_select.value or 7)
            settings["zombie_waiting_days"] = int(zombie_select.value or 30)
            settings["overload_doing_limit"] = int(overload_doing_select.value or 4)
            settings["overload_total_limit"] = int(overload_total_select.value or 10)
            save_settings(settings)
            show_message(page, "Settings", "Sync and safety policy saved.")

        def save_all_settings(_event):
            global UI_LANGUAGE
            settings["theme"] = "Dark" if theme_switch.value else "Light"
            settings["language"] = language_select.value or "en"
            UI_LANGUAGE = settings["language"]
            settings["app_theme_preset"] = app_theme_select.value or "Ocean Pro"
            settings["status_theme_preset"] = status_theme_select.value or "Classic Blue"
            settings["realtime_sync_enabled"] = bool(realtime_switch.value)
            settings["move_files_on_status"] = bool(move_files_switch.value)
            settings["confirm_risky_actions"] = bool(confirm_switch.value)
            settings["smart_search_enabled"] = bool(smart_search_switch.value)
            settings["smart_health_enabled"] = bool(smart_health_switch.value)
            settings["workload_hints_enabled"] = bool(workload_switch.value)
            settings["template_ranking_enabled"] = bool(template_rank_switch.value)
            settings["update_checks_enabled"] = bool(update_checks_switch.value)
            settings["offline_mode"] = bool(offline_mode_switch.value)
            settings["update_check_interval_minutes"] = int(update_interval_select.value or DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES)
            settings["sync_interval_seconds"] = int(interval_select.value or 5)
            settings["snapshot_retention"] = int(snapshot_select.value or 25)
            settings["stale_doing_days"] = int(stale_select.value or 7)
            settings["zombie_waiting_days"] = int(zombie_select.value or 30)
            settings["overload_doing_limit"] = int(overload_doing_select.value or 4)
            settings["overload_total_limit"] = int(overload_total_select.value or 10)
            save_settings(settings)
            apply_app_theme(settings)
            page.bgcolor = BG
            page.theme_mode = ft.ThemeMode.DARK if theme_switch.value else ft.ThemeMode.LIGHT
            page.update()
            show_message(page, "Settings", "Settings saved.")

        def reset_smart_defaults(_event):
            settings.update(
                {
                    "smart_search_enabled": True,
                    "smart_health_enabled": True,
                    "workload_hints_enabled": True,
                    "template_ranking_enabled": True,
                    "stale_doing_days": 7,
                    "zombie_waiting_days": 30,
                    "overload_doing_limit": 4,
                    "overload_total_limit": 10,
                }
            )
            save_settings(settings)
            show_message(page, "Settings", "Smart defaults restored.")
            render_current()

        def reset_sync_defaults(_event):
            settings.update(
                {
                    "realtime_sync_enabled": True,
                    "sync_interval_seconds": 5,
                    "snapshot_retention": 25,
                    "move_files_on_status": True,
                    "confirm_risky_actions": True,
                }
            )
            save_settings(settings)
            show_message(page, "Settings", "Sync and safety defaults restored.")
            render_current()

        def reset_ui_defaults(_event):
            global UI_LANGUAGE
            settings["theme"] = "Light"
            settings["language"] = "en"
            UI_LANGUAGE = "en"
            settings["app_theme_preset"] = "Ocean Pro"
            settings["status_theme_preset"] = "Classic Blue"
            save_settings(settings)
            apply_app_theme(settings)
            page.bgcolor = BG
            page.theme_mode = ft.ThemeMode.LIGHT
            show_message(page, "Settings", "UI defaults restored.")
            render_current()

        def parse_extensions(value):
            parts = [part.strip().lower() for part in value.replace(";", ",").split(",")]
            normalized = []
            for part in parts:
                if not part:
                    continue
                normalized.append(part if part.startswith(".") else f".{part}")
            return normalized

        def add_file_type(_event):
            name = (type_name.value or "").strip()
            if not name:
                show_message(page, "Missing type name", "Please enter a file type name.")
                return
            if name.casefold() in [item.casefold() for item in file_types()] or any(str(item.get("name", "")).casefold() == name.casefold() for item in custom_types):
                show_message(page, "Already exists", "This file type already exists.")
                return
            extensions = parse_extensions(type_ext.value or "")
            existing_extensions = {
                extension
                for item in custom_types
                for extension in parse_extensions(",".join(item.get("extensions", [])) if isinstance(item.get("extensions", []), list) else str(item.get("extensions", "")))
            }
            duplicate_extensions = [extension for extension in extensions if extension in existing_extensions]
            if duplicate_extensions:
                show_message(page, "Extension already mapped", f"{', '.join(duplicate_extensions[:3])} already belongs to another type.")
                return
            custom_types.append(
                {
                    "name": name,
                    "icon": (type_icon.value or name[:3]).strip().upper(),
                    "color": (type_color.value or "#2563EB").strip(),
                    "icon_file": icon_file["value"],
                    "extensions": extensions,
                    "default_action": type_action.value or "Open",
                }
            )
            save_settings(settings)
            ensure_status_folders()
            try:
                page.pop_dialog()
            except Exception:
                pass
            render_current()
            show_message(page, "File type added", f"{name} is ready.")

        def show_add_file_type_dialog(_event=None):
            type_name.value = ""
            type_icon.value = ""
            type_color.value = "#2563EB"
            color_preview.bgcolor = "#2563EB"
            type_ext.value = ""
            type_action.value = "Open"
            icon_file["value"] = ""
            page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Row(
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.CATEGORY_OUTLINED, color=PRIMARY),
                            ft.Text("Add custom work type", size=20, weight=ft.FontWeight.W_900, color=TEXT),
                        ],
                    ),
                    content=ft.Column(
                        width=660,
                        height=370,
                        spacing=14,
                        controls=[
                            ft.Text(f"Create a new category for files, links, templates, and Work folders. {APP_NAME} will use the extensions to classify matching files.", size=13, color=MUTED),
                            ft.Row(spacing=10, controls=[type_name, type_icon, type_action]),
                            ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[color_preview, type_color, ft.Button("Icon image", icon=ft.Icons.IMAGE_OUTLINED, on_click=choose_icon, width=130)]),
                            ft.Container(
                                padding=pad_sym(horizontal=12, vertical=10),
                                border_radius=14,
                                bgcolor="#F8FAFC",
                                border=border_all(1, BORDER),
                                content=ft.Column(
                                    spacing=8,
                                    controls=[
                                        ft.Text("Quick colors", size=12, weight=ft.FontWeight.W_900, color=MUTED),
                                        ft.Row(spacing=8, wrap=True, controls=[color_swatch(color) for color in type_color_choices]),
                                    ],
                                ),
                            ),
                            type_ext,
                        ],
                    ),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                        ft.Button("Save type", icon=ft.Icons.SAVE_OUTLINED, on_click=add_file_type, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                    bgcolor=WHITE,
                    shape=ft.RoundedRectangleBorder(radius=18),
                )
            )
            page.update()

        def remove_file_type(item):
            if item in custom_types:
                custom_types.remove(item)
                save_settings(settings)
                render_current()

        def type_row(name, icon_text, extensions, custom_item=None):
            is_custom = custom_item is not None
            color = custom_item.get("color", PRIMARY) if custom_item else type_style(name)[2]
            default_action = custom_item.get("default_action", "") if custom_item else ""
            detail_text = ", ".join(extensions) if extensions else ("Your extension rules" if is_custom else "System file/link rules")
            action_text = f"{default_action} by default" if default_action else "Smart classify"
            source_text = "My type" if is_custom else "System type"
            return ft.Container(
                height=66,
                bgcolor=WHITE,
                border=border_all(1, BORDER),
                border_radius=14,
                padding=pad_only(left=12, right=8),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=38, height=38, border_radius=11, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Text(icon_text or name[:2].upper(), size=12, weight=ft.FontWeight.W_800, color=color)),
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(name, size=15, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(detail_text, size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        ft.Container(padding=pad_sym(horizontal=9, vertical=4), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(action_text, size=11, weight=ft.FontWeight.W_800, color=MUTED)),
                        ft.Container(padding=pad_sym(horizontal=9, vertical=4), border_radius=999, bgcolor="#EFF6FF" if is_custom else "#F8FAFC", content=ft.Text(source_text, size=11, weight=ft.FontWeight.W_800, color=PRIMARY if is_custom else MUTED)),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color="#DC2626", disabled=not is_custom, tooltip="Delete custom type", on_click=lambda _e, item=custom_item: remove_file_type(item)),
                    ],
                ),
            )

        settings_query = state.get("settings_search", "").strip().casefold()

        def settings_visible(*terms):
            return not settings_query or any(settings_query in str(term).casefold() for term in terms)

        builtin_rows = [type_row(name, name[:3].upper(), [], None) for name in FILE_TYPES if settings_visible(name, "built-in file type")]
        custom_rows = [
            type_row(item.get("name", "Custom"), item.get("icon", ""), item.get("extensions", []), item)
            for item in custom_types
            if settings_visible(item.get("name", "Custom"), item.get("extensions", []), "custom file type")
        ]
        status_rows = [
            ("Tasks", str(len(all_tasks)), PRIMARY, "#EFF6FF"),
            ("Templates", str(len(load_templates())), "#7C3AED", "#F5F3FF"),
            ("Snapshots", str(len(list_snapshots(100))), "#059669", "#ECFDF5"),
            ("Last sync", str(settings.get("last_sync_at") or "Never"), "#D97706", "#FFFBEB"),
        ]

        def settings_stat(label, value, color, bg):
            return ft.Container(
                expand=True,
                height=66,
                bgcolor=bg,
                border=border_all(1, color + "44"),
                border_radius=16,
                padding=pad_sym(horizontal=12, vertical=9),
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(label, size=11, weight=ft.FontWeight.W_900, color=MUTED),
                        ft.Text(value, size=14, weight=ft.FontWeight.W_900, color=color, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ],
                ),
            )

        system_card = ft.Container(
            expand=True,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=22,
            padding=22,
            content=ft.ListView(
                expand=True,
                spacing=14,
                controls=[
                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=MUTED), ft.Text("System", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
                    settings_search,
                    ft.Container(
                        border=border_all(1, "#E0E7FF"),
                        border_radius=16,
                        padding=14,
                        bgcolor="#F8FBFF",
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.INFO_OUTLINED, color=PRIMARY), ft.Text("Credits", size=16, weight=ft.FontWeight.W_800, color=TEXT)]),
                                ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[app_logo_control(48, 14), ft.Column(spacing=3, controls=[ft.Text(APP_NAME, size=17, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Desktop Work Board", size=12, color=MUTED)])]),
                                ft.Text("Developer / Creator: HOYTURBRO", size=13, weight=ft.FontWeight.W_800, color=TEXT, selectable=True),
                                ft.Text("Publisher: HOYTURBRO", size=12, color=MUTED, selectable=True),
                                ft.Text("Alias: Hoyturbro | Product: SA CHECK Desktop Work Board | Copyright (c) 2026 HOYTURBRO", size=12, color=MUTED, selectable=True),
                                ft.Row(spacing=10, controls=[ft.Button("About SA CHECK", icon=ft.Icons.INFO_OUTLINED, on_click=show_about), ft.Button("User guide", icon=ft.Icons.HELP_OUTLINE, on_click=show_help)]),
                            ],
                        ),
                    ),
                    ft.Container(
                        border=border_all(1, "#DBEAFE"),
                        border_radius=16,
                        padding=14,
                        bgcolor="#F8FBFF",
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.FOLDER_SPECIAL_OUTLINED, color=PRIMARY), ft.Text("Work Folder Source", size=16, weight=ft.FontWeight.W_800, color=TEXT)]),
                                ft.Text(str(root_work), size=12, color=MUTED, selectable=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        ft.Button("Choose Work folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=choose_work_folder),
                                        ft.Button("Open Work folder", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _e: os.startfile(str(root_work)) if root_work.exists() else show_message(page, "Folder not found", "Choose or create a Work folder first.")),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Text(f"Data file\n{DATA_FILE}", size=13, color=MUTED, selectable=True),
                    ft.Row(spacing=10, controls=[settings_stat(*row) for row in status_rows]),
                    ft.Container(
                        border=border_all(1, "#E2E8F0"),
                        border_radius=16,
                        padding=14,
                        bgcolor="#FFFFFF",
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.PALETTE_OUTLINED, color=PRIMARY), ft.Text("Appearance", size=16, weight=ft.FontWeight.W_800, color=TEXT)]),
                                ft.Container(
                                    border=border_all(1, "#DBEAFE"),
                                    border_radius=14,
                                    bgcolor="#F8FBFF",
                                    padding=12,
                                    content=ft.Row(
                                        spacing=12,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Container(width=40, height=40, border_radius=12, bgcolor="#EFF6FF", alignment=CENTER, content=ft.Icon(ft.Icons.TRANSLATE, color=PRIMARY, size=21)),
                                            ft.Column(spacing=3, expand=True, controls=[ft.Text(t("language"), size=13, weight=ft.FontWeight.W_900, color=TEXT), ft.Text(t("language_hint"), size=11, color=MUTED)]),
                                            language_select,
                                        ],
                                    ),
                                ),
                                theme_switch,
                                ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[profile_media_control(52), ft.Column(spacing=4, expand=True, controls=[ft.Text("Sidebar profile media", size=13, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Use PNG, JPG, WEBP, BMP, or animated GIF. Video support needs a video runtime in a later build.", size=11, color=MUTED)]), ft.Button("Upload media", icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, on_click=choose_profile_media)]),
                                ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("App theme", size=13, weight=ft.FontWeight.W_800, color=MUTED), app_theme_select, app_theme_preview()]),
                                app_theme_mockup(),
                                ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Status theme", size=13, weight=ft.FontWeight.W_800, color=MUTED), status_theme_select]),
                                ft.Row(
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Button("Apply theme", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=save_theme, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                                        ft.Text(t("theme_apply_hint"), size=11, color=MUTED),
                                    ],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Container(width=74, height=28, border_radius=999, bgcolor=status_theme(STATUS_PENDING)[0], border=border_all(1, status_theme(STATUS_PENDING)[1]), alignment=CENTER, content=ft.Text("Waiting", size=11, weight=ft.FontWeight.W_800, color=status_theme(STATUS_PENDING)[1])),
                                        ft.Container(width=74, height=28, border_radius=999, bgcolor=status_theme(STATUS_PROGRESS)[0], border=border_all(1, status_theme(STATUS_PROGRESS)[1]), alignment=CENTER, content=ft.Text("Doing", size=11, weight=ft.FontWeight.W_800, color=status_theme(STATUS_PROGRESS)[1])),
                                        ft.Container(width=74, height=28, border_radius=999, bgcolor=status_theme(STATUS_DONE)[0], border=border_all(1, status_theme(STATUS_DONE)[1]), alignment=CENTER, content=ft.Text("Success", size=11, weight=ft.FontWeight.W_800, color=status_theme(STATUS_DONE)[1])),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        border=border_all(1, "#DBEAFE"),
                        border_radius=16,
                        padding=14,
                        bgcolor="#F8FBFF",
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, color=PRIMARY), ft.Text("System Updates", size=16, weight=ft.FontWeight.W_800, color=TEXT)]),
                                ft.Text(f"Current version: {APP_VERSION}. Update checks only use internet for app updates; normal work stays offline-first.", size=12, color=MUTED),
                                update_checks_switch,
                                offline_mode_switch,
                                ft.Row(
                                    spacing=12,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Column(
                                            spacing=2,
                                            expand=True,
                                            controls=[
                                                ft.Text("Auto-check interval", size=13, weight=ft.FontWeight.W_800, color=TEXT),
                                                ft.Text("How often SA CHECK checks GitHub while Online mode is enabled.", size=11, color=MUTED),
                                            ],
                                        ),
                                        ft.Row(spacing=8, controls=[update_interval_select, ft.Text("minutes", size=12, color=MUTED)]),
                                    ],
                                ),
                                ft.Row(spacing=10, controls=[
                                    ft.Button("Check now", icon=ft.Icons.REFRESH, on_click=lambda _e: check_for_updates(manual=True)),
                                    ft.Button("Version notes", icon=ft.Icons.FACT_CHECK_OUTLINED, on_click=show_version_notes),
                                ]),
                            ],
                        ),
                    ),
                    ft.Container(
                        border=border_all(1, BORDER),
                        border_radius=16,
                        padding=14,
                        bgcolor="#F8FAFC",
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.SHIELD_OUTLINED, color=MUTED), ft.Text("Sync & Safety Policy", size=16, weight=ft.FontWeight.W_800, color=TEXT)]),
                                realtime_switch,
                                ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Sync interval", size=13, color=MUTED), interval_select, ft.Text("seconds", size=13, color=MUTED)]),
                                ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Snapshots kept", size=13, color=MUTED), snapshot_select]),
                                move_files_switch,
                                confirm_switch,
                            ],
                        ),
                    ),
                    ft.Container(
                        border=border_all(1, "#DBEAFE"),
                        border_radius=16,
                        padding=14,
                        bgcolor="#F8FBFF",
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.TIPS_AND_UPDATES_OUTLINED, color=PRIMARY), ft.Text("Smart Features", size=16, weight=ft.FontWeight.W_800, color=TEXT)]),
                                smart_search_switch,
                                smart_health_switch,
                                workload_switch,
                                template_rank_switch,
                                ft.Container(
                                    border=border_all(1, "#E2E8F0"),
                                    border_radius=14,
                                    padding=12,
                                    bgcolor=WHITE,
                                    content=ft.Column(
                                        spacing=10,
                                        controls=[
                                            ft.Text("Smart thresholds", size=13, weight=ft.FontWeight.W_900, color=TEXT),
                                            ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Stale Doing", size=12, color=MUTED), stale_select, ft.Text("days", size=12, color=MUTED), ft.Text("Zombie Waiting", size=12, color=MUTED), zombie_select, ft.Text("days", size=12, color=MUTED)]),
                                            ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Overload Doing", size=12, color=MUTED), overload_doing_select, ft.Text("tasks/day", size=12, color=MUTED), ft.Text("Overload Total", size=12, color=MUTED), overload_total_select, ft.Text("tasks/day", size=12, color=MUTED)]),
                                        ],
                                    ),
                                ),
                                ft.Text(f"These features only analyze {APP_NAME} records and folder metadata. They do not rename, move, or delete Work files.", size=12, color=MUTED),
                            ],
                        ),
                    ),
                    ft.Container(
                        border=border_all(1, "#E2E8F0"),
                        border_radius=16,
                        padding=14,
                        bgcolor="#FFFFFF",
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.RESTART_ALT, color=MUTED), ft.Text("Reset Defaults", size=16, weight=ft.FontWeight.W_800, color=TEXT)]),
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        ft.Button("Reset smart", icon=ft.Icons.TIPS_AND_UPDATES_OUTLINED, on_click=reset_smart_defaults),
                                        ft.Button("Reset sync", icon=ft.Icons.SYNC, on_click=reset_sync_defaults),
                                        ft.Button("Reset UI", icon=ft.Icons.PALETTE_OUTLINED, on_click=reset_ui_defaults),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Row(spacing=10, controls=[ft.Button("Save settings", icon=ft.Icons.SAVE_OUTLINED, on_click=save_all_settings), ft.Button("Work browser", icon=ft.Icons.FOLDER_OUTLINED, on_click=show_browser), ft.Button("Sync now", icon=ft.Icons.SYNC, on_click=sync_now)]),
                    ft.Row(spacing=10, controls=[ft.Button("Reload data", icon=ft.Icons.REFRESH, on_click=lambda _e: (all_tasks.clear(), all_tasks.extend(load_tasks()), render_current())), ft.Button("Create folders", icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED, on_click=lambda _e: (ensure_status_folders(), show_message(page, "Folders ready", "Work folders are ready."))), ft.Button("Open data folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e: os.startfile(str(DATA_FILE.parent)))]),
                ],
            ),
        )
        type_card = ft.Container(
            expand=True,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=22,
            padding=22,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.CATEGORY_OUTLINED, color=MUTED), ft.Text("Type Library", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Button("+ Add custom type", icon=ft.Icons.ADD, on_click=show_add_file_type_dialog, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                        ],
                    ),
                    ft.Container(
                        padding=pad_sym(horizontal=14, vertical=12),
                        border_radius=16,
                        bgcolor="#F8FAFC",
                        border=border_all(1, BORDER),
                        content=ft.Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, size=18, color=PRIMARY),
                                ft.Text("System types are ready-made categories. My types are your own rules using extensions, color, and default action.", size=12, color=MUTED, expand=True),
                            ],
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            spacing=10,
                            expand=True,
                            controls=[*custom_rows, *builtin_rows]
                            if [*custom_rows, *builtin_rows]
                            else [ft.Container(height=120, alignment=CENTER, content=ft.Text("No file types match this search.", size=13, color=MUTED_2))],
                        ),
                    ),
                ],
            ),
        )
        active_settings_tab = state.get("settings_tab", "system")

        def settings_tab_button(label, icon, tab_key):
            selected = active_settings_tab == tab_key
            return ft.Container(
                height=42,
                padding=pad_sym(horizontal=14),
                border_radius=12,
                bgcolor=TEXT if selected else WHITE,
                border=border_all(1, TEXT if selected else BORDER),
                on_click=lambda _e, key=tab_key: (state.update({"settings_tab": key}), render_current()),
                content=ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, size=18, color=WHITE if selected else MUTED),
                        ft.Text(label, size=13, weight=ft.FontWeight.W_800, color=WHITE if selected else TEXT),
                    ],
                ),
            )

        main_body.controls = [
            ft.Column(
                spacing=14,
                expand=True,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            settings_tab_button("System & Theme", ft.Icons.TUNE_OUTLINED, "system"),
                            settings_tab_button("File Types", ft.Icons.CATEGORY_OUTLINED, "types"),
                        ],
                    ),
                    ft.Container(expand=True, content=system_card if active_settings_tab == "system" else type_card),
                ],
            )
        ]
        page.update()

    def render_health():
        header_title.value = "Health Center"
        header_subtitle.value = f"{APP_NAME} / Safety & Activity"
        templates = load_templates()
        problems = broken_items(all_tasks, templates)
        activity = load_activity_log(80)
        snapshots = list_snapshots(5)
        smart_health_on = settings.get("smart_health_enabled", True)
        workload_on = settings.get("workload_hints_enabled", True)
        stale_limit = int(settings.get("stale_doing_days") or 7)
        zombie_limit = int(settings.get("zombie_waiting_days") or 30)
        overload_doing_limit = int(settings.get("overload_doing_limit") or 4)
        overload_total_limit = int(settings.get("overload_total_limit") or 10)
        health_filter = state.get("health_filter", "All")

        def path_writable(path):
            try:
                path.mkdir(parents=True, exist_ok=True)
                probe = path / ".sacheck_health_probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                return True
            except Exception:
                return False

        health_checks = [
            {
                "label": "Work folder",
                "ok": root_work.exists() and root_work.is_dir(),
                "detail": str(root_work),
                "icon": ft.Icons.FOLDER_OUTLINED,
            },
            {
                "label": "Data folder",
                "ok": path_writable(DATA_FILE.parent),
                "detail": str(DATA_FILE.parent),
                "icon": ft.Icons.SAVE_OUTLINED,
            },
            {
                "label": "Tasks file",
                "ok": isinstance(all_tasks, list),
                "detail": f"{len(all_tasks)} records loaded",
                "icon": ft.Icons.FACT_CHECK_OUTLINED,
            },
            {
                "label": "Templates file",
                "ok": isinstance(templates, list),
                "detail": f"{len(templates)} records loaded",
                "icon": ft.Icons.ARTICLE_OUTLINED,
            },
            {
                "label": "Update channel",
                "ok": bool(update_channel_url()) and not settings.get("offline_mode", False),
                "detail": "Online checks enabled" if not settings.get("offline_mode", False) else "Offline mode is on",
                "icon": ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED,
            },
            {
                "label": "Snapshots",
                "ok": bool(snapshots),
                "detail": f"{len(snapshots)} recent snapshots",
                "icon": ft.Icons.BACKUP_OUTLINED,
            },
        ]
        health_ok_count = sum(1 for check in health_checks if check["ok"])
        broken_tasks = [problem for problem in problems if problem.get("source") == "Task"]
        broken_templates = [problem for problem in problems if problem.get("source") == "Template"]

        def problem_matches_filter(problem):
            reason = problem.get("reason", "")
            if health_filter == "Tasks":
                return problem.get("source") == "Task"
            if health_filter == "Templates":
                return problem.get("source") == "Template"
            if health_filter == "Missing":
                return reason == "Missing file/folder"
            if health_filter == "No target":
                return reason == "No target"
            if health_filter == "URL shortcut":
                return reason == "Missing URL shortcut"
            return True

        visible_problems = [problem for problem in problems if problem_matches_filter(problem)]

        def task_date_value(task):
            try:
                return datetime.strptime(task_calendar_date(task), "%Y-%m-%d").date()
            except ValueError:
                return date.today()

        type_mismatches = [
            task
            for task in all_tasks
            if task.get("detected_type")
            and task.get("type")
            and task.get("detected_type") not in {"Other", "Link"}
            and task.get("type") != task.get("detected_type")
        ][:12]
        stale_doing = [
            task
            for task in all_tasks
            if workload_on and task.get("status") == STATUS_PROGRESS and (date.today() - task_date_value(task)).days >= stale_limit
        ][:12]
        zombie_waiting = [
            task
            for task in all_tasks
            if workload_on and task.get("status") == STATUS_PENDING and (date.today() - task_date_value(task)).days >= zombie_limit
        ][:12]
        day_load = {}
        for task in all_tasks:
            day_key = task_calendar_date(task)
            day_load.setdefault(day_key, {"total": 0, "doing": 0, "waiting": 0})
            day_load[day_key]["total"] += 1
            if task.get("status") == STATUS_PROGRESS:
                day_load[day_key]["doing"] += 1
            if task.get("status") == STATUS_PENDING:
                day_load[day_key]["waiting"] += 1
        overloaded_days = [
            (day_key, counts)
            for day_key, counts in sorted(day_load.items(), key=lambda row: row[0], reverse=True)
            if workload_on and (counts["doing"] >= overload_doing_limit or counts["total"] >= overload_total_limit)
        ][:8]
        duplicate_groups = {}
        for item in [*all_tasks, *templates]:
            key = (str(item.get("name", "")).strip().casefold(), str(item.get("type", "Other")).casefold())
            if key[0]:
                duplicate_groups.setdefault(key, []).append(item)
        duplicate_items = [items for items in duplicate_groups.values() if len(items) > 1][:8]
        inbox_path = root_work / "Inbox"
        inbox_items = []
        if inbox_path.exists():
            try:
                inbox_items = [item for item in sorted(inbox_path.iterdir(), key=lambda p: p.name.casefold()) if not item.name.startswith("~$")][:10]
            except OSError:
                inbox_items = []
        smart_findings = len(type_mismatches) + len(stale_doing) + len(zombie_waiting) + len(overloaded_days) + len(duplicate_items) + len(inbox_items)
        health_score = max(0, 100 - len(problems) * 8 - len(type_mismatches) * 4 - len(stale_doing) * 5 - len(zombie_waiting) * 3 - len(overloaded_days) * 3 - len(duplicate_items) * 4)
        progress_badge.value = f"{health_score}% smart score"

        def insight_line(icon, title, detail, color=PRIMARY, bg="#EFF6FF"):
            return ft.Container(
                height=42,
                bgcolor=bg,
                border=border_all(1, "#E2E8F0"),
                border_radius=12,
                padding=pad_only(left=10, right=10),
                content=ft.Row(
                    spacing=9,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, size=16, color=color),
                        ft.Column(
                            spacing=0,
                            expand=True,
                            controls=[
                                ft.Text(title, size=12, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(detail, size=10, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                    ],
                ),
            )

        def smart_card(title, icon, color, bg, lines, empty_text):
            return ft.Container(
                expand=True,
                height=188,
                bgcolor=bg,
                border=border_all(1, color + "55"),
                border_radius=16,
                padding=16,
                content=ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(width=36, height=36, border_radius=10, bgcolor=WHITE, border=border_all(1, color + "44"), alignment=CENTER, content=ft.Icon(icon, size=19, color=color)),
                                ft.Text(title, size=16, weight=ft.FontWeight.W_900, color=TEXT, expand=True),
                            ],
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.ListView(
                                spacing=7,
                                controls=lines if lines else [ft.Container(expand=True, alignment=CENTER, content=ft.Text(empty_text, size=12, color=MUTED_2))],
                            ),
                        ),
                    ],
                ),
            )

        mismatch_lines = [
            insight_line(
                ft.Icons.CATEGORY_OUTLINED,
                task.get("name", "Untitled"),
                f"Folder type {task.get('type')} but detected {task.get('detected_type')}",
                color="#D97706",
                bg="#FFFBEB",
            )
            for task in type_mismatches[:3]
        ]
        stale_lines = [
            insight_line(
                ft.Icons.SCHEDULE,
                task.get("name", "Untitled"),
                f"Doing for {(date.today() - task_date_value(task)).days} days",
                color="#EA580C",
                bg="#FFF7ED",
            )
            for task in stale_doing[:3]
        ]
        duplicate_lines = [
            insight_line(
                ft.Icons.CONTENT_COPY,
                items[0].get("name", "Untitled"),
                f"{len(items)} records share this name/type",
                color="#7C3AED",
                bg="#F5F3FF",
            )
            for items in duplicate_items[:3]
        ]
        zombie_lines = [
            insight_line(
                ft.Icons.HOURGLASS_EMPTY,
                task.get("name", "Untitled"),
                f"Waiting for {(date.today() - task_date_value(task)).days} days",
                color="#64748B",
                bg="#F8FAFC",
            )
            for task in zombie_waiting[:2]
        ]
        workload_lines = [
            insight_line(
                ft.Icons.EVENT_BUSY_OUTLINED,
                day_key,
                f"{counts['total']} tasks, {counts['doing']} doing, {counts['waiting']} waiting",
                color="#DC2626" if counts["doing"] >= overload_doing_limit else "#D97706",
                bg="#FEF2F2" if counts["doing"] >= overload_doing_limit else "#FFFBEB",
            )
            for day_key, counts in overloaded_days[:3]
        ]
        inbox_lines = [
            insight_line(
                ft.Icons.INBOX_OUTLINED,
                item.name,
                f"Suggested: Waiting / {infer_type(str(item))}",
                color="#0891B2",
                bg="#ECFEFF",
            )
            for item in inbox_items[:4]
        ]
        smart_summary_lines = [
            insight_line(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, f"{health_score}% Health Score", f"{len(problems)} broken, {smart_findings} smart findings", color=DONE_TEXT if health_score >= 80 else DOING_TEXT if health_score >= 55 else "#DC2626", bg=DONE_BG if health_score >= 80 else DOING_BG if health_score >= 55 else "#FEF2F2"),
            insight_line(ft.Icons.TIPS_AND_UPDATES_OUTLINED, "Read-only intelligence", "No Work files are changed by this scan.", color=PRIMARY, bg="#EFF6FF"),
            *stale_lines[:1],
            *zombie_lines[:1],
        ]
        smart_overview = ft.Row(
            spacing=14,
            controls=[
                smart_card("Smart Score", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, PRIMARY, "#F8FBFF", smart_summary_lines, "System looks clean"),
                smart_card("Auto Classify", ft.Icons.AUTO_FIX_HIGH_OUTLINED, "#D97706", "#FFFBEB", [*mismatch_lines, *duplicate_lines][:4], "No category or duplicate hints"),
                smart_card("Workload", ft.Icons.EVENT_BUSY_OUTLINED, "#DC2626", "#FEF2F2", [*workload_lines, *stale_lines, *zombie_lines][:4], "No overload or zombie hints"),
                smart_card("Smart Inbox", ft.Icons.INBOX_OUTLINED, "#0891B2", "#ECFEFF", inbox_lines, "Create Work\\Inbox to stage loose files"),
            ],
        )

        def issue_row(problem):
            item = problem.get("item", {})
            icon, icon_color = task_icon(item.get("type", "Other"))
            is_template = problem.get("source") == "Template"

            def detail(_event):
                show_task_detail(page, item, save_and_render, all_tasks, is_template=is_template)

            def copy_target(_event):
                page.clipboard.set(problem.get("target") or item_target(item))
                show_message(page, "Copied", "Target copied.")

            def save_repaired(message):
                if is_template:
                    save_templates(templates)
                else:
                    save_tasks(all_tasks)
                log_activity("Smart Repair", message, {"item": item})
                render_current()
                show_message(page, "Smart Repair", message)

            async def relink(_event):
                if item.get("target_kind") == "folder":
                    selected = await pick_directory("Relink folder")
                else:
                    picked = await file_picker.pick_files(dialog_title="Relink file", allow_multiple=False)
                    selected = picked[0].path if picked else ""
                if not selected:
                    return
                before = dict(item)
                create_snapshot("Before smart repair relink")
                item["link"] = selected
                item["shortcut_path"] = selected
                item["target_kind"] = "folder" if Path(selected).is_dir() else "file"
                item["file_key"] = normalized_file_key(selected)
                item["type"] = item.get("type") or infer_type(selected)
                if not is_template:
                    push_undo({"kind": "task_restore", "action": "Relink target", "task_id": item.get("id"), "before": before, "after": dict(item)})
                save_repaired(f"{item.get('name', 'Item')} relinked.")

            def mark_url(_event):
                url_field = ft.TextField(label="URL", value=item.get("link", "https://") or "https://", border_radius=12, border_color=BORDER)

                def save_url(_save_event):
                    before = dict(item)
                    url = (url_field.value or "").strip()
                    if not url.startswith(("http://", "https://")):
                        show_message(page, "Invalid URL", "URL must start with http:// or https://")
                        return
                    create_snapshot("Before smart repair URL")
                    item["link"] = url
                    item["shortcut_path"] = ""
                    item["target_kind"] = "url"
                    item["file_key"] = ""
                    item["detected_type"] = infer_type(url)
                    if not is_template:
                        push_undo({"kind": "task_restore", "action": "Mark URL", "task_id": item.get("id"), "before": before, "after": dict(item)})
                    page.pop_dialog()
                    save_repaired(f"{item.get('name', 'Item')} marked as URL.")

                page.show_dialog(
                    ft.AlertDialog(
                        modal=True,
                        title=ft.Text("Mark as external URL", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                        content=ft.Column(width=460, height=90, controls=[url_field]),
                        actions=[ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())), ft.Button("Save URL", icon=ft.Icons.LINK, on_click=save_url, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12)))],
                        bgcolor=WHITE,
                        shape=ft.RoundedRectangleBorder(radius=16),
                    )
                )
                page.update()

            def remove_record(_event):
                create_snapshot("Before removing broken record")
                before = dict(item)
                if is_template:
                    if item in templates:
                        templates.remove(item)
                    save_templates(templates)
                else:
                    if item in all_tasks:
                        all_tasks.remove(item)
                    save_tasks(all_tasks)
                    push_undo({"kind": "task_restore", "action": "Remove broken record", "task_id": before.get("id"), "before": before, "after": {}})
                log_activity("Smart Repair", f"{before.get('name', 'Item')} removed from records.", {"item": before})
                render_current()

            return ft.Container(
                height=62,
                bgcolor=WHITE,
                border=border_all(1, BORDER),
                border_radius=14,
                padding=pad_only(left=12, right=8),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=38, height=38, border_radius=10, bgcolor="#FEF2F2", border=border_all(1, "#FECACA"), alignment=CENTER, content=ft.Icon(icon, size=19, color=icon_color)),
                        ft.Column(
                            expand=True,
                            spacing=2,
                            controls=[
                                ft.Text(item.get("name", "Untitled"), size=14, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"{problem.get('source')} | {problem.get('reason')} | {item.get('link') or item.get('shortcut_path') or '-'}", size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        row_action_button("Relink", ft.Icons.DRIVE_FILE_MOVE_OUTLINE, relink, width=128, primary=True),
                        row_action_button("Detail", ft.Icons.INFO_OUTLINE, detail, width=128),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            icon_color=MUTED_2,
                            items=[
                                ft.PopupMenuItem(content="Mark as URL", icon=ft.Icons.LINK, on_click=mark_url),
                                ft.PopupMenuItem(content="Remove record", icon=ft.Icons.DELETE_OUTLINE, on_click=remove_record),
                                ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_target),
                                ft.PopupMenuItem(content="Sync now", icon=ft.Icons.SYNC, on_click=sync_now),
                            ],
                        ),
                    ],
                ),
            )

        def activity_row(entry):
            return ft.Container(
                height=58,
                bgcolor=WHITE,
                border=border_all(1, BORDER),
                border_radius=14,
                padding=pad_sym(horizontal=14, vertical=8),
                content=ft.Row(
                    spacing=12,
                    controls=[
                        ft.Container(width=34, height=34, border_radius=10, bgcolor="#EFF6FF", alignment=CENTER, content=ft.Icon(ft.Icons.HISTORY, size=17, color=PRIMARY)),
                        ft.Column(
                            expand=True,
                            spacing=2,
                            controls=[
                                ft.Text(entry.get("action", "Activity"), size=13, weight=ft.FontWeight.W_800, color=TEXT),
                                ft.Text(entry.get("message", ""), size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        ft.Text(entry.get("time", ""), size=11, color=MUTED_2),
                    ],
                ),
            )

        def snapshot_row(snapshot):
            def restore(_event):
                try:
                    restored_tasks, _restored_templates = restore_snapshot(snapshot.get("path", ""))
                except Exception as exc:
                    show_message(page, "Restore failed", str(exc))
                    return
                all_tasks.clear()
                all_tasks.extend(restored_tasks)
                render_current()
                show_message(page, "Snapshot", "Snapshot restored.")

            def open_snapshot_folder(_event):
                path = Path(snapshot.get("path", ""))
                if path.exists():
                    os.startfile(str(path.parent))

            return ft.Container(
                height=44,
                border=border_all(1, BORDER),
                border_radius=12,
                bgcolor="#F8FAFC",
                padding=pad_sym(horizontal=12, vertical=6),
                content=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.BACKUP_OUTLINED, size=16, color=MUTED),
                        ft.Column(
                            expand=True,
                            spacing=1,
                            controls=[
                                ft.Text(snapshot.get("reason", "Snapshot"), size=12, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(snapshot.get("time", ""), size=10, color=MUTED_2),
                            ],
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            icon_size=16,
                            icon_color=MUTED_2,
                            items=[
                                ft.PopupMenuItem(content="Restore snapshot", icon=ft.Icons.RESTORE, on_click=restore),
                                ft.PopupMenuItem(content="Open folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=open_snapshot_folder),
                            ],
                        ),
                    ],
                ),
            )

        def health_check_tile(check):
            ok = bool(check.get("ok"))
            color = "#16A34A" if ok else "#DC2626"
            bg = "#F0FDF4" if ok else "#FEF2F2"
            return ft.Container(
                expand=True,
                height=82,
                bgcolor=bg,
                border=border_all(1, "#BBF7D0" if ok else "#FECACA"),
                border_radius=14,
                padding=14,
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=38, height=38, border_radius=10, bgcolor=WHITE, border=border_all(1, "#BBF7D0" if ok else "#FECACA"), alignment=CENTER, content=ft.Icon(check.get("icon", ft.Icons.CHECK_CIRCLE_OUTLINE), size=20, color=color)),
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Row(spacing=6, controls=[ft.Text(check.get("label", "Check"), size=13, weight=ft.FontWeight.W_900, color=TEXT), ft.Icon(ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR_OUTLINE, size=15, color=color)]),
                                ft.Text(check.get("detail", ""), size=11, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                    ],
                ),
            )

        health_check_card = ft.Container(
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=18,
            padding=18,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.MONITOR_HEART_OUTLINED, color=PRIMARY), ft.Text("Health Check", size=22, weight=ft.FontWeight.W_900, color=TEXT)]),
                            ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#EFF6FF", border=border_all(1, "#BFDBFE"), content=ft.Text(f"{health_ok_count}/{len(health_checks)} checks OK", size=12, weight=ft.FontWeight.W_900, color=PRIMARY)),
                        ],
                    ),
                    ft.Row(spacing=12, controls=[health_check_tile(check) for check in health_checks[:3]]),
                    ft.Row(spacing=12, controls=[health_check_tile(check) for check in health_checks[3:]]),
                ],
            ),
        )

        def health_filter_button(label, count):
            active = health_filter == label
            return ft.Container(
                on_click=lambda _e, value=label: (state.update({"health_filter": value}), render_current()),
                padding=pad_sym(horizontal=12, vertical=8),
                border_radius=999,
                bgcolor=PRIMARY if active else "#F8FAFC",
                border=border_all(1, "#1D4ED8" if active else "#CBD5E1"),
                content=ft.Row(
                    spacing=7,
                    controls=[
                        ft.Text(label, size=12, weight=ft.FontWeight.W_900, color=WHITE if active else TEXT),
                        ft.Container(width=28, height=20, border_radius=999, bgcolor=WHITE if active else "#EEF2FF", alignment=CENTER, content=ft.Text(str(count), size=10, weight=ft.FontWeight.W_900, color=PRIMARY if active else MUTED)),
                    ],
                ),
            )

        issue_card = ft.Container(
            expand=2,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=18,
            padding=22,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.LINK_OFF_OUTLINED, color="#DC2626"), ft.Text("Broken Link Center", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Button("Scan now", icon=ft.Icons.SYNC, on_click=sync_now, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                        ],
                    ),
                    ft.Text("Scans task and template records for missing local targets, empty targets, and missing URL shortcuts. Work files are not changed by this scan.", size=13, color=MUTED),
                    ft.Row(
                        spacing=8,
                        wrap=True,
                        controls=[
                            health_filter_button("All", len(problems)),
                            health_filter_button("Tasks", len(broken_tasks)),
                            health_filter_button("Templates", len(broken_templates)),
                            health_filter_button("Missing", sum(1 for problem in problems if problem.get("reason") == "Missing file/folder")),
                            health_filter_button("No target", sum(1 for problem in problems if problem.get("reason") == "No target")),
                            health_filter_button("URL shortcut", sum(1 for problem in problems if problem.get("reason") == "Missing URL shortcut")),
                        ],
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            expand=True,
                            spacing=10,
                            controls=[issue_row(problem) for problem in visible_problems] if visible_problems else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No broken items found for this filter", size=15, color=MUTED_2))],
                        ),
                    ),
                ],
            ),
        )

        activity_card = ft.Container(
            expand=1,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=18,
            padding=22,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.HISTORY, color=MUTED), ft.Text("Activity", size=22, weight=ft.FontWeight.W_800, color=TEXT)]), ft.Button("Undo", icon=ft.Icons.UNDO, on_click=undo_last, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12)))]),
                    ft.Container(padding=pad_sym(horizontal=12, vertical=10), border_radius=14, bgcolor="#F8FAFC", content=ft.Text("Undo restores the latest tracked rename/move/edit when possible.", size=12, color=MUTED)),
                    ft.Column(spacing=8, controls=[ft.Text("Recent snapshots", size=13, weight=ft.FontWeight.W_800, color=TEXT), *([snapshot_row(snapshot) for snapshot in snapshots] if snapshots else [ft.Text("No snapshots yet", size=12, color=MUTED_2)])]),
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            expand=True,
                            spacing=10,
                            controls=[activity_row(entry) for entry in activity] if activity else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No activity yet", size=15, color=MUTED_2))],
                        ),
                    ),
                ],
            ),
        )

        main_body.controls = [health_check_card] + ([smart_overview] if smart_health_on else []) + [ft.Row(spacing=18, expand=True, controls=[issue_card, activity_card])]
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
<h1>SA CHECK Report</h1><div class="muted">Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Developer: HOYTURBRO</div>
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
                                ft.Text("Developer / Creator: HOYTURBRO", size=14, weight=ft.FontWeight.W_900, color=TEXT, selectable=True),
                                ft.Text("Alias: Hoyturbro", size=13, color=MUTED, selectable=True),
                                ft.Text("Publisher: HOYTURBRO", size=13, color=MUTED, selectable=True),
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
                    expected_total = remote_file_size(url)
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

        def guide_header(icon, title, subtitle, color=PRIMARY):
            return ft.Container(
                data="guide_header",
                border=border_all(1, "#DBEAFE"),
                border_radius=16,
                bgcolor="#F8FBFF",
                padding=pad_sym(horizontal=14, vertical=12),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=42, height=42, border_radius=14, bgcolor=color + "16", alignment=CENTER, content=ft.Icon(icon, color=color, size=23)),
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(title, size=16, weight=ft.FontWeight.W_900, color=TEXT),
                                ft.Text(subtitle, size=12, color=MUTED),
                            ],
                        ),
                    ],
                ),
            )

        def step(icon, title, body, color=PRIMARY):
            return ft.Container(
                data="guide_step",
                border=border_all(1, BORDER),
                border_radius=14,
                bgcolor=WHITE,
                padding=pad_sym(horizontal=13, vertical=11),
                content=ft.Row(
                    spacing=11,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(width=34, height=34, border_radius=12, bgcolor=color + "14", alignment=CENTER, content=ft.Icon(icon, color=color, size=19)),
                        ft.Column(
                            spacing=4,
                            expand=True,
                            controls=[
                                ft.Text(title, size=13, weight=ft.FontWeight.W_900, color=TEXT),
                                ft.Text(body, size=12, color=MUTED, selectable=True),
                            ],
                        ),
                    ],
                ),
            )

        sections = [
            guide_header(ft.Icons.FOLDER_SPECIAL_OUTLINED, "1. เริ่มต้นเลือกคลังงาน", "ติดตั้งใหม่จะยังไม่ผูกกับ Work เก่า ให้เลือกหรือสร้างโฟลเดอร์งานเอง"),
            step(ft.Icons.SETTINGS_OUTLINED, "เลือก Work folder", "ไปที่ Settings > Work Folder Source > Choose Work folder แล้วเลือก Work1, Work2 หรือโฟลเดอร์งานของทีม", "#2563EB"),
            step(ft.Icons.CREATE_NEW_FOLDER_OUTLINED, "สร้างโฟลเดอร์เก็บงานใหม่", "ถ้ายังไม่มีคลังงาน ให้สร้างโฟลเดอร์ใหม่ เช่น Documents\\SA CHECK Work\\Work แล้วเลือกโฟลเดอร์นั้นเป็น Work folder", "#0F766E"),
            step(ft.Icons.SYNC, "Sync งานเข้าระบบ", "กด Sync now เพื่อให้แอพอ่านโฟลเดอร์ Waiting, Doing, Success และไฟล์ในคลังงานขึ้นมาบนบอร์ด", "#7C3AED"),

            guide_header(ft.Icons.ADD_TASK_OUTLINED, "2. วิธีเพิ่มงาน", "เพิ่มได้ทั้งไฟล์ โฟลเดอร์โปรเจค ลิงก์ เทมเพลต และงานใหม่จากในแอพ"),
            step(ft.Icons.UPLOAD_FILE_OUTLINED, "Add file", "กด + Quick Add > Add file แล้วเลือกไฟล์ เช่น Word, Excel, PDF แอพจะคัดลอกเข้า Waiting ให้ปลอดภัย", "#DC2626"),
            step(ft.Icons.FOLDER_OUTLINED, "Create project / Add project folder", "ใช้กับงานที่เป็นโฟลเดอร์ทั้งชุด เช่น Web, Project, Design แอพจะคัดลอกโฟลเดอร์เข้า Waiting และไม่ทับของเดิม", "#7C3AED"),
            step(ft.Icons.LINK_ROUNDED, "Add link", "ใช้เก็บ URL เช่น Google Sheet, Miro, Web หรือระบบภายใน แอพจะสร้าง shortcut .url ให้ใน Work folder", "#0891B2"),
            step(ft.Icons.NOTE_ADD_OUTLINED, "Create new work", "สร้างงานเปล่าจากชนิดไฟล์ที่ตั้งไว้ เช่น Word/Excel/Text แล้วให้แอพวางไว้ใน Waiting", "#0F766E"),
            step(ft.Icons.ARTICLE_OUTLINED, "Templates", "เก็บไฟล์ต้นแบบไว้หน้า Templates แล้วกดใช้ซ้ำเพื่อสร้างงานใหม่เข้า Waiting ได้เร็ว", "#D97706"),

            guide_header(ft.Icons.DASHBOARD_ROUNDED, "3. ใช้งานบอร์ดและสถานะ", "บอร์ดหลักช่วยดูงาน Waiting, Doing, Success และเลื่อนสถานะได้"),
            step(ft.Icons.PLAY_CIRCLE_OUTLINE, "ย้ายสถานะ", "เปิดเมนูของงาน หรือเข้า Detail แล้วเลือก Move to Waiting / Doing / Success ไฟล์จะถูกย้ายโฟลเดอร์ตามสถานะ", "#D97706"),
            step(ft.Icons.INFO_OUTLINE, "ดูรายละเอียด", "กด Detail เพื่อแก้ชื่อ, ชนิดงาน, วันที่, note, เปิดไฟล์, เปิดโฟลเดอร์ หรือคัดลอก path", "#2563EB"),
            step(ft.Icons.SEARCH, "ค้นหาและกรอง", "ช่อง Search ใช้ค้นชื่อไฟล์ note path ประเภทงาน และสถานะ ช่วยหาไฟล์ในคลังงานเร็วขึ้น", "#0F766E"),

            guide_header(ft.Icons.EVENT_OUTLINED, "4. Calendar, Health และความปลอดภัย", "ใช้ช่วยตามงาน ตรวจไฟล์หาย และย้อนการแก้ไข"),
            step(ft.Icons.CALENDAR_TODAY_OUTLINED, "Calendar", "เพิ่ม Calendar event จาก + Quick Add หรือแก้วันที่ใน Detail เพื่อใช้เตือนงานตามวัน", "#7C3AED"),
            step(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "Health", "หน้า Health ช่วยดูไฟล์ที่ path หาย, duplicate, snapshot และ activity ล่าสุด", "#16A34A"),
            step(ft.Icons.UNDO, "Undo / Snapshot", "ระบบเก็บ undo และ snapshot บางจังหวะ เช่น ก่อนเปลี่ยน Work folder หรือแก้รายการสำคัญ เพื่อช่วยย้อนกลับ", "#D97706"),

            guide_header(ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, "5. ติดตั้ง อัปเดต ถอนการติดตั้ง", "ออกแบบให้กด installer ทับเพื่ออัปเดตระบบได้"),
            step(ft.Icons.INSTALL_DESKTOP_OUTLINED, "ติดตั้ง", "รัน SA_CHECK_Installer.exe แล้วระบบจะติดตั้งตัวแอพไว้ที่ C:\\SACHECK และสร้าง shortcut ให้", "#2563EB"),
            step(ft.Icons.UPDATE, "อัปเดต", "ถ้ามี installer เวอร์ชันใหม่ ให้กดติดตั้งทับที่ C:\\SACHECK ได้เลย โค้ด/คู่มือจะอัปเดต แต่ Work folder ที่เลือกไว้จะไม่โดนลบ", "#0F766E"),
            step(ft.Icons.DELETE_OUTLINE, "Uninstall", "ถอนการติดตั้งจะลบเฉพาะไฟล์ระบบแอพใน C:\\SACHECK ไม่ลบ Work1/Work2 หรือโฟลเดอร์งานที่ผู้ใช้เลือกไว้", "#DC2626"),
            step(ft.Icons.VERIFIED_USER_OUTLINED, "Credits", "Developer / Creator: HOYTURBRO | Alias: Hoyturbro | Publisher: HOYTURBRO", "#0F766E"),
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

        guide_controls = [
            ft.Container(
                border=border_all(1, "#E2E8F0"),
                border_radius=18,
                bgcolor="#F8FAFC",
                padding=12,
                content=ft.Column(spacing=10, controls=group),
            )
            for group in guide_groups
        ]

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
    calendar_events = settings.setdefault("calendar_events", [])
    if not isinstance(calendar_events, list):
        calendar_events = []
        settings["calendar_events"] = calendar_events
    settings.setdefault("calendar_event_alerts", {})

    def save_calendar_events():
        settings["calendar_events"] = calendar_events
        settings.setdefault("calendar_event_alerts", {})
        save_settings(settings)

    def event_date_value(event):
        try:
            return datetime.strptime(str(event.get("date", ""))[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def events_for_day(day):
        return [event for event in calendar_events if event_date_value(event) == day]

    def event_style(event):
        color = event.get("color") or "#7C3AED"
        bg_map = {
            "#2563EB": "#EFF6FF",
            "#D97706": "#FFFBEB",
            "#16A34A": "#F0FDF4",
            "#7C3AED": "#F5F3FF",
            "#DC2626": "#FEF2F2",
            "#0891B2": "#ECFEFF",
            "#DB2777": "#FDF2F8",
            "#0F766E": "#F0FDFA",
            "#EA580C": "#FFF7ED",
            "#A855F7": "#FAF5FF",
            "#14B8A6": "#F0FDFA",
            "#6366F1": "#EEF2FF",
            "#0284C7": "#F0F9FF",
            "#65A30D": "#F7FEE7",
            "#CA8A04": "#FEFCE8",
            "#E11D48": "#FFF1F2",
            "#C026D3": "#FDF4FF",
            "#9333EA": "#FAF5FF",
            "#475569": "#F8FAFC",
            "#111827": "#F8FAFC",
            "#22C55E": "#F0FDF4",
            "#06B6D4": "#ECFEFF",
            "#F59E0B": "#FFFBEB",
            "#EF4444": "#FEF2F2",
            "#EC4899": "#FDF2F8",
        }
        bg = bg_map.get(color, "#F8FAFC")
        return color, bg

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
        time_options = [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)]
        initial_time_value = f"{picker_state['hour']:02d}:{(30 if picker_state['minute'] >= 30 else 0):02d}"
        picker_state["hour"], picker_state["minute"] = [int(part) for part in initial_time_value.split(":", 1)]
        date_field = ft.TextField(
            label="Selected date",
            value=picker_state["date"].isoformat(),
            height=50,
            read_only=True,
            border_radius=14,
            border_color=BORDER,
            focused_border_color=PRIMARY,
            prefix_icon=ft.Icons.EVENT_OUTLINED,
            suffix=ft.IconButton(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, icon_size=18, tooltip="Open calendar"),
        )
        time_field = dropdown(180, initial_time_value, time_options, menu_height=220)
        kind_field = dropdown(190, source.get("kind", "Event"), ["Event", "Holiday", "Meeting", "Deadline", "Note"])
        selected_color = {"value": source.get("color", "#7C3AED")}
        color_preview = ft.Container(width=34, height=34, border_radius=12, bgcolor=selected_color["value"], border=border_all(1, BORDER))
        notify_switch = ft.Switch(label="Daily summary at 09:00", value=bool(source.get("notify", True)))
        alarm_switch = ft.Switch(label="Alarm again at event time", value=bool(source.get("alarm", True)))
        note_field = ft.TextField(label="Note", value=source.get("note", ""), multiline=True, min_lines=2, max_lines=2, border_radius=12, border_color=BORDER)
        color_choices = [
            "#7C3AED", "#6366F1", "#2563EB", "#0284C7", "#0891B2", "#0F766E",
            "#16A34A", "#65A30D", "#CA8A04", "#D97706", "#EA580C", "#DC2626",
            "#E11D48", "#DB2777", "#C026D3", "#9333EA", "#475569", "#111827",
            "#22C55E", "#06B6D4", "#F59E0B", "#EF4444", "#EC4899", "#14B8A6",
        ]

        def update_picker_fields():
            date_field.value = picker_state["date"].isoformat()
            time_field.value = f"{picker_state['hour']:02d}:{picker_state['minute']:02d}"
            page.update()

        def set_time_from_dropdown(event):
            value = event.control.value or "09:00"
            hour, minute = [int(part) for part in value.split(":", 1)]
            picker_state["hour"] = hour
            picker_state["minute"] = minute
            update_picker_fields()

        time_field.on_select = set_time_from_dropdown

        def on_date_change(event):
            picked = event.control.value or event.data
            if isinstance(picked, datetime):
                picker_state["date"] = picked.date()
            elif isinstance(picked, date):
                picker_state["date"] = picked
            else:
                try:
                    picker_state["date"] = datetime.strptime(str(picked)[:10], "%Y-%m-%d").date()
                except ValueError:
                    return
            update_picker_fields()

        def open_date_picker(_event=None):
            page.show_dialog(
                ft.DatePicker(
                    value=datetime.combine(picker_state["date"], datetime.min.time()),
                    current_date=datetime.now(),
                    first_date=datetime(2000, 1, 1),
                    last_date=datetime(2050, 12, 31),
                    help_text="Select event date",
                    cancel_text="Cancel",
                    confirm_text="Apply",
                    on_change=on_date_change,
                )
            )

        date_field.suffix.on_click = open_date_picker
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
            update_picker_fields()
            parsed = picker_state["date"].isoformat()
            event_time = f"{picker_state['hour']:02d}:{picker_state['minute']:02d}"
            event_id = source.get("id") or str(uuid.uuid4())
            payload = {
                "id": event_id,
                "title": title,
                "date": parsed,
                "time": event_time,
                "kind": kind_field.value or "Event",
                "color": selected_color["value"] or "#7C3AED",
                "notify": bool(notify_switch.value),
                "alarm": bool(alarm_switch.value),
                "note": note_field.value or "",
                "created_at": source.get("created_at") or datetime.now().isoformat(timespec="seconds"),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            clear_event_alert_keys(event_id)
            if editing:
                source.clear()
                source.update(payload)
            else:
                calendar_events.append(payload)
            save_calendar_events()
            page.pop_dialog()
            render_current()
            show_message(page, "Calendar event", "Event saved.")

        def delete_event(_event):
            if editing and source in calendar_events:
                calendar_events.remove(source)
                save_calendar_events()
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
                    height=425,
                    spacing=10,
                    controls=[
                        title_field,
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
                                            ft.Container(expand=True, on_click=open_date_picker, content=date_field),
                                            time_field,
                                            kind_field,
                                        ],
                                    ),
                                    ft.Text("Date uses the standard calendar popup. Time uses a fixed 24-hour dropdown.", size=10, color=MUTED),
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
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[notify_switch, alarm_switch],
                        ),
                        note_field,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.TextButton("Delete", on_click=delete_event, visible=editing, style=ft.ButtonStyle(color="#DC2626")),
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                                        ft.Button("Save event", icon=ft.Icons.SAVE_OUTLINED, on_click=save_event, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def show_event_detail_dialog(event):
        color, bg = event_style(event)
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

    def render_calendar():
        header_title.value = "Calendar"
        header_subtitle.value = f"{APP_NAME} / Work Schedule"

        status_filter = calendar_state.get("status", "All")
        calendar_items = []
        grouped_by_day = {}
        all_grouped_by_day = {}
        events_by_day = {}
        for event in calendar_events:
            event_day = event_date_value(event)
            if event_day:
                events_by_day.setdefault(event_day, []).append(event)
        for task in all_tasks:
            try:
                parsed = datetime.strptime(task_day(task), "%Y-%m-%d").date()
            except ValueError:
                continue
            calendar_items.append((parsed, task))
            all_grouped_by_day.setdefault(parsed, []).append(task)
            if status_filter == "All" or task.get("status") == status_filter:
                grouped_by_day.setdefault(parsed, []).append(task)

        filtered_count = sum(len(items) for items in grouped_by_day.values())
        total_count = len(calendar_items)
        event_count = len(calendar_events)
        status_counts = {
            "All": total_count,
            STATUS_PENDING: sum(1 for _day, item in calendar_items if item.get("status") == STATUS_PENDING),
            STATUS_PROGRESS: sum(1 for _day, item in calendar_items if item.get("status") == STATUS_PROGRESS),
            STATUS_DONE: sum(1 for _day, item in calendar_items if item.get("status") == STATUS_DONE),
        }

        today = date.today()
        selected_day = calendar_state["selected"]
        year = calendar_state["year"]
        month = calendar_state["month"]
        progress_badge.value = f"{filtered_count}/{total_count} work + {event_count} events" if status_filter != "All" else f"{total_count} work + {event_count} events"
        month_label = ft.Text(f"{calendar.month_name[month]} {year}", size=24, weight=ft.FontWeight.W_800, color=TEXT)

        thai_holidays = {
            (1, 1): "New Year",
            (4, 6): "Chakri Day",
            (4, 13): "Songkran",
            (4, 14): "Songkran",
            (4, 15): "Songkran",
            (5, 1): "Labour Day",
            (5, 4): "Coronation Day",
            (6, 3): "Queen Suthida Birthday",
            (7, 28): "King Vajiralongkorn Birthday",
            (8, 12): "Mother's Day",
            (10, 13): "King Bhumibol Memorial Day",
            (10, 23): "Chulalongkorn Day",
            (12, 5): "Father's Day",
            (12, 10): "Constitution Day",
            (12, 31): "New Year's Eve",
        }

        def calendar_day_info(day):
            notes = []
            if day.weekday() == 5:
                notes.append(("SAT", "Weekend", "#BE185D", "#FDF2FA"))
            elif day.weekday() == 6:
                notes.append(("SUN", "Weekend", "#DC2626", "#FFF1F2"))
            holiday_name = thai_holidays.get((day.month, day.day))
            if holiday_name:
                notes.append(("HOL", holiday_name, "#7C3AED", "#F5F3FF"))
            return notes

        def refresh_calendar():
            state["screen"] = SCREEN_CALENDAR
            render_current()

        def shift_month(delta):
            next_month = calendar_state["month"] + delta
            next_year = calendar_state["year"]
            if next_month < 1:
                next_month = 12
                next_year -= 1
            elif next_month > 12:
                next_month = 1
                next_year += 1
            calendar_state.update({"year": next_year, "month": next_month, "selected": date(next_year, next_month, 1)})
            refresh_calendar()

        def select_day(day):
            calendar_state["selected"] = day
            calendar_state["year"] = day.year
            calendar_state["month"] = day.month
            refresh_calendar()

        def set_calendar_status(status_value):
            calendar_state["status"] = status_value
            refresh_calendar()

        def status_chip(label, status_value, color, bg):
            selected = status_filter == status_value
            return ft.Container(
                height=44,
                padding=pad_sym(horizontal=14),
                border_radius=14,
                bgcolor=bg if selected else WHITE,
                border=border_all(1.5 if selected else 1, color if selected else BORDER),
                on_click=lambda _e, value=status_value: set_calendar_status(value),
                content=ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=9, height=9, border_radius=999, bgcolor=color),
                        ft.Text(label, size=12, weight=ft.FontWeight.W_800, color=TEXT),
                        ft.Container(
                            padding=pad_sym(horizontal=8, vertical=3),
                            border_radius=999,
                            bgcolor="#F8FAFC" if selected else "#EEF2F7",
                            content=ft.Text(str(status_counts.get(status_value, 0)), size=11, weight=ft.FontWeight.W_800, color=color),
                        ),
                    ],
                ),
            )

        def task_chip(task):
            status = task.get("status")
            color = WAITING_TEXT if status == STATUS_PENDING else DOING_TEXT if status == STATUS_PROGRESS else DONE_TEXT
            bg = WHITE if status == STATUS_PENDING else "#FFF7ED" if status == STATUS_PROGRESS else "#DCFCE7"
            icon, icon_color = task_icon(task.get("type", "Other"))
            return ft.PopupMenuButton(
                content=ft.Container(
                    height=21,
                    border_radius=8,
                    bgcolor=bg,
                    border=border_all(1, "#E2E8F0"),
                    padding=pad_sym(horizontal=6),
                    content=ft.Row(
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(icon, size=10, color=icon_color),
                            ft.Text(task.get("name", "Untitled task"), size=10, weight=ft.FontWeight.W_700, color=color, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                        ],
                    ),
                ),
                items=calendar_task_menu(task, refresh_calendar),
            )

        def event_chip(event):
            color, bg = event_style(event)
            return ft.Container(
                height=21,
                border_radius=8,
                bgcolor=bg,
                border=border_all(1, color + "55"),
                padding=pad_sym(horizontal=6),
                on_click=lambda _e, item=event: show_event_detail_dialog(item),
                content=ft.Row(
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CELEBRATION_OUTLINED, size=10, color=color),
                        ft.Text(f"{event.get('time', '09:00')} {event.get('title', 'Event')}", size=10, weight=ft.FontWeight.W_800, color=color, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ],
                ),
            )

        def day_cell(day):
            weekday_palette = [
                ("#EEF4FF", "#BFD4FF"),
                ("#EAFBFF", "#A7E6F0"),
                ("#ECFDF3", "#A7E3B8"),
                ("#FFFAE6", "#F4D783"),
                ("#FFF2E6", "#F0C29B"),
                ("#FDF2FA", "#E7A8D4"),
                ("#FFF1F2", "#E9A4A8"),
            ]
            is_current_month = day.month == month
            is_selected = day == selected_day
            is_today = day == today
            raw_day_tasks = sorted(all_grouped_by_day.get(day, []), key=lambda item: (item.get("status", ""), item.get("name", "")))
            day_tasks = sorted(grouped_by_day.get(day, []), key=lambda item: (item.get("status", ""), item.get("name", "")))
            day_events = sorted(events_by_day.get(day, []), key=lambda item: item.get("title", ""))
            waiting_count = sum(1 for item in raw_day_tasks if item.get("status") == STATUS_PENDING)
            doing_count = sum(1 for item in raw_day_tasks if item.get("status") == STATUS_PROGRESS)
            done_count = sum(1 for item in raw_day_tasks if item.get("status") == STATUS_DONE)
            visible_events = day_events[:1]
            visible_tasks = day_tasks[: max(0, 2 - len(visible_events))]
            weekday_bg, weekday_border = weekday_palette[day.weekday()]
            day_notes = calendar_day_info(day)
            cell_bg = "#DBEAFE" if is_today else (weekday_bg if is_current_month else "#F8FAFC")
            cell_border = PRIMARY if is_selected else (weekday_border if is_current_month else BORDER)
            return ft.Container(
                expand=True,
                height=90,
                bgcolor=cell_bg,
                border=border_all(3 if is_today else (2 if is_selected else 1), PRIMARY if is_today else cell_border),
                border_radius=14,
                padding=8,
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=14, color="#302563EB", offset=ft.Offset(0, 5)) if is_today else (ft.BoxShadow(spread_radius=0, blur_radius=8, color="#10000000", offset=ft.Offset(0, 3)) if is_current_month else None),
                on_click=lambda _e, value=day: select_day(value),
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=5,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Container(
                                            width=24,
                                            height=24,
                                            border_radius=999,
                                            bgcolor=PRIMARY if is_today else None,
                                            alignment=CENTER,
                                            content=ft.Text(str(day.day), size=13 if is_today else 12, weight=ft.FontWeight.W_900 if is_today else ft.FontWeight.W_800, color=WHITE if is_today else (TEXT if is_current_month else MUTED_2)),
                                        ),
                                        ft.Container(
                                            height=18,
                                            padding=pad_sym(horizontal=6),
                                            border_radius=999,
                                            bgcolor="#172554",
                                            alignment=CENTER,
                                            content=ft.Text("TODAY", size=8, weight=ft.FontWeight.W_900, color=WHITE),
                                        ) if is_today else ft.Container(width=0, height=0),
                                    ],
                                ),
                                ft.Text(f"W{waiting_count} D{doing_count} S{done_count}" if raw_day_tasks else "", size=9, color=MUTED_2),
                            ],
                        ),
                        *[event_chip(event) for event in visible_events],
                        *[task_chip(task) for task in visible_tasks],
                        ft.Container(
                            height=15,
                            border_radius=999,
                            bgcolor="#F1F5F9",
                            alignment=CENTER,
                            content=ft.Text(f"+{(len(day_tasks) - len(visible_tasks)) + (len(day_events) - len(visible_events))}", size=9, weight=ft.FontWeight.W_700, color=MUTED),
                        ) if (len(day_tasks) > len(visible_tasks) or len(day_events) > len(visible_events)) else ft.Container(height=0),
                        ft.Row(
                            spacing=4,
                            controls=[
                                ft.Container(
                                    height=13,
                                    padding=pad_sym(horizontal=5),
                                    border_radius=999,
                                    bgcolor=note_bg,
                                    content=ft.Text(code, size=8, weight=ft.FontWeight.W_900, color=note_color),
                                )
                                for code, _title, note_color, note_bg in day_notes[:2]
                            ],
                        ) if day_notes else ft.Container(height=0),
                    ],
                ),
            )

        first_day = date(year, month, 1)
        start_day = first_day - timedelta(days=first_day.weekday())
        weekday_row = ft.Row(
            spacing=6,
            controls=[ft.Container(expand=True, alignment=CENTER, content=ft.Text(label, size=12, weight=ft.FontWeight.W_800, color=MUTED)) for label in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]],
        )
        week_rows = []
        for week_index in range(6):
            week_start = start_day + timedelta(days=week_index * 7)
            week_rows.append(ft.Row(spacing=6, controls=[day_cell(week_start + timedelta(days=offset)) for offset in range(7)]))

        selected_tasks = sorted(grouped_by_day.get(selected_day, []), key=lambda item: (item.get("status", ""), item.get("name", "")))
        selected_events = sorted(events_by_day.get(selected_day, []), key=lambda item: item.get("title", ""))
        selected_day_notes = calendar_day_info(selected_day)

        def selected_task_row(task):
            icon, icon_color = task_icon(task.get("type", "Other"))
            status = STATUS_LABELS.get(task.get("status"), "Waiting")
            status_bg = WAITING_BG if task.get("status") == STATUS_PENDING else DOING_BG if task.get("status") == STATUS_PROGRESS else DONE_BG
            status_color = WAITING_TEXT if task.get("status") == STATUS_PENDING else DOING_TEXT if task.get("status") == STATUS_PROGRESS else DONE_TEXT
            return ft.Container(
                height=68,
                bgcolor=WHITE,
                border=border_all(1, BORDER),
                border_radius=14,
                padding=pad_only(left=12, right=4),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=38, height=38, border_radius=11, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=19, color=icon_color)),
                        ft.Column(
                            spacing=3,
                            expand=True,
                            controls=[
                                ft.Text(task.get("name", "Untitled task"), size=14, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Row(
                                    spacing=6,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Text(task.get("type", "Other"), size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Container(
                                            padding=pad_sym(horizontal=7, vertical=3),
                                            border_radius=7,
                                            bgcolor=status_bg,
                                            content=ft.Text(status, size=11, weight=ft.FontWeight.W_800, color=status_color),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, icon_size=18, icon_color=MUTED_2, items=calendar_task_menu(task, refresh_calendar)),
                    ],
                ),
            )

        def selected_event_row(event):
            color, bg = event_style(event)
            note_preview = event.get("note") or "No note yet."
            event_time = event.get("time", "09:00")
            return ft.Container(
                height=116,
                bgcolor=bg,
                border=border_all(1, color + "55"),
                border_radius=14,
                padding=pad_only(left=12, right=4, top=10, bottom=10),
                on_click=lambda _e, item=event: show_event_detail_dialog(item),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(width=38, height=38, border_radius=11, bgcolor=WHITE, alignment=CENTER, content=ft.Icon(ft.Icons.CELEBRATION_OUTLINED, size=19, color=color)),
                        ft.Column(
                            spacing=4,
                            expand=True,
                            controls=[
                                ft.Text(event.get("title", "Event"), size=14, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"{event.get('kind', 'Event')} | {event_time} | {'09:00 + alarm' if event.get('notify', True) and event.get('alarm', True) else '09:00 summary' if event.get('notify', True) else 'alarm only' if event.get('alarm', True) else 'no alert'}", size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(note_preview, size=12, color=MUTED, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
                        ft.PopupMenuButton(
                            icon=ft.Icons.MORE_VERT,
                            icon_size=18,
                            icon_color=MUTED_2,
                            items=[
                                ft.PopupMenuItem(content="Details", icon=ft.Icons.INFO_OUTLINE, on_click=lambda _e, item=event: show_event_detail_dialog(item)),
                                ft.PopupMenuItem(content="Edit event", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda _e, item=event: show_calendar_event_dialog(item)),
                                ft.PopupMenuItem(content="Copy note", icon=ft.Icons.CONTENT_COPY, on_click=lambda _e, item=event: (page.clipboard.set(item.get("note", "")), show_message(page, "Copied", "Event note copied."))),
                            ],
                        ),
                    ],
                ),
            )

        calendar_panel = ft.Container(
            expand=True,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=22,
            padding=14,
            content=ft.Column(spacing=6, controls=[weekday_row, *week_rows]),
        )
        detail_panel = ft.Container(
            width=360,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=22,
            padding=20,
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=3,
                                controls=[
                                    ft.Text(selected_day.strftime("%A"), size=13, weight=ft.FontWeight.W_800, color=MUTED),
                                    ft.Text(selected_day.strftime("%d %B %Y"), size=20, weight=ft.FontWeight.W_800, color=TEXT),
                                    ft.Text(f"{len(selected_tasks)} work / {len(selected_events)} events", size=11, weight=ft.FontWeight.W_700, color=MUTED_2),
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Container(
                                                padding=pad_sym(horizontal=8, vertical=4),
                                                border_radius=999,
                                                bgcolor=note_bg,
                                                content=ft.Text(title, size=10, weight=ft.FontWeight.W_800, color=note_color),
                                            )
                                            for _code, title, note_color, note_bg in selected_day_notes
                                        ],
                                    ) if selected_day_notes else ft.Text("Regular workday", size=11, weight=ft.FontWeight.W_700, color=MUTED_2),
                                ],
                            ),
                            ft.Container(padding=pad_sym(horizontal=10, vertical=5), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(str(len(selected_tasks) + len(selected_events)), size=13, weight=ft.FontWeight.W_800, color=PRIMARY)),
                        ],
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            expand=True,
                            spacing=10,
                            controls=[
                                *([ft.Text("Events", size=12, weight=ft.FontWeight.W_900, color=MUTED)] if selected_events else []),
                                *[selected_event_row(event) for event in selected_events],
                                *([ft.Text("Work", size=12, weight=ft.FontWeight.W_900, color=MUTED)] if selected_tasks else []),
                                *[selected_task_row(task) for task in selected_tasks],
                            ] if selected_tasks or selected_events else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No work or events on this day", size=14, color=MUTED_2))],
                        ),
                    ),
                ],
            ),
        )
        toolbar = ft.Container(
            height=58,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=18,
            padding=pad_sym(horizontal=18, vertical=6),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[month_label]),
                    ft.Row(
                        spacing=6,
                        controls=[
                            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Previous month", on_click=lambda _e: shift_month(-1)),
                            ft.Button("Today", icon=ft.Icons.TODAY_OUTLINED, on_click=lambda _e: (calendar_state.update({"year": today.year, "month": today.month, "selected": today}), refresh_calendar())),
                            ft.Button("Add Event", icon=ft.Icons.ADD_ALERT_OUTLINED, on_click=lambda _e: show_calendar_event_dialog(selected_date=selected_day), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Next month", on_click=lambda _e: shift_month(1)),
                        ],
                    ),
                ],
            ),
        )
        status_overview = ft.Container(
            height=54,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=18,
            padding=pad_sym(horizontal=18, vertical=5),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Status", size=12, weight=ft.FontWeight.W_900, color=MUTED),
                    status_chip("All work", "All", PRIMARY, "#EFF6FF"),
                    status_chip("Waiting", STATUS_PENDING, WAITING_TEXT, WAITING_BG),
                    status_chip("Doing", STATUS_PROGRESS, DOING_TEXT, DOING_BG),
                    status_chip("Success", STATUS_DONE, DONE_TEXT, DONE_BG),
                    ft.Container(expand=True),
                    ft.Text("Click a status to verify every job by day.", size=11, color=MUTED_2),
                ],
            ),
        )
        main_body.controls = [toolbar, status_overview, ft.Row(spacing=18, expand=True, controls=[calendar_panel, detail_panel])]
        page.update()

    def show_calendar(_e=None):
        state["screen"] = SCREEN_CALENDAR
        render_current()

    def on_search(event):
        state["search"] = event.control.value or ""
        state["group_limits"] = {}
        render_current()

    search_field.on_change = on_search

    def build_sidebar_controls():
        online_state = state.get("online_status", "checking")
        status_color = "#16A34A" if online_state == "online" else "#D97706" if online_state == "checking" else "#DC2626"
        status_text = "Online" if online_state == "online" else "Check" if online_state == "checking" else "Offline"
        online_enabled = not settings.get("offline_mode", False)

        def update_popup_button():
            manifest = state.get("update_manifest") or {}
            version_text = str(manifest.get("version") or "").strip()
            return ft.Container(
                on_click=lambda _e: show_update_prompt(manifest),
                content=ft.Stack(
                    width=58,
                    height=64,
                    controls=[
                        ft.Container(
                            left=6,
                            top=14,
                            content=nav_button(ft.Icons.DOWNLOAD_FOR_OFFLINE_OUTLINED, False),
                        ),
                        ft.Container(
                            right=0,
                            top=0,
                            width=20,
                            height=20,
                            border_radius=999,
                            bgcolor="#2563EB",
                            border=border_all(2, NAV_BG),
                            alignment=CENTER,
                            content=ft.Icon(ft.Icons.ARROW_DOWNWARD_ROUNDED, size=12, color=WHITE),
                        ),
                        *([ft.Container(
                            left=0,
                            bottom=0,
                            width=58,
                            height=16,
                            border_radius=999,
                            bgcolor="#EFF6FF",
                            border=border_all(1, "#BFDBFE"),
                            alignment=CENTER,
                            content=ft.Text(version_text, size=8, weight=ft.FontWeight.W_900, color="#1D4ED8", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        )] if version_text else []),
                    ],
                ),
            )

        return [
            ft.Container(
                width=48,
                height=48,
                border_radius=14,
                bgcolor="#020617",
                border=border_all(1, "#334155"),
                alignment=CENTER,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                content=profile_media_control(44),
            ),
            ft.Container(
                width=58,
                height=22,
                border_radius=999,
                bgcolor="#0F172A",
                border=border_all(1, "#334155"),
                alignment=CENTER,
                content=ft.Row(
                    spacing=4,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=7, height=7, border_radius=99, bgcolor=status_color),
                        ft.Text(status_text, size=9, weight=ft.FontWeight.W_800, color="#CBD5E1"),
                    ],
                ),
            ),
            ft.Container(
                width=58,
                height=22,
                alignment=CENTER,
                content=ft.Switch(value=online_enabled, scale=0.55, on_change=lambda e: confirm_connectivity_change(bool(e.control.value))),
            ),
            ft.Container(height=18),
            ft.Container(on_click=show_board, content=nav_button(ft.Icons.DASHBOARD_ROUNDED, state["screen"] == SCREEN_BOARD)),
            ft.Container(on_click=show_browser, content=nav_button(ft.Icons.FOLDER_OUTLINED, state["screen"] == SCREEN_BROWSER)),
            ft.Container(on_click=show_calendar, content=nav_button(ft.Icons.CALENDAR_TODAY_OUTLINED, state["screen"] == SCREEN_CALENDAR)),
            ft.Container(on_click=show_templates, content=nav_button(ft.Icons.ARTICLE_OUTLINED, state["screen"] == SCREEN_TEMPLATES)),
            ft.Container(on_click=show_health, content=nav_button(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, state["screen"] == SCREEN_HEALTH)),
            ft.Container(on_click=show_settings, content=nav_button(ft.Icons.SETTINGS_OUTLINED, state["screen"] == SCREEN_SETTINGS)),
            ft.Container(expand=True),
            *([update_popup_button()] if state.get("update_available") else []),
            ft.Container(on_click=show_help, content=nav_button(ft.Icons.HELP_OUTLINE, False)),
        ]

    def update_sidebar():
        try:
            sidebar.content.controls = build_sidebar_controls()
        except NameError:
            pass

    sidebar = ft.Container(
        width=80,
        bgcolor=NAV_BG,
        border=ft.Border(right=ft.BorderSide(1, "#020617")),
        padding=pad_sym(vertical=28),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
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
            ft.PopupMenuItem(content="Add file", icon=ft.Icons.UPLOAD_FILE_OUTLINED, on_click=lambda _e: add_task_dialog("file")),
            ft.PopupMenuItem(content="Add link", icon=ft.Icons.LINK_ROUNDED, on_click=lambda _e: add_task_dialog("link")),
            ft.PopupMenuItem(content="Create project", icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED, on_click=lambda _e: add_task_dialog("project")),
            ft.PopupMenuItem(content="Calendar event", icon=ft.Icons.ADD_ALERT_OUTLINED, on_click=lambda _e: show_calendar_event_dialog(selected_date=calendar_state["selected"])),
            ft.PopupMenuItem(content="Templates", icon=ft.Icons.ARTICLE_OUTLINED, on_click=show_templates),
            ft.PopupMenuItem(content="Export report", icon=ft.Icons.IOS_SHARE_OUTLINED, on_click=export_report),
            ft.PopupMenuItem(content="About SA CHECK", icon=ft.Icons.INFO_OUTLINED, on_click=show_about),
            ft.PopupMenuItem(content="Sync now", icon=ft.Icons.SYNC, on_click=sync_now),
        ],
    )

    sync_button = ft.IconButton(icon=ft.Icons.SYNC, tooltip="Sync Work folders", icon_color=MUTED, on_click=sync_now)
    export_button = ft.IconButton(icon=ft.Icons.IOS_SHARE_OUTLINED, tooltip="Export report", icon_color=MUTED, on_click=export_report)
    about_button = ft.IconButton(icon=ft.Icons.INFO_OUTLINED, tooltip="About SA CHECK", icon_color=MUTED, on_click=show_about)

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
                ft.Row(spacing=10, controls=[about_button, export_button, sync_button, quick_add]),
            ],
        ),
    )

    content = ft.Container(
        expand=True,
        padding=pad_only(left=24, right=24, top=26, bottom=24),
        content=ft.Column(spacing=22, expand=True, controls=[header, main_body]),
    )

    page.add(ft.Row(spacing=0, expand=True, controls=[sidebar, content]))
    render_current()
    if settings.get("manual_seen_version") != MANUAL_VERSION:
        show_help(auto=True)
    check_for_updates(manual=False)

    def show_event_reminder_popup(events, reminder_day, title="Today's reminders", alert_time="09:00"):
        if not events:
            return
        show_windows_toast(f"{APP_NAME} Calendar", f"{len(events)} reminder(s) for {reminder_day.strftime('%d %b %Y')}")
        show_message(page, "Calendar reminder", f"{len(events)} event(s) due now.", kind="warning")

        def event_line(event):
            color, bg = event_style(event)
            event_time = event.get("time", alert_time)
            return ft.Container(
                bgcolor=bg,
                border=border_all(1, color + "55"),
                border_radius=12,
                padding=pad_sym(horizontal=12, vertical=9),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CELEBRATION_OUTLINED, size=18, color=color),
                        ft.Column(
                            spacing=2,
                            expand=True,
                            controls=[
                                ft.Text(event.get("title", "Event"), size=14, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(event.get("note") or event.get("kind", "Event"), size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ],
                        ),
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

    def check_calendar_event_reminders():
        now = datetime.now()
        today_key = now.date().isoformat()
        now_hm = now.strftime("%H:%M")
        notified = settings.setdefault("calendar_event_alerts", {})
        due_daily = []
        due_alarm = []
        for event in calendar_events:
            if str(event.get("date", ""))[:10] != today_key:
                continue
            event_id = event.get("id") or event.get("title", "")
            if event.get("notify", True) and now_hm >= "09:00":
                daily_key = f"daily:{today_key}:{event_id}:09:00"
                if not notified.get(daily_key):
                    due_daily.append(event)
                    notified[daily_key] = datetime.now().isoformat(timespec="seconds")
            event_time = event.get("time", "09:00")
            if event.get("alarm", True) and now_hm >= event_time:
                alarm_key = f"alarm:{today_key}:{event_id}:{event_time}"
                if not notified.get(alarm_key):
                    due_alarm.append(event)
                    notified[alarm_key] = datetime.now().isoformat(timespec="seconds")
        if due_daily or due_alarm:
            save_calendar_events()
            combined = []
            seen = set()
            for item in [*due_alarm, *due_daily]:
                key = item.get("id") or item.get("title", "")
                if key in seen:
                    continue
                seen.add(key)
                combined.append(item)
            popup_title = "Event-time alarm" if due_alarm else "Today's reminders"
            show_event_reminder_popup(combined, now.date(), popup_title, now_hm)

    def realtime_sync_loop():
        while not state.get("closed"):
            time.sleep(sync_interval_seconds())
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
            except Exception:
                state["syncing"] = False

    page.run_thread(realtime_sync_loop)
    page.run_thread(lambda: (time.sleep(2), check_calendar_event_reminders()))


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
        return ft.Container(
            padding=pad_sym(horizontal=12, vertical=7),
            border_radius=999,
            bgcolor=bg,
            border=border_all(1, color),
            content=ft.Row(
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=8, height=8, border_radius=999, bgcolor=color),
                    ft.Text(label or resolved_label, size=12, weight=ft.FontWeight.W_900, color=color),
                ],
            ),
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
                                ft.Text(f"Edit Task: {task.get('name', 'Untitled task')}", size=26, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
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
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=MUTED), ft.Text("Core Details", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
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
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, color=MUTED), ft.Text("Detailed Notes", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
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

    def copy_target(_event):
        page.clipboard.set(target)
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
                            ft.Text(task.get("name", "Untitled task"), size=32, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
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


def task_card(page, task, save_and_render, all_tasks):
    icon, icon_color = task_icon(task.get("type", "Other"))

    def copy_target(_event):
        page.clipboard.set(task.get("link", ""))
        show_message(page, "Copied", "Task target copied to clipboard.")

    def try_open(_event):
        if not open_target(task):
            show_message(page, "Cannot open", "The target file or link was not found.")

    def try_folder(_event):
        if not open_folder(task):
            show_message(page, "Cannot open folder", "No valid folder was found for this task.")

    def open_detail(_event):
        show_task_detail(page, task, save_and_render, all_tasks)

    def move_to(status):
        before = dict(task)
        create_snapshot("Before card status move")
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
        save_and_render("Status updated.")

    menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        icon_size=19,
        icon_color=MUTED_2,
        items=[
            ft.PopupMenuItem(content="Folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=try_folder),
            ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_target),
            ft.PopupMenuItem(content="Edit date", icon=ft.Icons.EVENT_OUTLINED, on_click=lambda _e: show_task_date_dialog(page, task, save_and_render, all_tasks)),
            ft.PopupMenuItem(content="Move to Waiting", icon=ft.Icons.RADIO_BUTTON_UNCHECKED, on_click=lambda _e: move_to(STATUS_PENDING)),
            ft.PopupMenuItem(content="Move to Doing", icon=ft.Icons.PLAY_CIRCLE_OUTLINE, on_click=lambda _e: move_to(STATUS_PROGRESS)),
            ft.PopupMenuItem(content="Move to Success", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda _e: move_to(STATUS_DONE)),
        ],
    )

    return ft.Container(
        height=58,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=14,
        padding=pad_only(left=14, right=2),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#10000000", offset=ft.Offset(0, 4)),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=34, height=34, border_radius=10, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=17, color=icon_color)),
                ft.Text(task.get("name", "Untitled task"), size=15, color=TEXT, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                row_action_button("Open", ft.Icons.OPEN_IN_NEW, try_open, width=104),
                row_action_button("Detail", ft.Icons.INFO_OUTLINE, open_detail, width=108),
                menu,
            ],
        ),
    )


def grouped_task_card(page, task, save_and_render, all_tasks):
    return task_card(page, task, save_and_render, all_tasks)


def type_group_card(page, file_type, tasks, save_and_render, all_tasks, group_key=None, group_limits=None, on_more=None):
    icon, icon_color = task_icon(file_type)
    limit = (group_limits or {}).get(group_key, DEFAULT_BATCH_SIZE)
    visible_tasks, resolved_limit = visible_slice(tasks, limit, DEFAULT_BATCH_SIZE)
    hidden_count = max(0, len(tasks) - len(visible_tasks))
    controls = [grouped_task_card(page, task, save_and_render, all_tasks) for task in visible_tasks]
    if hidden_count:
        def load_more(_event):
            if group_limits is not None and group_key:
                group_limits[group_key] = next_visible_limit(resolved_limit, len(tasks), DEFAULT_BATCH_SIZE)
            if on_more:
                on_more()

        controls.append(
            ft.Container(
                height=44,
                border_radius=10,
                bgcolor="#F8FAFC",
                alignment=CENTER,
                content=ft.Button(
                    f"Show more ({hidden_count} left)",
                    icon=ft.Icons.EXPAND_MORE,
                    on_click=load_more,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            )
        )
    return ft.Container(
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=13,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color="#10000000", offset=ft.Offset(0, 4)),
        content=ft.ExpansionTile(
            expanded=False,
            maintain_state=True,
            tile_padding=pad_only(left=10, right=8),
            controls_padding=pad_only(left=8, right=8, bottom=8),
            collapsed_bgcolor=WHITE,
            bgcolor=WHITE,
            title=ft.Row(
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=28, height=28, border_radius=9, bgcolor="#F8FAFC", alignment=CENTER, content=ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=16, color=MUTED)),
                    ft.Container(width=30, height=30, border_radius=9, bgcolor="#EFF6FF", alignment=CENTER, content=ft.Icon(icon, size=16, color=icon_color)),
                    ft.Text(file_type, size=13, weight=ft.FontWeight.W_800, color=TEXT, expand=True),
                    ft.Container(padding=pad_sym(horizontal=8, vertical=3), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(str(len(tasks)), size=11, weight=ft.FontWeight.W_800, color=MUTED)),
                ],
            ),
            controls=[ft.Column(spacing=10, controls=controls)],
        ),
    )


def grouped_task_controls(page, tasks, save_and_render, all_tasks, column_key="", group_limits=None, on_more=None):
    grouped = {}
    for task in tasks:
        grouped.setdefault(task.get("type", "Other"), []).append(task)
    controls = []
    ordered_types = [file_type for file_type in runtime_file_types() if file_type in grouped]
    ordered_types.extend(sorted(file_type for file_type in grouped if file_type not in ordered_types))
    for file_type in ordered_types:
        controls.append(type_group_card(page, file_type, grouped[file_type], save_and_render, all_tasks, f"{column_key}:{file_type}", group_limits, on_more))
    return controls


def kanban_column(page, title, tasks, tint, accent, save_and_render, all_tasks, grouped=True, group_limits=None, on_more=None):
    if tasks:
        controls = grouped_task_controls(page, tasks, save_and_render, all_tasks, title, group_limits, on_more) if grouped else [task_card(page, task, save_and_render, all_tasks) for task in tasks]
        body = ft.ListView(spacing=12, expand=True, controls=controls)
    else:
        body = ft.Container(expand=True, alignment=CENTER, content=ft.Text("No tasks yet", size=14, weight=ft.FontWeight.W_500, color=MUTED_2))
    return ft.Container(
        expand=True,
        bgcolor=tint,
        border=border_all(1, BORDER),
        border_radius=18,
        padding=10,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=16, color="#0C000000", offset=ft.Offset(0, 5)),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Container(
                    height=44,
                    padding=pad_sym(horizontal=12, vertical=0),
                    border_radius=12,
                    bgcolor=accent,
                    shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color="#18000000", offset=ft.Offset(0, 4)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Container(width=6, height=26, border_radius=999, bgcolor="#FFFFFF99"),
                                    ft.Text(title, size=16, weight=ft.FontWeight.W_800, color=WHITE),
                                    ft.Container(padding=pad_sym(horizontal=8, vertical=3), border_radius=999, bgcolor="#FFFFFFE8", content=ft.Text(str(len(tasks)), size=11, weight=ft.FontWeight.W_900, color=accent)),
                                ],
                            ),
                            ft.Icon(ft.Icons.MORE_VERT, size=20, color="#FFFFFFCC"),
                        ],
                    ),
                ),
                ft.Container(expand=True, content=body),
            ],
        ),
    )


if __name__ == "__main__":
    ft.run(main)
