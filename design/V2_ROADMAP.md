# SA CHECK — V2.0.0 Roadmap

แผนยกเครื่องระบบสู่เวอร์ชัน 2.0.0 แบบทำเป็นเฟส (audit-first, verify ทีละขั้น, ไม่พังของเดิม)

Creator: HOYTURBRO · Planning assist: Claude

---

## Phase 0 — Audit (เสร็จแล้ว)

สรุปสถาปัตยกรรมปัจจุบัน (v1.x WIP, commit `548c3ad` บน main):

- **Theme engine**: `APP_THEME_PRESETS` 7 ธีม (รวม Mint Studio=teal, Night Arcade=dark) + `ensure_palette_contrast`, `readable_text_for`, `color_luminance` ปรับ contrast อัตโนมัติ
- **Sidebar**: `nav_item(icon, label, screen, handler)` มี label แล้ว
- **Context**: `ui/shared.py` DashboardContext ครบ (update_channel_url, apply_app_theme, set_work_folder, show_calendar_event_dialog ฯลฯ)
- **Screens**: board / browser / calendar / templates / settings / health — dispatch ใน `render_current()` (if/elif)
- **Scale**: batched render 40/กลุ่ม + collapsed type groups + ListView virtualization
- **Data model** (`make_task`): id, name, type, detected_type, status, target_kind, link, shortcut_path, file_key, note, date_added, status_date, done_date — **ยังไม่มี** progress / priority / tags / members
- **Add flows**: add work/link/project + template (file+link) ผ่าน `create_task_from_source` / `create_template_from_source` — ครบ
- **Categorization**: `config/category.py` (250+ นามสกุล + URL rules) + `file_intelligence.py` (extension → signature sniff → project stack) — ยังไม่ cache ผลลัพธ์

หลักการทำทุกเฟส: ต่อยอดของเดิม ไม่รื้อ theme engine / ctx / add flows ที่ทำงานอยู่.

---

## Pillar A — UI overhaul → north-star (Intelligence OS Light)

อ้างอิง: `design/intelligence_os_light.html`

- **A1. Command palette (⌘K)** — overlay กระโดดหน้า + ค้นงาน. ใหม่ทั้งหมด, self-contained, เสี่ยงต่ำ.
- **A2. Command Center (overview screen)** — hero + metric cards + mini-board เป็นหน้า default ใหม่. เพิ่ม SCREEN_OVERVIEW + nav item.
- **A3. Card redesign** — badge สีตามหมวด + hover lift (แก้ `ui/dialogs.py` task_card ตัว live).
- **A4. Board polish** — metric header cards เลขนับขึ้น + microbar + column header teal.
- **A5. "SA Light" theme preset** — เพิ่ม preset teal ที่แมตช์ token ของ north-star + ตั้งเป็น default.

## Pillar B — Scale & stability (งานมา 1000+ ต้องลื่น)

- **B1. Debounce search** — หน่วง ~280ms กัน re-render ทุกตัวอักษร (`on_search`).
- **B2. Persist expansion** — จำกลุ่มที่กางไว้ ไม่ให้ background sync หุบ (`type_group_card` + `state["expanded_groups"]`).
- **B3. Sync เบาลง** — throttle `work_signature`; sync ที่ไม่เปลี่ยน status ไม่ rebuild ทั้ง board (targeted update).
- **B4. Cache การคัดแยก** — เก็บ detected_type ตาม file_key+mtime, ไม่ re-sniff ไฟล์ที่ไม่เปลี่ยน.
- **B5. Stress test** — mock 1000–2000 งานหลายประเภท วัด render/scroll/search.

## Pillar C — Smarter categorization

- **C1. Inference cache** (ผูกกับ B4).
- **C2. Custom type manager** — เพิ่ม/แก้/ลบหมวด + สี + นามสกุล จาก Settings ให้ครบวงจร.
- **C3. Bulk import** — ลากไฟล์ทีละเยอะ → คัดแยก + จัดลง Waiting ตามหมวด พร้อม progress.
- **C4. Mismatch surfacing** — เตือนเมื่อ type (โฟลเดอร์) ≠ detected_type ให้ย้าย 1 คลิก (ต่อยอด health).

## Pillar D — Data model additions

- **D1. เพิ่ม field**: `progress` (0–100), `priority` (int), `tags` (list), `members` (list) — optional, default เมื่อไม่มี.
- **D2. Migration**: `normalize_task` เติม default + กันของเก่าไม่พัง.
- **D3. UI**: การ์ดโชว์ progress bar + tags; แก้ในหน้า Detail.
- **D4. Sort/filter** ตาม priority / progress / tag.

---

## ลำดับที่แนะนำ (dependency-aware)

1. **B1 + B2** — quick win ความนิ่ง เสี่ยงต่ำสุด เห็นผลไว
2. **A1** — command palette (wow, self-contained)
3. **D1 + D2** — วางฐาน data model ก่อน (UI หลายอย่างต้องใช้)
4. **A5 + A3** — theme token + card redesign
5. **A2 + A4** — Command Center + board polish (ใช้ metric/progress จาก D)
6. **D3 + D4** — โชว์/จัดการ field ใหม่บน UI
7. **B4 + C1** — cache คัดแยก (ต้องเทสกับโฟลเดอร์ใหญ่)
8. **C2 + C3 + C4** — categorization ครบวงจร
9. **B3** — sync targeted update (ละเอียดอ่อน ทำท้ายสุด)
10. **B5** — stress test ปิดจ็อบก่อนปล่อย

## Guardrails

- ทำงานบน branch `v2.0.0` แยกจาก `main` (main = ตัวเสถียร)
- แต่ละเฟส: แก้ → `py_compile` + import ผ่าน venv → รันเทส → commit เดี่ยว
- ไม่แตะ theme engine / ctx / add-flow / snapshot / undo ที่ทำงานอยู่ นอกจากจำเป็น
- Data model เปลี่ยนแบบ backward-compatible เสมอ (ของเก่าเปิดได้)
- อัปเดต APP_VERSION → `2.0.0` + VERSION_HISTORY ตอนใกล้ปล่อย
