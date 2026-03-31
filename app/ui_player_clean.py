from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps
from PIL import ImageTk

from app.external_assets import ensure_external_assets


@dataclass
class CleanTheme:
    bg: str = "#2d97bd"  # cheerful cyan like TV UI
    panel_white: str = "#ffffff"
    panel_border: str = "#1b2a35"
    text_black: str = "#111111"
    board_bg: str = "#eaf4fb"
    cell_border: str = "#98b7cc"
    cell_hidden: str = "#2b2a57"
    key_bg: str = "#f3f6f9"
    key_border: str = "#9fb2c2"
    key_active: str = "#dfeaf2"


class PlayerWindowClean:
    """
    UI-only player window, rebuilt from scratch per requested layout:
    - Top: question (black on white)
    - Under: board with revealable letters (UI only)
    - Middle: 3 players + wheel + host (images)
    - Bottom: on-screen keyboard
    """

    def __init__(self, root: tk.Tk) -> None:
        self.theme = CleanTheme()
        self.window = tk.Toplevel(root)
        self.window.title("Поле чудес — UI (игрок)")
        self.window.configure(bg=self.theme.bg)
        self.window.minsize(1200, 760)

        self._assets = ensure_external_assets(Path(__file__).resolve().parents[1])
        self._img_refs: list[ImageTk.PhotoImage] = []

        self._question_var = tk.StringVar(
            value="История о Маугли утверждает, что эта кошка наряду с волками взяла на себя нелегкую функцию воспитания «человеческого детеныша»."
        )
        self._answer = "БАГИРА"
        self._mask = "•АГ•РА"

        # wheel animation frames
        self._wheel_frames: list[ImageTk.PhotoImage] = []
        self._wheel_frame_idx = 0
        self._wheel_running = False
        self._wheel_after: str | None = None

        self._build()
        self._prepare_images()
        self._draw_scene()

    # -------------------- layout --------------------
    def _build(self) -> None:
        top = tk.Frame(self.window, bg=self.theme.bg)
        top.pack(fill="x", padx=18, pady=(16, 10))

        q = tk.Label(
            top,
            textvariable=self._question_var,
            bg=self.theme.panel_white,
            fg=self.theme.text_black,
            font=("Segoe UI", 16),
            wraplength=1040,
            justify="center",
            relief="solid",
            bd=2,
            padx=16,
            pady=10,
        )
        q.pack(fill="x")

        mid = tk.Frame(self.window, bg=self.theme.bg)
        mid.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        # board
        self.board = tk.Canvas(mid, height=140, bg=self.theme.bg, highlightthickness=0)
        self.board.pack(fill="x", pady=(0, 10))

        # scene
        self.scene = tk.Canvas(mid, bg=self.theme.bg, highlightthickness=0)
        self.scene.pack(fill="both", expand=True)

        bottom = tk.Frame(self.window, bg=self.theme.bg)
        bottom.pack(fill="x", padx=18, pady=(0, 16))

        self.keyboard = tk.Frame(bottom, bg=self.theme.bg)
        self.keyboard.pack(fill="x")

        self._build_keyboard()

        self.window.bind("<Configure>", lambda _e: (self._draw_board(), self._draw_scene()))

    def _build_keyboard(self) -> None:
        rows = ["ЙЦУКЕНГШЩЗХЪ", "ФЫВАПРОЛДЖЭ", "ЯЧСМИТЬБЮ"]
        for row in rows:
            fr = tk.Frame(self.keyboard, bg=self.theme.bg)
            fr.pack(pady=4)
            for ch in row:
                b = tk.Button(
                    fr,
                    text=ch,
                    width=3,
                    font=("Segoe UI", 14),
                    bg=self.theme.key_bg,
                    fg=self.theme.text_black,
                    relief="solid",
                    bd=1,
                    activebackground=self.theme.key_active,
                    command=lambda c=ch: self._on_key(c),
                )
                b.pack(side="left", padx=2)

    # -------------------- images --------------------
    def _prepare_images(self) -> None:
        # prepare wheel frames (pre-rotate)
        wheel_path = self._assets.get("wheel")
        if wheel_path:
            base = Image.open(wheel_path).convert("RGBA")
            base = ImageOps.contain(base, (520, 360))
            # circular-ish crop not required; keep as is and rotate in place
            for deg in range(0, 360, 10):
                fr = base.rotate(deg, resample=Image.BICUBIC, expand=True)
                fr = ImageOps.contain(fr, (520, 360))
                self._wheel_frames.append(ImageTk.PhotoImage(fr))

        # player icon (same image reused for 3)
        self._player_img = None
        p = self._assets.get("player_icon")
        if p:
            im = Image.open(p).convert("RGBA")
            im = ImageOps.contain(im, (160, 220))
            self._player_img = ImageTk.PhotoImage(im)

        # host image
        self._host_img = None
        hp = self._assets.get("host")
        if hp:
            im = Image.open(hp).convert("RGBA")
            im = ImageOps.contain(im, (260, 340))
            self._host_img = ImageTk.PhotoImage(im)

    # -------------------- draw --------------------
    def _draw_board(self) -> None:
        c = self.board
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())

        pad = 10
        x0, y0, x1, y1 = pad, pad, w - pad, h - pad
        c.create_rectangle(x0, y0, x1, y1, fill=self.theme.board_bg, outline=self.theme.panel_border, width=2)

        cols = 14
        rows = 2
        gx0, gy0, gx1, gy1 = x0 + 18, y0 + 18, x1 - 18, y1 - 18
        cell_w = (gx1 - gx0) / cols
        cell_h = (gy1 - gy0) / rows

        # place mask centered in bottom row
        text = self._mask.replace(" ", "")
        start = max(0, (cols - len(text)) // 2)
        row_idx = 1

        for r in range(rows):
            for col in range(cols):
                cx0 = gx0 + col * cell_w
                cy0 = gy0 + r * cell_h
                cx1 = cx0 + cell_w - 2
                cy1 = cy0 + cell_h - 2
                c.create_rectangle(
                    int(cx0),
                    int(cy0),
                    int(cx1),
                    int(cy1),
                    fill="#ffffff",
                    outline=self.theme.cell_border,
                    width=1,
                )
                if r == row_idx and start <= col < start + len(text):
                    ch = text[col - start]
                    if ch == "•":
                        c.create_rectangle(int(cx0) + 1, int(cy0) + 1, int(cx1) - 1, int(cy1) - 1, fill=self.theme.cell_hidden, outline="")
                    else:
                        c.create_text(int((cx0 + cx1) / 2), int((cy0 + cy1) / 2), text=ch, fill="#0b1220", font=("Segoe UI Black", int(cell_h * 0.60)))

    def _draw_scene(self) -> None:
        c = self.scene
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())

        # simple friendly stage gradient
        for i in range(18):
            y0 = int(i * h / 18)
            y1 = int((i + 1) * h / 18)
            col = _mix(self.theme.bg, "#0f3d52", i / 17)
            c.create_rectangle(0, y0, w, y1, fill=col, outline="")

        # players (3) left-to-center
        names = ["Виктория", "Андрей", "Егор"]
        xs = [int(w * 0.16), int(w * 0.28), int(w * 0.40)]
        ground = int(h * 0.70)
        for i in range(3):
            c.create_text(xs[i], int(h * 0.14), text=names[i], fill="#0b1220", font=("Segoe UI Semibold", 14))
            if self._player_img:
                self._img_refs.append(self._player_img)
                c.create_image(xs[i], ground, image=self._player_img, anchor="s")
            else:
                # fallback: simple stick figure
                c.create_oval(xs[i] - 22, ground - 170, xs[i] + 22, ground - 126, fill="#ffffff", outline="#0b1220")
                c.create_line(xs[i], ground - 126, xs[i], ground - 58, fill="#0b1220", width=6)
                c.create_line(xs[i], ground - 100, xs[i] - 26, ground - 82, fill="#0b1220", width=6)
                c.create_line(xs[i], ground - 100, xs[i] + 26, ground - 82, fill="#0b1220", width=6)

        # wheel center-left
        wheel_x = int(w * 0.46)
        wheel_y = int(h * 0.66)
        if self._wheel_frames:
            img = self._wheel_frames[self._wheel_frame_idx % len(self._wheel_frames)]
            self._img_refs.append(img)
            c.create_image(wheel_x, wheel_y, image=img, anchor="s")
            # click hint pointer
            c.create_polygon(wheel_x + 240, wheel_y - 120, wheel_x + 272, wheel_y - 104, wheel_x + 240, wheel_y - 88, fill="#d12f2f", outline="#7a1f1f")
            c.create_rectangle(wheel_x - 260, wheel_y - 40, wheel_x + 260, wheel_y + 16, outline="#0b1220")
        else:
            c.create_oval(wheel_x - 180, wheel_y - 120, wheel_x + 180, wheel_y + 40, fill="#ffffff", outline="#0b1220", width=2)

        # host on the right of wheel
        host_x = int(w * 0.78)
        if self._host_img:
            self._img_refs.append(self._host_img)
            c.create_image(host_x, ground + 10, image=self._host_img, anchor="s")
        else:
            c.create_oval(host_x - 40, ground - 180, host_x + 40, ground - 100, fill="#ffffff", outline="#0b1220", width=2)
            c.create_rectangle(host_x - 50, ground - 100, host_x + 50, ground + 10, fill="#ffffff", outline="#0b1220", width=2)

        # bind click to spin (wheel area)
        c.tag_bind("all", "<Button-1>", self._on_scene_click)

    # -------------------- interactions (UI-only) --------------------
    def _on_key(self, ch: str) -> None:
        # UI-only: reveal if present
        ch = (ch or "").strip().upper()
        if not ch:
            return
        ch = "Е" if ch == "Ё" else ch
        new = []
        for a, m in zip(self._answer, self._mask):
            if a == ch:
                new.append(ch)
            else:
                new.append(m)
        self._mask = "".join(new)
        self._draw_board()

    def _on_scene_click(self, _e) -> None:
        # we bind actual click handler below; keep placeholder
        return

    def _on_scene_click(self, e) -> None:  # type: ignore[no-redef]
        # click near wheel starts/stops spin
        w = max(1, self.scene.winfo_width())
        h = max(1, self.scene.winfo_height())
        wheel_x = int(w * 0.46)
        wheel_y = int(h * 0.66)
        if abs(e.x - wheel_x) < 280 and abs(e.y - wheel_y) < 220:
            self._wheel_running = True
            self._wheel_kick()

    def _wheel_kick(self) -> None:
        if not self._wheel_running or not self._wheel_frames:
            return
        # simple constant-speed loop for now (UI-only)
        self._wheel_frame_idx = (self._wheel_frame_idx + 1) % len(self._wheel_frames)
        self._draw_scene()
        self._wheel_after = self.window.after(30, self._wheel_kick)


def _mix(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

