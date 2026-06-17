"""File, folder, and URL type detection for SACHECK."""

from pathlib import Path
from urllib.parse import unquote, urlparse
import zipfile


def is_url(target: str) -> bool:
    return (target or "").lower().startswith(("http://", "https://"))


def read_url_shortcut_target(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.lower().startswith("url="):
                return line.split("=", 1)[1].strip()
    except OSError:
        return ""
    return ""


def infer_type_from_url(target: str, url_extension_types: dict, url_rules: list) -> str:
    value = (target or "").strip()
    if not value:
        return "Other"

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = unquote(parsed.path).lower()
    query = unquote(parsed.query).lower()
    combined = f"{host}{path}?{query}"

    suffix = Path(path).suffix.lower()
    if suffix in url_extension_types:
        return url_extension_types[suffix]
    for extension, file_type in url_extension_types.items():
        if extension and extension in combined:
            return file_type

    for rule in url_rules:
        rule_host = rule.get("host")
        rule_contains = rule.get("host_contains")
        rule_prefix = rule.get("path_prefix")
        rule_path_contains = rule.get("path_contains")
        if rule_host and not host.endswith(rule_host):
            continue
        if rule_contains and rule_contains not in host:
            continue
        if rule_prefix and not path.startswith(rule_prefix):
            continue
        if rule_path_contains and rule_path_contains.lower() not in combined:
            continue
        return rule.get("type", "Other")

    if "office.com" in host or "sharepoint.com" in host or "onedrive.live.com" in host:
        if any(token in combined for token in ("word", "docx", "document")):
            return "Word"
        if any(token in combined for token in ("excel", "xlsx", "spreadsheet")):
            return "Excel"
        if any(token in combined for token in ("powerpoint", "pptx", "presentation")):
            return "Slide"
    if "pdf" in path.split("/")[-1]:
        return "PDF"
    return "Link" if is_url(value) else "Other"


def infer_type_from_folder(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return "Other"
    names = {item.name.lower() for item in path.iterdir()}
    suffixes = {item.suffix.lower() for item in path.iterdir() if item.is_file()}

    if {"index.html", "package.json"} & names or {".html", ".htm", ".css", ".js", ".ts", ".jsx", ".tsx"} & suffixes:
        return "Web"
    if {"package.json", "pyproject.toml", "requirements.txt", "composer.json", "pom.xml", "build.gradle"} & names:
        return "Project"
    if {".py", ".js", ".ts", ".java", ".cs", ".php", ".go", ".rs", ".sql"} & suffixes:
        return "Project"
    if {"readme.md", ".gitignore"} & names:
        return "Project"
    return "Project"


def detect_project_stack(path: str) -> str:
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        return ""
    try:
        names = {item.name.lower() for item in folder.iterdir()}
        suffixes = {item.suffix.lower() for item in folder.iterdir() if item.is_file()}
    except OSError:
        return ""

    stacks = []
    package_text = ""
    package_path = folder / "package.json"
    if package_path.exists():
        try:
            package_text = package_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            package_text = ""

    node_markers = {"package.json", "vite.config.js", "vite.config.ts", "next.config.js", "next.config.ts", "nuxt.config.ts"}
    if names & node_markers:
        if "next" in package_text or {"next.config.js", "next.config.ts"} & names:
            stacks.append("Next.js")
        elif "react" in package_text or {".jsx", ".tsx"} & suffixes:
            stacks.append("React")
        elif "vue" in package_text or ".vue" in suffixes:
            stacks.append("Vue")
        elif "svelte" in package_text or ".svelte" in suffixes:
            stacks.append("Svelte")
        elif "angular" in package_text or "angular.json" in names:
            stacks.append("Angular")
        elif "vite" in package_text or {"vite.config.js", "vite.config.ts"} & names:
            stacks.append("Vite")
        else:
            stacks.append("Node/Web")

    python_markers = {"manage.py", "pyproject.toml", "requirements.txt", "pipfile", "poetry.lock"}
    if names & python_markers or ".py" in suffixes:
        if "manage.py" in names:
            stacks.append("Django")
        elif "app.py" in names or "main.py" in names:
            try:
                sample = "\n".join(
                    (folder / name).read_text(encoding="utf-8", errors="ignore")[:2000].lower()
                    for name in ("app.py", "main.py")
                    if (folder / name).exists()
                )
            except OSError:
                sample = ""
            if "fastapi" in sample:
                stacks.append("FastAPI")
            elif "flask" in sample:
                stacks.append("Flask")
            else:
                stacks.append("Python")
        else:
            stacks.append("Python")

    if "composer.json" in names:
        stacks.append("PHP/Laravel" if (folder / "artisan").exists() else "PHP")
    if "pom.xml" in names or "build.gradle" in names:
        stacks.append("Java")
    if ".csproj" in suffixes or ".sln" in suffixes:
        stacks.append(".NET")
    if "go.mod" in names:
        stacks.append("Go")
    if "cargo.toml" in names:
        stacks.append("Rust")
    if "dockerfile" in names or "docker-compose.yml" in names:
        stacks.append("Docker")
    if ".sql" in suffixes:
        stacks.append("SQL")

    if not stacks and {"index.html"} & names:
        stacks.append("HTML/CSS/JS")
    if not stacks and {".html", ".css", ".js"} & suffixes:
        stacks.append("Static Web")

    unique = []
    for stack in stacks:
        if stack not in unique:
            unique.append(stack)
    return " + ".join(unique[:3])


def infer_type_from_file_signature(path: Path) -> str:
    if path.exists() and path.is_dir():
        return infer_type_from_folder(path)
    if not path.exists() or not path.is_file():
        return "Other"
    try:
        header = path.read_bytes()[:4096]
    except OSError:
        return "Other"

    if header.startswith(b"%PDF"):
        return "PDF"
    if header.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as archive:
                names = {name.lower() for name in archive.namelist()}
                if any(name.startswith("word/") for name in names):
                    return "Word"
                if any(name.startswith("xl/") for name in names):
                    return "Excel"
                if any(name.startswith("ppt/") for name in names):
                    return "Slide"
                if "mimetype" in names:
                    mimetype = archive.read("mimetype").decode("utf-8", errors="ignore").lower()
                    if "text" in mimetype:
                        return "Word"
                    if "spreadsheet" in mimetype:
                        return "Excel"
                    if "presentation" in mimetype:
                        return "Slide"
                if any(name.endswith(".drawio") or name.endswith(".xml") for name in names):
                    sample_names = [name for name in archive.namelist()[:8] if name.lower().endswith((".drawio", ".xml"))]
                    for sample_name in sample_names:
                        sample = archive.read(sample_name)[:2048].decode("utf-8", errors="ignore").lower()
                        if "<mxfile" in sample or "drawio" in sample:
                            return "Diagram"
        except (OSError, zipfile.BadZipFile, KeyError):
            return "Other"

    text_sample = header.decode("utf-8", errors="ignore").lower()
    if "<mxfile" in text_sample or "graphml" in text_sample or "@startuml" in text_sample:
        return "Diagram"
    if "<svg" in text_sample:
        return "Diagram"
    return "Other"


def infer_type_from_path(path: str, extension_types: dict, url_extension_types: dict, url_rules: list) -> str:
    value = (path or "").strip().strip('"')
    if not value:
        return "Other"
    if is_url(value):
        return infer_type_from_url(value, url_extension_types, url_rules)

    target_path = Path(value)
    if target_path.exists() and target_path.is_dir():
        return infer_type_from_folder(target_path)
    suffix = target_path.suffix.lower()
    if suffix == ".url" and target_path.exists():
        shortcut_url = read_url_shortcut_target(target_path)
        if shortcut_url:
            return infer_type_from_url(shortcut_url, url_extension_types, url_rules)
    extension_type = extension_types.get(suffix)
    if extension_type:
        return extension_type
    return infer_type_from_file_signature(target_path)


def infer_type_from_target(target: str, extension_types: dict, url_extension_types: dict, url_rules: list) -> str:
    value = (target or "").strip()
    if is_url(value):
        return infer_type_from_url(value, url_extension_types, url_rules)
    return infer_type_from_path(value, extension_types, url_extension_types, url_rules)
