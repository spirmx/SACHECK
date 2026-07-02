# SA CHECK Web Prototype

เว็บต้นแบบ UX/UI แบบ standalone สำหรับทดลองทิศทาง SA CHECK รุ่นถัดไป โดยใช้ Mock Data และไม่เชื่อมต่อหรือแก้ข้อมูลของ Desktop app

## เปิดใช้งาน

เปิด `index.html` โดยตรง หรือเปิด local server:

```powershell
python -m http.server 4173
```

จากนั้นเข้า `http://127.0.0.1:4173/web-prototype/` เมื่อรันจากโฟลเดอร์โปรเจกต์หลัก

## ฟังก์ชันต้นแบบ

- Command Center พร้อม metrics, intelligence briefing และ focus queue
- Work Board จำลองข้อมูล 1,250 งาน พร้อมค้นหา กรอง เรียง และลากการ์ดข้าม Waiting / Doing / Success
- Large-workspace rendering แสดงครั้งละ 18 งานต่อคอลัมน์และโหลดเพิ่มเป็นชุด เพื่อไม่สร้าง DOM 1,000+ การ์ดพร้อมกัน
- Template Library พร้อมค้นหา กรองประเภท และสร้างงานจาก Template
- Calendar พร้อมเลือกวันและเพิ่มกิจกรรม Mock
- Intelligence dashboard พร้อม workload radar และ prediction
- Smart Command Palette เปิดด้วย `Ctrl/Cmd + K`
- Quick Add เพิ่มงานใหม่เข้า Mock state
- Responsive layout และ motion system

ข้อมูลทั้งหมดอยู่ในหน่วยความจำของ browser และจะ reset เมื่อ refresh หน้า
