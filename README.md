# SA CHECK

## Current Release

Version: `1.0.3-02 Build 2`

This is a small platform update for testing the GitHub in-app updater notification flow.

Changes in this build:

- Update prompt appears every time SA CHECK detects a newer uploaded platform.
- GitHub update manifest is fetched with a cachebuster on every check.
- Removed same-session duplicate blocking so every update upload is visible during testing.
- Work folders, user settings, and cache are not cleared by this update.

Update channel:

- Manifest: `sacheck_update.json`
- Installer payload: `release/SA_CHECK_Installer.exe`
- Repository: `https://github.com/spirmx/SACHECK`

SA CHECK เป็นแอพ Desktop สำหรับจัดบอร์ดงาน SA/IT บน Windows ทำงานแบบ offline-first และอ่านไฟล์จากโฟลเดอร์ Work ที่ผู้ใช้เลือกได้เอง เหมาะกับงานที่แยกหลายคลัง เช่น Work1, Work2 หรือโฟลเดอร์งานของแต่ละทีม

## ตำแหน่งระบบ

```text
C:\SACHECK
```

ตัวแอพที่ติดตั้งจริง:

```text
C:\SACHECK\app\SACHECK.exe
```

Shortcut หลัก:

```text
C:\Users\Hoyturbro\Desktop\SA CHECK.lnk
```

## วิธีเปิดใช้งาน

เปิดจาก Desktop shortcut:

```text
SA CHECK.lnk
```

หรือเปิดตรงจากไฟล์:

```powershell
C:\SACHECK\app\SACHECK.exe
```

## แนวคิดของระบบ

SA CHECK แยก 2 ส่วนออกจากกัน:

- โฟลเดอร์แอพ: อยู่ที่ `C:\SACHECK`
- โฟลเดอร์งานจริง: เลือกได้จากหน้า Settings ในแอพ

โฟลเดอร์แอพไม่ควรเอาไฟล์งานจริงไปกองไว้ข้างใน ให้ใช้ปุ่มเลือก Work Folder ใน Settings เพื่อชี้ไปยังคลังงานที่ต้องการแทน

## เลือก Work Folder

เข้าแอพ แล้วไปที่:

```text
Settings > Work Folder Source > Choose Work folder
```

เลือกโฟลเดอร์งานที่ต้องการ เช่น:

```text
C:\Users\Hoyturbro\Desktop\TQM Work Inside\Work
D:\Work1
D:\Work2
```

หลังเลือกแล้ว SA CHECK จะอ่านงานจากโฟลเดอร์นั้น และจำค่าไว้ใน:

```text
C:\SACHECK\app\data\app_settings.json
```

## โครงสร้าง Work Folder

ระบบรองรับสถานะงานหลัก:

```text
Work\<Category>\Waiting
Work\<Category>\Doing
Work\<Category>\Success
Work\<Category>\Template
```

ตัวอย่าง:

```text
Work\Word\Waiting
Work\Word\Doing
Work\Word\Success
Work\Word\Template
```

## ฟีเจอร์หลัก

- Board สำหรับดูงาน Waiting, Doing, Success
- Browser สำหรับอ่านไฟล์จาก Work Folder
- Detail สำหรับดูและแก้ข้อมูลงาน
- Rename ไฟล์/โฟลเดอร์จริงจากหน้า Detail
- Calendar พร้อมไฮไลท์วันนี้
- Template สำหรับสร้างงานซ้ำ
- Settings สำหรับเลือก Work Folder และตั้งค่าระบบ
- Desktop shortcut และ Start Menu shortcut
- Auto Run ตอนเปิด Windows

## การ Rename ไฟล์และโฟลเดอร์

การเปลี่ยนชื่อใน Detail จะเปลี่ยนชื่อไฟล์หรือโฟลเดอร์จริงด้วย ระบบจะ sanitize ตัวอักษรต้องห้ามของ Windows ให้อัตโนมัติ เช่น:

