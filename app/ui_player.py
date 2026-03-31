from __future__ import annotations

import math
from pathlib import Path
import tkinter as tk
from dataclasses import dataclass

from app.assets import load_sprites
from app.model import GameState, Puzzle, normalize_answer
from app.wheel import WheelSpin, default_sectors


@dataclass
class PlayerUiTheme:
    bg: str = "#1d2b3a"
    floor_dark: str = "#15212e"
    floor_light: str = "#22384b"
    board_frame: str = "#caa343"
    board_bg: str = "#b9d8ee"
    board_cell: str = "#d8edf8"
    board_cell_border: str = "#88a7bf"
    board_cell_hidden: str = "#2a2850"
    hud_bg: str = "#1d242c"
    hud_border: str = "#3b454f"
    hud_text: str = "#e9f1f7"
    accent_yellow: str = "#f2c230"
    accent_green: str = "#3aa45c"
    accent_red: str = "#d14d4d"
    panel_shadow: str = "#0e141b"
    wheel_top: str = "#f3f4f6"
    wheel_dark: str = "#121417"
    wheel_light: str = "#f8f9fa"
    wheel_outline: str = "#2b333c"
    wheel_base: str = "#77838f"
    wheel_base_dark: str = "#66727e"
    wheel_highlight: str = "#909aa5"
    shadow: str = "#0c1218"


