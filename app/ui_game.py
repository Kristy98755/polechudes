from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from app.model import GameState, normalize_letter
from app.wheel import WheelSector, WheelSpin, default_sectors


class GameWindow:
    def __init__(self, root: tk.Tk, state: GameState) -> None:
        self.state = state
        self.window = tk.Toplevel(root)
        self.window.title("Поле чудес — Игра")
        self.window.configure(bg="#0b1020")
        self.window.minsize(1100, 700)

        self._phrase_var = tk.StringVar(value="")
        self._mask_var = tk.StringVar(value="")
        self._question_var = tk.StringVar(value="")

        self._player_name_vars = [tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self._player_score_vars = [tk.StringVar(), tk.StringVar(), tk.StringVar()]

        self._build()

        self.wheel = WheelSpin(default_sectors())
        self._wheel_after: str | None = None
        self._anim_after: str | None = None

        self.state.subscribe_phrase(self._on_phrase)
        self.refresh_from_state()
        self._start_wheel_anim_loop()

    def _build(self) -> None:
        top = tk.Frame(self.window, bg="#0b1020")
        top.pack(fill="x", padx=16, pady=12)

        title = tk.Label(
            top,
            text="ПОЛЕ ЧУДЕС",
            font=("Segoe UI Black", 26),
            fg="#ffd35a",
            bg="#0b1020",
        )
        title.pack(side="left")

        self._phrase_label = tk.Label(
            top,
            textvariable=self._phrase_var,
            font=("Segoe UI", 14),
            fg="#d6e3ff",
            bg="#0b1020",
            anchor="e",
        )
        self._phrase_label.pack(side="right", fill="x", expand=True, padx=(16, 0))

        mid = tk.Frame(self.window, bg="#0b1020")
        mid.pack(fill="both", expand=True, padx=16, pady=8)

        left = tk.Frame(mid, bg="#0b1020")
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(mid, bg="#0b1020")
        right.pack(side="right", fill="y", padx=(16, 0))

        board = tk.Frame(left, bg="#0b1020")
        board.pack(fill="x", pady=(8, 12))

        q = tk.Label(
            board,
            textvariable=self._question_var,
            font=("Segoe UI", 14),
            fg="#a9c3ff",
            bg="#0b1020",
            anchor="w",
        )
        q.pack(fill="x", pady=(0, 6))

        self._mask_label = tk.Label(
            board,
            textvariable=self._mask_var,
            font=("Consolas", 34),
            fg="#eaf1ff",
            bg="#0b1020",
            anchor="center",
        )
        self._mask_label.pack(fill="x", pady=(0, 6))

        # On-screen keyboard
        kb = tk.Frame(left, bg="#0b1020")
        kb.pack(fill="x")

        self._build_keyboard(kb)

        # Players panel
        players = tk.Frame(right, bg="#0b1020")
        players.pack(fill="y")

        for i in range(3):
            card = tk.Frame(players, bg="#121a33", bd=0, highlightthickness=1, highlightbackground="#2b3a72")
            card.pack(fill="x", pady=8)

            name = tk.Label(card, textvariable=self._player_name_vars[i], font=("Segoe UI Semibold", 14), fg="#cfe0ff", bg="#121a33")
            name.pack(fill="x", padx=12, pady=(10, 2))

            score = tk.Label(card, textvariable=self._player_score_vars[i], font=("Segoe UI Black", 22), fg="#ffd35a", bg="#121a33")
            score.pack(fill="x", padx=12, pady=(0, 10))

        # Wheel canvas
        self.canvas = tk.Canvas(right, width=380, height=260, bg="#0b1020", highlightthickness=0)
        self.canvas.pack(pady=(10, 0))

        self._status_var = tk.StringVar(value="")
        st = tk.Label(right, textvariable=self._status_var, font=("Segoe UI", 11), fg="#9bb1e6", bg="#0b1020", anchor="center")
        st.pack(fill="x", pady=(8, 0))

    def _build_keyboard(self, parent: tk.Widget) -> None:
        letters_rows = [
            "ЙЦУКЕНГШЩЗХЪ",
            "ФЫВАПРОЛДЖЭ",
            "ЯЧСМИТЬБЮ",
        ]
        for r, row in enumerate(letters_rows):
            fr = tk.Frame(parent, bg="#0b1020")
            fr.pack(fill="x", pady=4)
            for ch in row:
                b = tk.Button(
                    fr,
                    text=ch,
                    width=3,
                    font=("Segoe UI", 14),
                    relief="flat",
                    bg="#1a2550",
                    fg="#eaf1ff",
                    activebackground="#24326a",
                    activeforeground="#ffffff",
                    command=lambda c=ch: self.on_letter(c),
                )
                b.pack(side="left", padx=2)

        fr2 = tk.Frame(parent, bg="#0b1020")
        fr2.pack(fill="x", pady=(6, 0))
        btn = tk.Button(
            fr2,
            text="Открыть пробел/разделитель",
            font=("Segoe UI", 11),
            relief="flat",
            bg="#151d3a",
            fg="#cfe0ff",
            activebackground="#1b254a",
            activeforeground="#ffffff",
            command=self.refresh_from_state,
        )
        btn.pack(side="left", padx=2)

    def refresh_from_state(self) -> None:
        p = self.state.current_puzzle()
        self._question_var.set(p.question if p else "Сначала добавьте вопрос/слово в пульте управления.")
        self._mask_var.set(self.state.guess_mask or "—")

        for i, pl in enumerate(self.state.current_trio.players[:3]):
            self._player_name_vars[i].set(pl.name)
            self._player_score_vars[i].set(str(pl.score))

    def on_letter(self, letter: str) -> None:
        letter = normalize_letter(letter)
        if not letter:
            return
        n = self.state.try_reveal_letter(letter)
        if n:
            self.refresh_from_state()

    # -------------------- wheel drawing --------------------
    def _start_wheel_anim_loop(self) -> None:
        self._tick_wheel()

    def _tick_wheel(self) -> None:
        # 60 FPS-ish
        self.wheel.step(1 / 60)
        self._draw_wheel()
        self._anim_after = self.window.after(16, self._tick_wheel)

    def _draw_wheel(self) -> None:
        c = self.canvas
        c.delete("all")

        w = int(c["width"])
        h = int(c["height"])

        cx = w // 2
        cy = h // 2 + 10

        # cylinder top ellipse
        rx = 150
        ry = 52
        body_h = 90

        # body shadow
        c.create_oval(cx - rx, cy - ry + body_h, cx + rx, cy + ry + body_h, fill="#10162e", outline="")
        c.create_rectangle(cx - rx, cy, cx + rx, cy + body_h, fill="#18224a", outline="")

        # top surface
        c.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, fill="#22306a", outline="#3b4da0", width=2)

        # perspective ring "texture": draw ticked sectors along ellipse perimeter
        n = len(self.wheel.sectors)
        for i, sec in enumerate(self.wheel.sectors):
            ang = (i / n) * 2 * math.pi - self.wheel.angle
            # point on ellipse perimeter (front gets thicker)
            x = cx + rx * math.sin(ang)
            y = cy - ry * math.cos(ang)
            front = (math.cos(ang) + 1) / 2  # 0..1
            thickness = 2 + 5 * front
            col = _sector_color(sec, front)
            c.create_line(cx, cy, x, y, fill="#2a3a7a", width=1)
            c.create_oval(x - thickness, y - thickness, x + thickness, y + thickness, fill=col, outline="")

            if front > 0.72:
                # label only for visible-front sectors
                c.create_text(
                    x,
                    y - 16,
                    text=sec.label,
                    fill="#eaf1ff",
                    font=("Segoe UI Semibold", 10),
                )

        # pointer
        c.create_polygon(
            cx,
            cy - ry - 10,
            cx - 14,
            cy - ry + 12,
            cx + 14,
            cy - ry + 12,
            fill="#ffd35a",
            outline="#8a6a1a",
        )

        cur = self.wheel.current_sector()
        self._status_var.set(f"Сектор: {cur.label}{' (крутится)' if self.wheel.running else ''}")

    def start_spin(self, on_stop=None) -> None:
        self.wheel.start(on_stop=on_stop)

    def emergency_stop(self) -> WheelSector:
        return self.wheel.emergency_stop()

    def _on_phrase(self, phrase: str) -> None:
        self._phrase_var.set(phrase)
        # auto-clear after a bit
        self.window.after(4000, lambda: self._phrase_var.set(""))


def _sector_color(sec: WheelSector, front: float) -> str:
    # simple palette: warmer on front to simulate light
    if sec.kind == "bankrupt":
        base = (210, 60, 60)
    elif sec.kind == "prize":
        base = (60, 180, 120)
    elif sec.kind in ("x2", "x3", "plus"):
        base = (80, 140, 230)
    elif sec.kind == "pass":
        base = (160, 160, 160)
    else:
        base = (230, 180, 70)

    k = 0.65 + 0.35 * front
    r = int(base[0] * k)
    g = int(base[1] * k)
    b = int(base[2] * k)
    return f"#{r:02x}{g:02x}{b:02x}"