```text
New:Template.docx -> New-Template.docx
Client/Work:01 -> Client-Work-01
```

ถ้ามีชื่อซ้ำ ระบบจะเติมเลขต่อท้ายแทนการเขียนทับไฟล์เดิม

## ไฟล์สำคัญของระบบ

```text
C:\SACHECK\app.py                         จุดเริ่มต้นของ Flet app
C:\SACHECK\ui\flet_dashboard.py           หน้าจอหลักของแอพ
C:\SACHECK\core\flet_data.py              จัดการ task, template, rename, sync
C:\SACHECK\core\app_paths.py              จัดการ path และ Work Folder ที่เลือก
C:\SACHECK\installer\install_sacheck.ps1  ติดตั้งแอพลง C:\SACHECK\app
C:\SACHECK\installer\uninstall_sacheck.ps1 ถอนติดตั้ง
C:\SACHECK\SACHECK.spec                   PyInstaller build spec
```

## สำหรับคนพัฒนาต่อ

เอกสารสำหรับแก้โค้ด, build, install, debug และโครงสร้างภายในระบบแยกไว้ที่:

```text
C:\SACHECK\DEVELOPERS.md
```

## Build EXE

ใช้คำสั่งนี้จาก PowerShell:

```powershell
cd C:\SACHECK
.\.venv\Scripts\python.exe -m PyInstaller C:\SACHECK\SACHECK.spec --noconfirm
```

ผลลัพธ์จะอยู่ที่:

```text
C:\SACHECK\dist\SACHECK.exe
```

หลัง build ให้ copy เข้า release:

```powershell
Copy-Item C:\SACHECK\dist\SACHECK.exe C:\SACHECK\release\SACHECK.exe -Force
```

## Install Final App

หลัง build แล้ว ให้รัน:

```powershell
cd C:\SACHECK
powershell -NoProfile -ExecutionPolicy Bypass -File .\installer\install_sacheck.ps1
```

สิ่งที่ installer ทำ:

- วางตัวแอพที่ `C:\SACHECK\app\SACHECK.exe`
- สร้าง Desktop shortcut ชื่อ `SA CHECK.lnk`
- สร้าง Start Menu shortcut ชื่อ `SA CHECK.lnk`
- ตั้ง Auto Run ใน Windows Startup
- เก็บค่า settings เดิมไว้ถ้ามีอยู่แล้ว

## Uninstall

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\SACHECK\installer\uninstall_sacheck.ps1
```

คำสั่งนี้จะลบตัวติดตั้งและ shortcut ของ SA CHECK ออกจากเครื่อง

## หมายเหตุเรื่อง Flet

ระบบนี้เป็นแอพ Desktop ที่เขียนด้วย Flet และแพ็กเป็น `.exe` ด้วย PyInstaller แล้ว แต่ถ้าต้องการ build แบบ native Flet Windows เต็มรูปแบบ ต้องติดตั้ง Visual Studio Build Tools พร้อม Desktop development with C++ และ Windows SDK ก่อน

ถ้าเครื่องยังไม่มี toolchain นี้ การ build native Flet จะขึ้น error ประมาณ:

```text
Unable to find suitable Visual Studio toolchain
```

เวอร์ชันที่ใช้งานจริงตอนนี้คือ:

```text
C:\SACHECK\app\SACHECK.exe
```

## ข้อควรระวัง

- อย่าลบ `C:\SACHECK\app\data\app_settings.json` ถ้าไม่อยากเสียค่า Work Folder ที่เลือกไว้
- อย่าเก็บไฟล์งานจริงไว้ในโฟลเดอร์แอพ
- ก่อน rebuild ควรปิด SA CHECK ให้หมดก่อน
- ถ้าโฟลเดอร์เก่าลบไม่ได้ ให้ปิด Codex/โปรแกรมที่เปิดโฟลเดอร์นั้นอยู่ หรือรีสตาร์ทเครื่อง
