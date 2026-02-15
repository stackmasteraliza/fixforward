"""Generate a realistic terminal-style animated GIF demo for FixForward."""

from PIL import Image, ImageDraw, ImageFont
import imageio
import os

# Catppuccin Mocha terminal theme
BG = (30, 30, 46)
FG = (205, 214, 244)
GREEN = (166, 227, 161)
RED = (243, 139, 168)
YELLOW = (249, 226, 175)
CYAN = (137, 220, 235)
MAGENTA = (203, 166, 247)
DIM = (108, 112, 134)
BLUE = (137, 180, 250)
TITLE_BAR = (49, 50, 68)
BORDER = (88, 91, 112)

WIDTH = 880
HEIGHT = 640
PADDING = 16
LINE_HEIGHT = 17
FONT_SIZE = 13

font_path = "/System/Library/Fonts/Menlo.ttc"
font = ImageFont.truetype(font_path, FONT_SIZE)
font_small = ImageFont.truetype(font_path, 11)

# Max visible lines in the terminal window
MAX_VISIBLE = (HEIGHT - 44) // LINE_HEIGHT


def make_frame(lines_data, cursor=False, scroll_offset=0):
    """Create a single frame with colored terminal lines."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # Title bar with macOS traffic lights
    draw.rectangle([0, 0, WIDTH, 32], fill=TITLE_BAR)
    draw.ellipse([12, 10, 24, 22], fill=(255, 95, 86))
    draw.ellipse([32, 10, 44, 22], fill=(255, 189, 46))
    draw.ellipse([52, 10, 64, 22], fill=(39, 201, 63))
    # Title text
    title = "alizaali — fixforward — 80x24"
    bbox = draw.textbbox((0, 0), title, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 9), title, fill=DIM, font=font_small)

    # Render visible lines
    visible = lines_data[scroll_offset:scroll_offset + MAX_VISIBLE]
    y = 40
    for text, color in visible:
        if y + LINE_HEIGHT > HEIGHT - 4:
            break
        draw.text((PADDING, y), text, fill=color, font=font)
        y += LINE_HEIGHT

    # Blinking cursor
    if cursor:
        draw.rectangle([PADDING, y + 2, PADDING + 7, y + LINE_HEIGHT - 2], fill=FG)

    return img


# ──────────────────────────────────────────────────────────
# Realistic terminal output matching actual fixforward run
# ──────────────────────────────────────────────────────────

# Sections are grouped so we can add pauses between them
# Each section is a list of (text, color) lines + pause duration

sections = [
    # ── Prompt ──
    {
        "lines": [
            ("$ fixforward run --path ./demo/broken_python", GREEN),
        ],
        "pause": 12,
    },
    # ── Banner (appears instantly) ──
    {
        "lines": [
            ("", FG),
            ("╔═══════════════════════════════════════════════════════════════╗", MAGENTA),
            ("║                                                               ║", MAGENTA),
            ("║    _____ _      _____                            _            ║", MAGENTA),
            ("║   |  ___(_)_  _|  ___|__  _ ____      ____ _ _ __| |          ║", MAGENTA),
            ("║   | |_  | \\ \\/ / |_ / _ \\| '__\\ \\ /\\ / / _` | '__| |        ║", MAGENTA),
            ("║   |  _| | |>  <|  _| (_) | |   \\ V  V / (_| | |  | |        ║", MAGENTA),
            ("║   |_|   |_/_/\\_\\_|  \\___/|_|    \\_/\\_/ \\__,_|_|  |_|        ║", MAGENTA),
            ("║                                                               ║", MAGENTA),
            ("╚═════════ incident-to-PR autopilot · GitHub Copilot CLI ═══════╝", MAGENTA),
        ],
        "pause": 6,
        "instant": True,
    },
    # ── Step 1 ──
    {
        "lines": [
            ("", FG),
            ("  [1/6] Detecting project ecosystem...", CYAN),
        ],
        "pause": 10,
    },
    {
        "lines": [
            ("╭────────────────────────────────────────────────────────────────╮", BORDER),
            ("│  Detected: Python / pytest                                     │", GREEN),
            ("╰────────────────────────────────────────────────────────────────╯", BORDER),
        ],
        "pause": 6,
        "instant": True,
    },
    # ── Step 2 ──
    {
        "lines": [
            ("", FG),
            ("  [2/6] Running tests to capture failures...", CYAN),
        ],
        "pause": 14,
    },
    {
        "lines": [
            ("┏━━━━━━━━━━━━━━━━━━━━ TEST FAILURES DETECTED ━━━━━━━━━━━━━━━━━━━┓", RED),
            ("┃  1 failed / 4 passed / 5 total  (0.2s)                         ┃", RED),
            ("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", RED),
        ],
        "pause": 10,
        "instant": True,
    },
    # ── Step 3 ──
    {
        "lines": [
            ("", FG),
            ("  [3/6] Classifying failures...", CYAN),
        ],
        "pause": 8,
    },
    {
        "lines": [
            ("", FG),
            ("                        Failure Classification", FG),
            ("", FG),
            ("   Tag   Test          File          Category    Confidence", DIM),
            ("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", DIM),
            ("   AST   test_divide   test_app.py   assertion   ████░ 85%", YELLOW),
            ("                                     Assertion: value mismatch", DIM),
            ("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", DIM),
        ],
        "pause": 12,
        "instant": True,
    },
    # ── Step 4 (Copilot) ──
    {
        "lines": [
            ("", FG),
            ("  [4/6] Asking GitHub Copilot for a fix...", CYAN),
        ],
        "pause": 20,
    },
    {
        "lines": [
            ("", FG),
            ("╭──────────────────────────── app.py ────────────────────────────╮", BORDER),
            ("│  --- a/app.py                                                  │", RED),
            ("│  +++ b/app.py                                                  │", GREEN),
            ("│  @@ -16,4 +16,4 @@ def divide(a, b):                         │", CYAN),
            ("│       if b == 0:                                               │", FG),
            ("│           raise ValueError(\"Cannot divide by zero\")            │", FG),
            ("│  -    return a / b                                             │", RED),
            ("│  +    return a // b                                            │", GREEN),
            ("╰────────────────────────────────────────────────────────────────╯", BORDER),
        ],
        "pause": 14,
        "instant": True,
    },
    # ── Step 5 ──
    {
        "lines": [
            ("", FG),
            ("  [5/6] Applying patch on a safe branch...", CYAN),
        ],
        "pause": 8,
    },
    {
        "lines": [
            ("╭──────────────────────── PATCH APPLIED ─────────────────────────╮", BORDER),
            ("│  Branch: fixforward/auto-20260215-130944                       │", BLUE),
            ("│  Files changed: app.py                                         │", FG),
            ("╰────────────────────────────────────────────────────────────────╯", BORDER),
        ],
        "pause": 8,
        "instant": True,
    },
    # ── Step 6 ──
    {
        "lines": [
            ("", FG),
            ("  [6/6] Re-running tests to verify fix...", CYAN),
        ],
        "pause": 14,
    },
    {
        "lines": [
            ("", FG),
            ("╭──────── BEFORE ────────╮  ╭───────── AFTER ────────╮", BORDER),
            ("│  1 failed / 4 passed   │  │  0 failed / 5 passed   │", FG),
            ("│  5 total               │  │  5 total               │", FG),
            ("╰────────────────────────╯  ╰────────────────────────╯", BORDER),
        ],
        "pause": 10,
        "instant": True,
    },
    {
        "lines": [
            ("┏━━━━━━━━━━━━━━━━━━━━━ Confidence Score ━━━━━━━━━━━━━━━━━━━━━━━━┓", GREEN),
            ("┃    ███████████████████░  95%                                    ┃", GREEN),
            ("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", GREEN),
            ("", FG),
            ("  All tests passing after fix!", GREEN),
        ],
        "pause": 10,
        "instant": True,
    },
    # ── Final ──
    {
        "lines": [
            ("", FG),
            ("╔═════════════════════════════════════════════════════════════════╗", GREEN),
            ("║  FixForward complete!                                          ║", GREEN),
            ("║  Review the branch, then push and open a PR.                   ║", GREEN),
            ("╚═════════════════════════════════════════════════════════════════╝", GREEN),
        ],
        "pause": 30,
        "instant": True,
    },
]

# Build frames
frames = []
all_lines = []

for section in sections:
    is_instant = section.get("instant", False)

    if is_instant:
        # Add all lines at once (simulates Rich panel appearing)
        all_lines.extend(section["lines"])
        scroll = max(0, len(all_lines) - MAX_VISIBLE)
        img = make_frame(all_lines, cursor=True, scroll_offset=scroll)
        frames.append(img)
    else:
        # Type out line by line
        for line in section["lines"]:
            all_lines.append(line)
            scroll = max(0, len(all_lines) - MAX_VISIBLE)
            img = make_frame(all_lines, cursor=True, scroll_offset=scroll)
            frames.append(img)

    # Pause after section
    scroll = max(0, len(all_lines) - MAX_VISIBLE)
    pause_img = make_frame(all_lines, cursor=True, scroll_offset=scroll)
    for _ in range(section["pause"]):
        frames.append(pause_img)

# Final frame without cursor, hold longer
scroll = max(0, len(all_lines) - MAX_VISIBLE)
final = make_frame(all_lines, cursor=False, scroll_offset=scroll)
for _ in range(40):
    frames.append(final)

out_path = os.path.join(os.path.dirname(__file__), "demo.gif")
imageio.mimsave(out_path, [f.copy() for f in frames], duration=0.10, loop=0)
print(f"GIF saved to {out_path} ({len(frames)} frames)")
