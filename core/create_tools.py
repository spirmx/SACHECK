"""Create-new tool definitions and file builders for SACHECK."""

from __future__ import annotations

from pathlib import Path
import time
import zipfile


CREATE_TOOLS = [
    {
        "name": "Word Document",
        "type": "Word",
        "kind": "file",
        "extension": ".docx",
        "icon": "Word",
        "description": "Create a blank Word file in Doing.",
    },
    {
        "name": "Excel Workbook",
        "type": "Excel",
        "kind": "file",
        "extension": ".xlsx",
        "icon": "Excel",
        "description": "Create a blank Excel file in Doing.",
    },
    {
        "name": "PowerPoint Slide",
        "type": "Slide",
        "kind": "file",
        "extension": ".pptx",
        "icon": "Slide",
        "description": "Create a blank presentation in Doing.",
    },
    {
        "name": "HTML Page",
        "type": "Web",
        "kind": "file",
        "extension": ".html",
        "icon": "Web",
        "description": "Create an HTML starter file.",
    },
    {
        "name": "Text Note",
        "type": "Other",
        "kind": "file",
        "extension": ".txt",
        "icon": "Other",
        "description": "Create a plain text work note.",
    },
    {
        "name": "VS Code Project",
        "type": "Project",
        "kind": "folder",
        "icon": "Project",
        "launcher": "code",
        "description": "Create a project folder and open it.",
    },
    {
        "name": "Google Sheet",
        "type": "Google Sheet",
        "kind": "url",
        "url": "https://docs.google.com/spreadsheets/create",
        "icon": "Google Sheet",
        "description": "Open a new Google Sheet and track the link.",
    },
    {
        "name": "Google Doc",
        "type": "Word",
        "kind": "url",
        "url": "https://docs.google.com/document/create",
        "icon": "Word",
        "description": "Open a new Google Doc and track the link.",
    },
    {
        "name": "Google Slide",
        "type": "Slide",
        "kind": "url",
        "url": "https://docs.google.com/presentation/create",
        "icon": "Slide",
        "description": "Open a new Google Slides deck.",
    },
    {
        "name": "Canva",
        "type": "Canva",
        "kind": "url",
        "url": "https://www.canva.com/",
        "icon": "Canva",
        "description": "Open Canva and track this job.",
    },
    {
        "name": "Miro Board",
        "type": "Miro",
        "kind": "url",
        "url": "https://miro.com/app/dashboard/",
        "icon": "Miro",
        "description": "Open Miro and track this board.",
    },
    {
        "name": "Figma",
        "type": "Figma",
        "kind": "url",
        "url": "https://www.figma.com/files/",
        "icon": "Figma",
        "description": "Open Figma files.",
    },
]


def retry_create_operation(operation, *, attempts=3, delay=0.16, label="Create file"):
    last_error = None
    for attempt in range(attempts):
        try:
            return operation()
        except OSError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(delay * (attempt + 1))
    raise OSError(f"{label} failed after {attempts} attempts. Last error: {last_error}")


def tool_default_name(tool: dict, timestamp: str) -> str:
    return f"{tool.get('name', 'New Work')} {timestamp}"


def create_project_folder(path: Path, title: str):
    path.mkdir(parents=True, exist_ok=True)
    readme = path / "README.md"
    if not readme.exists():
        retry_create_operation(lambda: readme.write_text(f"# {title}\n\nCreated from SACHECK.\n", encoding="utf-8"), label=f"Create {readme.name}")
    src = path / "src"
    src.mkdir(exist_ok=True)


def write_blank_docx(path: Path):
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p/><w:sectPr/></w:body></w:document>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)


def write_blank_xlsx(path: Path):
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    sheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def write_blank_pptx(path: Path):
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""
    presentation = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldIdLst/></p:presentation>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("ppt/presentation.xml", presentation)


def write_blank_file(path: Path, tool: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        write_blank_docx(path)
    elif suffix == ".xlsx":
        write_blank_xlsx(path)
    elif suffix == ".pptx":
        write_blank_pptx(path)
    elif suffix == ".html":
        retry_create_operation(lambda: path.write_text("<!doctype html>\n<html>\n<head><meta charset=\"utf-8\"><title>New Work</title></head>\n<body>\n\n</body>\n</html>\n", encoding="utf-8"), label=f"Create {path.name}")
    else:
        retry_create_operation(lambda: path.write_text("", encoding="utf-8"), label=f"Create {path.name}")
