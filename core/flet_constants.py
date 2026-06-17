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
STATUS_FOLDERS = {
    STATUS_PENDING: "Waiting",
    STATUS_PROGRESS: "Doing",
    STATUS_DONE: "Success",
}

try:
    from config.category import CATEGORIES

    FILE_TYPES = [name for name in CATEGORIES.keys()]
except Exception:
    FILE_TYPES = ["Word", "Excel", "PDF", "Figma", "Miro", "Canva", "Slide", "Google Sheet", "Diagram", "Web", "Project", "Library", "Link", "Other"]