class PlayerWindow:
    """
    "Витринный" интерфейс игрока (без бэкенда).
    Максимально приближаем композицию к референсу: сцена, табло, игроки, барабан, нижняя плашка вопроса.
    """

    def __init__(self, root: tk.Tk, state: GameState) -> None:
        self.state = state
        self.theme = PlayerUiTheme()

        self.window = tk.Toplevel(root)
        self.window.title("Поле чудес — Окно игрока")
        self.window.configure(bg=self.theme.bg)
        self.window.minsize(1180, 720)

        self.canvas = tk.Canvas(self.window, bg=self.theme.bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.window.bind("<Configure>", lambda _e: self._draw())
        self.canvas.bind("<Button-1>", self._on_click)

        self.wheel = WheelSpin(default_sectors())
        self._anim_after: str | None = None
        self._sprite_refs: list[tk.PhotoImage] = []
        self.sprites = load_sprites(Path(__file__).resolve().parents[1], max_width=520, max_height=560)

        self._install_mock_data()
        self._start_anim()

    def _install_mock_data(self) -> None:
        # mock trio
        self.state.current_trio.players[0].name = "Виктория"
        self.state.current_trio.players[1].name = "Андрей"
        self.state.current_trio.players[2].name = "Егор"
        self.state.current_trio.players[0].score = 1350
        self.state.current_trio.players[1].score = 600
        self.state.current_trio.players[2].score = 1500

        # mock puzzle
        q = "История о Маугли утверждает, что эта кошка наряду с волками взяла на себя нелегкую функцию воспитания «человеческого детеныша»."
        a = normalize_answer("БАГИРА")
        if not self.state.puzzles:
            self.state.add_puzzle(Puzzle(question=q, answer=a, explanation="", category="regular"))
        self.state.set_current_puzzle(0)

        # reveal some letters to show board
        for ch in ("А", "Г", "Р"):
            self.state.revealed_letters.add(ch)
        self.state._recompute_mask()  # internal: ok for mock mode

    def _start_anim(self) -> None:
        self._tick()

    def _tick(self) -> None:
        self.wheel.step(1 / 60)
        self._draw()
        self._anim_after = self.window.after(16, self._tick)

    def _on_click(self, e) -> None:
        # click on wheel area starts spin
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        wheel_bbox = self._wheel_bbox(w, h)
        if wheel_bbox[0] <= e.x <= wheel_bbox[2] and wheel_bbox[1] <= e.y <= wheel_bbox[3]:
            if not self.wheel.running:
                self.wheel.start()

    # -------------------- drawing --------------------
    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")

        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())

        self._draw_background(c, w, h)
        self._draw_board(c, w, h)
        self._draw_players(c, w, h)
        self._draw_wheel(c, w, h)
        self._draw_host(c, w, h)
        self._draw_bottom_hud(c, w, h)

    def _draw_background(self, c: tk.Canvas, w: int, h: int) -> None:
        # subtle vertical gradient by stripes (cheap)
        for i in range(0, 32):
            y0 = int(i * h / 32)
            y1 = int((i + 1) * h / 32)
            k = i / 31
            col = _mix("#0f1722", self.theme.bg, 0.35 + 0.65 * k)
            c.create_rectangle(0, y0, w, y1, fill=col, outline="")

        # "floor" tiles
        floor_top = int(h * 0.52)
        c.create_rectangle(0, floor_top, w, h, fill=self.theme.floor_dark, outline="")
        step = max(40, int(w / 18))
        for x in range(0, w + step, step):
            c.create_line(x, floor_top, x, h, fill="#0c141d")
        for y in range(floor_top, h, step):
            c.create_line(0, y, w, y, fill="#0c141d")

        # back wall vertical columns (right)
        col_x0 = int(w * 0.72)
        for i in range(6):
            x0 = col_x0 + i * int(w * 0.045)
            x1 = x0 + int(w * 0.03)
            if x1 > w:
                break
            c.create_rectangle(x0, int(h * 0.06), x1, int(h * 0.48), fill="#cbb88a", outline="#b29f75")

    def _board_bbox(self, w: int, h: int) -> tuple[int, int, int, int]:
        x0 = int(w * 0.36)
        y0 = int(h * 0.08)
        x1 = int(w * 0.82)
        y1 = int(h * 0.36)
        return x0, y0, x1, y1

    def _draw_board(self, c: tk.Canvas, w: int, h: int) -> None:
        x0, y0, x1, y1 = self._board_bbox(w, h)
        pad = 10

        # frame
        c.create_rectangle(x0, y0, x1, y1, fill=self.theme.board_bg, outline=self.theme.board_frame, width=10)
        c.create_rectangle(x0 + pad, y0 + pad, x1 - pad, y1 - pad, fill=self.theme.board_bg, outline="#6d879c", width=2)

        # grid
        cols = 12
        rows = 3
        gx0, gy0, gx1, gy1 = x0 + 22, y0 + 22, x1 - 22, y1 - 22
        cell_w = (gx1 - gx0) / cols
        cell_h = (gy1 - gy0) / rows

        answer = self.state.current_puzzle().answer if self.state.current_puzzle() else ""
        mask = self.state.guess_mask if self.state.guess_mask else ""
        # place answer into middle row (like many game UIs)
        # for mock: render mask centered
        text = mask if mask else "•" * min(8, cols)
        text = text.replace(" ", "")
        start_col = max(0, (cols - len(text)) // 2)
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
                    fill=self.theme.board_cell,
                    outline=self.theme.board_cell_border,
                    width=1,
                )

                ch = ""
                hidden = False
                if r == row_idx and start_col <= col < start_col + len(text):
                    ch = text[col - start_col]
                    hidden = (ch == "•")

                if hidden:
                    c.create_rectangle(
                        int(cx0) + 1,
                        int(cy0) + 1,
                        int(cx1) - 1,
                        int(cy1) - 1,
                        fill=self.theme.board_cell_hidden,
                        outline="",
                    )
                elif ch and ch != "•":
                    c.create_text(
                        int((cx0 + cx1) / 2),
                        int((cy0 + cy1) / 2),
                        text=ch,
                        fill="#0f1722",
                        font=("Segoe UI Black", int(cell_h * 0.55)),
                    )

    def _draw_players(self, c: tk.Canvas, w: int, h: int) -> None:
        # podium / players area (left)
        base_x = int(w * 0.14)
        base_y = int(h * 0.34)
        podium_w = int(w * 0.28)
        podium_h = int(h * 0.22)

        # podium top
        c.create_polygon(
            base_x,
            base_y,
            base_x + podium_w,
            base_y,
            base_x + int(podium_w * 0.92),
            base_y + int(podium_h * 0.32),
            base_x + int(podium_w * 0.08),
            base_y + int(podium_h * 0.32),
            fill="#5c6a7b",
            outline="#2e3a47",
            width=2,
        )
        # podium front
        c.create_polygon(
            base_x + int(podium_w * 0.08),
            base_y + int(podium_h * 0.32),
            base_x + int(podium_w * 0.92),
            base_y + int(podium_h * 0.32),
            base_x + podium_w,
            base_y + podium_h,
            base_x,
            base_y + podium_h,
            fill="#445160",
            outline="#2e3a47",
            width=2,
        )

        # score boxes on podium
        scores = [p.score for p in self.state.current_trio.players[:3]]
        names = [p.name for p in self.state.current_trio.players[:3]]

        for i in range(3):
            bx0 = base_x + int(podium_w * (0.12 + i * 0.28))
            by0 = base_y + int(podium_h * 0.18)
            bw = int(podium_w * 0.22)
            bh = int(podium_h * 0.18)
            c.create_rectangle(bx0, by0, bx0 + bw, by0 + bh, fill="#11161c", outline="#2f3842", width=2)
            c.create_text(
                bx0 + bw // 2,
                by0 + bh // 2,
                text=f"{scores[i]:07d}",
                fill="#e9f1f7",
                font=("Consolas", int(bh * 0.55), "bold"),
            )

        # player "silhouettes" + names above
        y_names = int(h * 0.095)
        xs = [int(w * 0.18), int(w * 0.30), int(w * 0.42)]
        for i in range(3):
            c.create_text(xs[i], y_names, text=names[i], fill="#ffd35a", font=("Segoe UI Semibold", 14))
            spr = [self.sprites.player1, self.sprites.player2, self.sprites.player3][i]
            if spr is not None:
                self._sprite_refs.append(spr)
                c.create_image(xs[i], int(h * 0.28), image=spr, anchor="s")
            else:
                self._draw_player_vector(c, xs[i], int(h * 0.30), scale=max(0.8, w / 1400))

    def _draw_player_vector(self, c: tk.Canvas, x: int, y: int, *, scale: float) -> None:
        # Nicer placeholder: rounded body, neck, subtle shading, simple face.
        head_r = int(36 * scale)
        body_w = int(78 * scale)
        body_h = int(110 * scale)

        # shadow
        c.create_oval(x - body_w // 2, y + body_h - 6, x + body_w // 2, y + body_h + 10, fill="#0b121a", outline="")

        # head
        c.create_oval(x - head_r, y - body_h - head_r, x + head_r, y - body_h + head_r, fill="#f1caa6", outline="")
        # hair
        c.create_arc(x - head_r, y - body_h - head_r - 10, x + head_r, y - body_h + head_r, start=0, extent=180, fill="#2a2e35", outline="")
        # eyes
        eye_y = y - body_h - 2
        c.create_oval(x - 12, eye_y - 6, x - 4, eye_y + 2, fill="#0f1722", outline="")
        c.create_oval(x + 4, eye_y - 6, x + 12, eye_y + 2, fill="#0f1722", outline="")

        # neck
        _rounded_rect(c, x - int(14 * scale), y - body_h + head_r - 6, x + int(14 * scale), y - body_h + head_r + 10, int(6 * scale), fill="#e7bfa0", outline="")

        # body (rounded)
        _rounded_rect(
            c,
            x - body_w // 2,
            y - body_h + head_r + 6,
            x + body_w // 2,
            y + body_h,
            int(14 * scale),
            fill="#2f5571",
            outline="#21384a",
            width=2,
        )
        # simple highlight stripe
        c.create_rectangle(x - body_w // 2 + 10, y - body_h + head_r + 16, x - body_w // 2 + 18, y + body_h - 10, fill="#3a6a8b", outline="")

    def _wheel_bbox(self, w: int, h: int) -> tuple[int, int, int, int]:
        x0 = int(w * 0.13)
        y0 = int(h * 0.46)
        x1 = int(w * 0.55)
        y1 = int(h * 0.76)
        return x0, y0, x1, y1

    def _draw_wheel(self, c: tk.Canvas, w: int, h: int) -> None:
        x0, y0, x1, y1 = self._wheel_bbox(w, h)

        # Single geometry: cylinder top ellipse == sector disc ellipse.
        wheel_w = x1 - x0
        wheel_h = y1 - y0
        top_y0 = y0 + int(wheel_h * 0.10)
        top_y1 = y0 + int(wheel_h * 0.52)
        body_y0 = top_y1 - int(wheel_h * 0.06)
        body_y1 = y1

        # shadow under wheel
        c.create_oval(x0 + 22, y1 - 10, x1 - 14, y1 + 28, fill=self.theme.shadow, outline="")

        # cylinder body
        c.create_rectangle(x0 + 6, body_y0, x1 - 6, body_y1, fill=self.theme.wheel_base_dark, outline=self.theme.wheel_outline, width=2)
        c.create_oval(x0 + 6, body_y1 - 26, x1 - 6, body_y1 + 26, fill=self.theme.wheel_base_dark, outline=self.theme.wheel_outline, width=2)

        # top lip + highlight
        c.create_oval(x0, top_y0, x1, top_y1, fill=self.theme.wheel_highlight, outline=self.theme.wheel_outline, width=2)
        c.create_oval(x0 + 8, top_y0 + 8, x1 - 8, top_y1 - 8, fill=self.theme.wheel_top, outline=self.theme.wheel_outline, width=2)

        # sectors on the same ellipse (alternating black/white, labels near edge)
        n = len(self.wheel.sectors)
        # Tk's create_arc draws from 0 degrees at 3 o'clock, counterclockwise
        # We'll map wheel.angle (radians) so that pointer is near bottom-right like reference
        angle_deg = (self.wheel.angle * 180 / math.pi) % 360
        start = 110 - angle_deg
        extent = 360 / n
        for i, sec in enumerate(self.wheel.sectors):
            is_dark = (i % 2 == 0)
            fill = self.theme.wheel_dark if is_dark else self.theme.wheel_light
            c.create_arc(
                x0 + 18,
                top_y0 + 18,
                x1 - 18,
                top_y1 - 18,
                start=start + i * extent,
                extent=extent,
                fill=fill,
                outline="#1f252c",
                width=1,
            )

            # label positions: near edge of ellipse
            mid = math.radians((start + i * extent + extent / 2) % 360)
            cx = (x0 + x1) / 2
            cy = (top_y0 + top_y1) / 2
            rx = (x1 - x0) * 0.36
            ry = (top_y1 - top_y0) * 0.36
            lx = cx + rx * math.cos(mid)
            ly = cy - ry * math.sin(mid)
            col = "#ffffff" if is_dark else "#0f1722"
            c.create_text(int(lx), int(ly), text=sec.label, fill=col, font=("Segoe UI Semibold", 9))

        # hub
        cx = (x0 + x1) / 2
        cy = (top_y0 + top_y1) / 2
        c.create_oval(cx - 20, cy - 20, cx + 20, cy + 20, fill="#0f1722", outline="#3a4652", width=2)
        c.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#2a333c", outline="")

        # pointer (right side)
        px = int(x1 - 8)
        py = int((top_y0 + top_y1) / 2 + 18)
        c.create_polygon(
            px,
            py,
            px + 36,
            py + 14,
            px,
            py + 28,
            fill="#c23b3b",
            outline="#7a1f1f",
        )

    def _draw_host(self, c: tk.Canvas, w: int, h: int) -> None:
        x = int(w * 0.88)
        y = int(h * 0.47)
        if self.sprites.host is not None:
            self._sprite_refs.append(self.sprites.host)
            c.create_image(x, y, image=self.sprites.host, anchor="s")
            return

        # improved vector placeholder (no real-person identification)
        scale = max(0.9, w / 1400)
        head_r = int(w * 0.052 * scale)
        head_y = y - int(h * 0.20 * scale)
        c.create_oval(x - head_r, head_y - head_r, x + head_r, head_y + head_r, fill="#f1caa6", outline="")
        c.create_arc(x - head_r, head_y - head_r - 10, x + head_r, head_y + head_r, start=0, extent=180, fill="#9ea4ab", outline="")
        c.create_oval(x - int(head_r * 0.52), head_y + 6, x + int(head_r * 0.52), head_y + 22, fill="#5c4a40", outline="")
        body_w = int(head_r * 1.8)
        body_h = int(h * 0.24 * scale)
        c.create_rectangle(x - body_w // 2, head_y + head_r - 2, x + body_w // 2, head_y + head_r + body_h, fill="#2f4c62", outline="#203646", width=2)
        c.create_polygon(x, head_y + head_r + 18, x - 18, head_y + head_r + 42, x + 18, head_y + head_r + 42, fill="#b33636", outline="")
        mx = x - 28
        my = head_y + head_r + 92
        c.create_oval(mx - 22, my - 22, mx + 22, my + 22, fill="#21262c", outline="#404b55", width=2)
        c.create_line(mx, my + 18, mx + 12, my + 48, fill="#1b2026", width=6)

    def _draw_bottom_hud(self, c: tk.Canvas, w: int, h: int) -> None:
        hud_h = int(h * 0.18)
        y0 = h - hud_h
        c.create_rectangle(0, y0, w, h, fill=self.theme.hud_bg, outline=self.theme.hud_border, width=2)
        c.create_line(0, y0, w, y0, fill=self.theme.panel_shadow, width=6)

        # round badge (left)
        badge_w = int(w * 0.13)
        c.create_rectangle(0, y0, badge_w, h, fill="#12181f", outline=self.theme.hud_border, width=2)
        c.create_text(int(badge_w * 0.46), y0 + int(hud_h * 0.58), text="2-й\nРАУНД", fill=self.theme.accent_yellow, font=("Segoe UI Black", 20), justify="center")

        # question bar
        qx0 = badge_w + 12
        qx1 = int(w * 0.78)
        qy0 = y0 + 18
        qy1 = h - 18
        c.create_rectangle(qx0, qy0, qx1, qy1, fill="#262f38", outline="#4a5663", width=2)
        question = self.state.current_puzzle().question if self.state.current_puzzle() else "—"
        c.create_text(
            int((qx0 + qx1) / 2),
            int((qy0 + qy1) / 2),
            text=question,
            fill=self.theme.hud_text,
            font=("Segoe UI", 14),
            width=int((qx1 - qx0) * 0.92),
            justify="center",
        )

        # say-word button area (right)
        bx0 = qx1 + 12
        bx1 = w - 12
        c.create_rectangle(bx0, qy0, bx1, qy1, fill="#1a222a", outline="#4a5663", width=2)

        # "Сказать слово" button look
        btn_w = int((bx1 - bx0) * 0.55)
        btn_h = int((qy1 - qy0) * 0.42)
        px = bx0 + int((bx1 - bx0) * 0.18)
        py = qy0 + int((qy1 - qy0) * 0.52)
        c.create_rectangle(px, py, px + btn_w, py + btn_h, fill="#2a6a3c", outline="#164123", width=2)
        c.create_text(px + btn_w // 2, py + btn_h // 2, text="Сказать\nслово", fill="#e9f1f7", font=("Segoe UI Semibold", 14), justify="center")

        # little score digits mock (like reference)
        digits = "4224300"
        dx0 = bx0 + int((bx1 - bx0) * 0.12)
        dy0 = qy0 + 18
        cell = int(min(38, (bx1 - bx0) * 0.10))
        for i, d in enumerate(digits):
            x = dx0 + i * (cell + 4)
            if x + cell > bx1 - 10:
                break
            c.create_rectangle(x, dy0, x + cell, dy0 + cell, fill="#f1f1f1", outline="#c9c9c9")
            c.create_text(x + cell // 2, dy0 + cell // 2, text=d, fill="#1a222a", font=("Segoe UI Black", 16))


def _mix(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _rounded_rect(c: tk.Canvas, x0: int, y0: int, x1: int, y1: int, r: int, **kwargs) -> None:
    r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    if r == 0:
        c.create_rectangle(x0, y0, x1, y1, **kwargs)
        return
    c.create_arc(x0, y0, x0 + 2 * r, y0 + 2 * r, start=90, extent=90, style="pieslice", **kwargs)
    c.create_arc(x1 - 2 * r, y0, x1, y0 + 2 * r, start=0, extent=90, style="pieslice", **kwargs)
    c.create_arc(x1 - 2 * r, y1 - 2 * r, x1, y1, start=270, extent=90, style="pieslice", **kwargs)
    c.create_arc(x0, y1 - 2 * r, x0 + 2 * r, y1, start=180, extent=90, style="pieslice", **kwargs)
    c.create_rectangle(x0 + r, y0, x1 - r, y1, **kwargs)
    c.create_rectangle(x0, y0 + r, x1, y1 - r, **kwargs)


