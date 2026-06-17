# SA CHECK Developer Notes

เอกสารนี้สำหรับคนที่จะพัฒนา SA CHECK ต่อจากระบบปัจจุบัน โฟกัสที่โครงสร้างโค้ด จุดที่ควรแก้ และขั้นตอน build/install ให้ไม่หลุดจากตัวจริงที่ลงไว้ใน `C:\SACHECK`

## ภาพรวมระบบ

SA CHECK เป็น Flet desktop app ที่ package ด้วย PyInstaller เป็น Windows `.exe`

ตำแหน่ง source หลัก:

```text
C:\SACHECK
```

ตำแหน่ง app ที่ผู้ใช้เปิดจริง:

```text
C:\SACHECK\app\SACHECK.exe
```

ตัว shortcut บน Desktop ชี้มาที่:

```text
C:\SACHECK\app\SACHECK.exe
```

## Entry Points

```text
C:\SACHECK\app.py
C:\SACHECK\flet_app.py
```

ทั้งสองไฟล์ตั้งค่า Windows AppUserModelID และเรียก:

```python
ft.run(main, name="SA CHECK", assets_dir="assets")
```

UI หลักมาจาก:

```text
C:\SACHECK\ui\flet_dashboard.py
```

## โครงสร้างโค้ดสำคัญ

```text
C:\SACHECK\ui\flet_dashboard.py
```

หน้าจอหลักทั้งหมดของ Flet app เช่น sidebar, board, browser, detail, calendar, settings และ dialogs

```text
C:\SACHECK\core\flet_data.py
```

โหลด/บันทึก task, template, sync จาก Work Folder, rename ไฟล์/โฟลเดอร์, snapshot, undo และ activity log

```text
C:\SACHECK\core\app_paths.py
```

จัดการ path ของระบบ, path settings และ Work Folder ที่ user เลือกจากหน้า Settings

```text
C:\SACHECK\config\category.py
```

ตั้งค่า category, icon, extension และ rule การแยกประเภทไฟล์

```text
C:\SACHECK\assets\app
```

โลโก้และ icon ของแอพ

## Data Files

ไฟล์ data หลักอยู่ใน:

```text
C:\SACHECK\app\data
```

ไฟล์สำคัญ:

```text
app_settings.json   ค่า theme, Work Folder ที่เลือก, calendar events
tasks.json          รายการงานบน board
templates.json      รายการ template
settings_log.json   log ของ settings/activity บางส่วน
```

อย่าลบ `app_settings.json` ถ้าไม่ต้องการ reset ค่า Work Folder ของผู้ใช้

## Work Folder

Work Folder ไม่ควรอยู่ปนกับ source app ผู้ใช้เลือกจากหน้า Settings:

```text
Settings > Work Folder Source > Choose Work folder
```

โค้ดที่อ่านค่าตรงนี้อยู่ใน:

```text
C:\SACHECK\core\app_paths.py
```

ฟังก์ชันสำคัญ:

```python
configured_work_folder()
work_folder()
```

ถ้าไม่มีค่าใน settings ระบบ fallback ไปยังค่า default เดิม

## Calendar

โค้ด Calendar อยู่ใน:

```text
C:\SACHECK\ui\flet_dashboard.py
```

ฟังก์ชันหลัก:

```python
render_calendar()
```

จุดวาด cell ของแต่ละวัน:

```python
day_cell(day)
```

ไฮไลท์วันนี้ใช้ตัวแปร:

```python
is_today = day == today
```

## Rename Logic

การ rename จากหน้า Detail ไปเปลี่ยนไฟล์/โฟลเดอร์จริงอยู่ใน:

```text
C:\SACHECK\core\flet_data.py
```

ฟังก์ชันหลัก:

```python
rename_task_target()
```

จุดสำคัญคือชื่อใหม่ต้องผ่าน:

```python
safe_item_name()
```

เพื่อกันอักขระต้องห้ามของ Windows เช่น `:`, `/`, `\`, `?`, `*`

## Run From Source

```powershell
cd C:\SACHECK
.\.venv\Scripts\python.exe app.py
```

ถ้าใช้ source run แล้วเห็น behavior ไม่เหมือน exe ให้เช็คว่า `assets_dir="assets"` และ path data ถูกอ่านจากตำแหน่งที่คาดไว้หรือไม่

## Syntax Check

```powershell
cd C:\SACHECK
.\.venv\Scripts\python.exe -m py_compile .\ui\flet_dashboard.py
.\.venv\Scripts\python.exe -m py_compile .\core\flet_data.py
.\.venv\Scripts\python.exe -m py_compile .\core\app_paths.py
```

## Build

ก่อน build ให้ปิด SA CHECK ที่เปิดอยู่ก่อน

```powershell
Get-Process -Name SACHECK,flet -ErrorAction SilentlyContinue | Stop-Process -Force
```

build ด้วย PyInstaller:

```powershell
cd C:\SACHECK
.\.venv\Scripts\python.exe -m PyInstaller C:\SACHECK\SACHECK.spec --noconfirm
```

ผลลัพธ์:

```text
C:\SACHECK\dist\SACHECK.exe
```

copy เข้า release:

```powershell
Copy-Item C:\SACHECK\dist\SACHECK.exe C:\SACHECK\release\SACHECK.exe -Force
```

## Install

```powershell
cd C:\SACHECK
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\install_sacheck.ps1
```

installer จะ copy จาก:

```text
C:\SACHECK\release
```

ไปที่:

```text
C:\SACHECK\app
```

และสร้าง shortcut:

```text
C:\Users\Hoyturbro\Desktop\SA CHECK.lnk
```

## Release Checklist

1. ปิด app ที่รันอยู่
2. `py_compile` ไฟล์ที่แก้
3. build ด้วย PyInstaller
4. copy `dist\SACHECK.exe` ไป `release\SACHECK.exe`
5. run `installer\install_sacheck.ps1`
6. เปิดจาก Desktop shortcut
7. เช็คหน้า Board, Browser, Detail, Calendar, Settings
8. ถ้าแก้ rename ให้ทดสอบชื่อที่มีอักขระต้องห้าม เช่น `A:B/C`
9. ถ้าแก้ Work Folder ให้ทดสอบเลือกโฟลเดอร์ใหม่จาก Settings

## Native Flet Build Note

ถ้าต้องการ build แบบ native Flet Windows เต็มรูปแบบ ต้องติดตั้ง Visual Studio Build Tools พร้อม:

```text
Desktop development with C++
Windows SDK
```

ถ้ายังไม่มี จะเจอ error:

```text
Unable to find suitable Visual Studio toolchain
```

ตัว production ตอนนี้ใช้ PyInstaller build ที่:

```text
C:\SACHECK\app\SACHECK.exe
```

## ข้อควรระวังตอนแก้

- อย่า hardcode Work Folder ใหม่ในโค้ด ให้ใช้ `work_folder()`
- อย่าลบ settings ของผู้ใช้ตอน install
- อย่าเอาไฟล์งานจริงใส่ใน `C:\SACHECK`
- ก่อนแก้ UI ให้อ่าน pattern เดิมใน `flet_dashboard.py`
- ถ้าแก้ installer ต้องเช็ค shortcut target ให้ยังเป็น `C:\SACHECK\app\SACHECK.exe`
- ถ้าแก้ logo/icon ให้เช็คทั้ง `assets\app` และ spec build
