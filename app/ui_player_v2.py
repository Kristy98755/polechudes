from __future__ import annotations

import math
import random
from pathlib import Path

from app.wheel import default_sectors, WheelSector
import tkinter as tk
from dataclasses import dataclass


@dataclass(frozen=True)
class V2Theme:
    bg_top: str = "#2fa7d8"
    bg_bottom: str = "#0a5a7c"
    question_bg: str = "#ffffff"
    question_border: str = "#0b1f2a"
    question_text: str = "#101010"

    board_bg: str = "#f4fbff"
    board_border: str = "#0b1f2a"
    cell_bg: str = "#ffffff"
    cell_border: str = "#93b8cc"
    cell_hidden: str = "#2a2a55"
    cell_text: str = "#0b1f2a"

    key_bg: str = "#f1f6fb"
    key_border: str = "#6e97ad"
    key_text: str = "#0b1f2a"
    key_active: str = "#dbeaf5"

    # Wheel palette closer to classic white-blue look
    wheel_base: str = "#7a8793"
    wheel_base_dark: str = "#66727d"
    wheel_rim: str = "#e9eef2"      # light grey ring
    wheel_rim2: str = "#d7dee5"     # inner ring shadow
    wheel_top: str = "#fdfefe"
    wheel_dark: str = "#0f1722"
    wheel_light: str = "#ffffff"
    wheel_light2: str = "#f3f7fb"
    wheel_label_blue: str = "#1c3f93"
    wheel_disc_blue: str = "#0b58d0"
    wheel_disc_blue2: str = "#0a4ab0"
    wheel_gold: str = "#f2c230"
    wheel_gold2: str = "#c79b1a"
    wheel_outline: str = "#0b1f2a"
    pointer: str = "#d33131"

    skin: str = "#f2c7a0"
    suit: str = "#2f5f7a"
    suit_dark: str = "#23485d"
    hair_grey: str = "#9da6ad"
    hair_dark: str = "#343b43"
    moustache: str = "#5c463a"
    shadow: str = "#06141b"


class PlayerWindowV2:
    """
    UI-only. Игроки — блоки в духе Minecraft (Стив), ведущий — PNG из assets/host_yakubovich.png.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.theme = V2Theme()
        self.sectors = default_sectors()
        self._image_refs: list[tk.PhotoImage] = []
        self._host_photo: tk.PhotoImage | None = self._load_host_sprite()
        self._steve_photo: tk.PhotoImage | None = self._load_steve_sprite()
        self.window = tk.Toplevel(root)
        self.window.title("Поле чудес — UI (игрок)")
        self.window.configure(bg=self.theme.bg_top)
        self.window.minsize(1200, 780)
        self.result_label = None
        self.result_flash_after = None

        self.question_var = tk.StringVar(
            value="История о Маугли утверждает, что эта кошка наряду с волками взяла на себя нелегкую функцию воспитания «человеческого детеныша»."
        )

        # mock data (UI only)
        self.player_names = ["Виктория", "Андрей", "Егор"]
        self.player_scores = [1350, 600, 1500]
        self.answer = "БАГИРА"
        self.mask = "•АГ•РА"

        # wheel animation state
        self._wheel_angle = 0.0
        self._wheel_omega = 0.0
        self._wheel_running = False
        self._after: str | None = None

        self._build()
        self._tick()

    def _load_host_sprite(self) -> tk.PhotoImage | None:
        root = Path(__file__).resolve().parents[1]
        candidates = [
            root / "assets" / "host_yakubovich.png",
            root / "assets" / "host.png",
        ]
        for path in candidates:
            if not path.is_file():
                continue
            try:
                img = tk.PhotoImage(file=str(path))
                # уменьшим, если огромный (только subsample)
                while img.width() > 220 or img.height() > 320:
                    img = img.subsample(2, 2)
                self._image_refs.append(img)
                return img
            except tk.TclError:
                continue
        return None

    def _load_steve_sprite(self) -> tk.PhotoImage | None:
        root = Path(__file__).resolve().parents[1]
        for name in ("player_steve.png", "steve.png"):
            path = root / "assets" / name
            if not path.is_file():
                continue
            try:
                img = tk.PhotoImage(file=str(path))
                # пиксель-арт: увеличиваем до читаемого роста (~130–165 px)
                while img.height() < 120:
                    img = img.zoom(2, 2)
                while img.height() > 168:
                    img = img.subsample(2, 2)
                self._image_refs.append(img)
                return img
            except tk.TclError:
                continue
        return None

    def _wheel_start_deg(self) -> float:
        """Тот же start, что в _draw_wheel (Tk: 0° = вправо, против часовой)."""
        angle_deg = (self._wheel_angle * 180 / math.pi) % 360
        return -angle_deg - 90.0

    def _pointer_tip_tk_deg(self, cx: int, cy: int, rx: int, ry: int) -> float:
        """
        Угол от центра барабана к острию указателя (как в Tk create_arc).
        Совпадает с полигоном указателя: вершина (px-4, py+10).
        """
        px = cx + rx - 6
        py = cy - int(ry * 0.15)
        tip_x = px - 4
        tip_y = py + 10
        dx = tip_x - cx
        dy = tip_y - cy
        return (math.degrees(math.atan2(-dy, dx))) % 360.0

    def _get_current_sector(self) -> WheelSector:
        n = len(self.sectors)
        if n <= 0:
            raise ValueError("no sectors")
        extent = 360.0 / n
        start = self._wheel_start_deg()

        w = max(400, self.scene.winfo_width())
        h = max(300, self.scene.winfo_height())
        cx, cy, rx, ry = self._wheel_geom(w, h)

        pointer_deg = self._pointer_tip_tk_deg(cx, cy, rx, ry)
        # Сектор i занимает [start + i*extent, start + (i+1)*extent) по окружности Tk
        rel = (pointer_deg - start) % 360.0
        idx = int(rel / extent) % n
        return self.sectors[idx]

    def _show_result(self, sector: WheelSector) -> None:
        text = sector.label
        self.result_label.config(text=text)
        self._flash_result(0)

    def _flash_result(self, count: int) -> None:
        if count >= 8:  # 4 цикла
            self.result_label.config(fg="#ffdd99")
            if self.result_flash_after:
                self.window.after_cancel(self.result_flash_after)
            self.result_flash_after = self.window.after(2000, lambda: self.result_label.config(text=""))
            return
        if count % 2 == 0:
            self.result_label.config(fg="#ffffff")
        else:
            self.result_label.config(fg="#ffdd99")
        self.result_flash_after = self.window.after(300, lambda: self._flash_result(count+1))

    def _build(self) -> None:
        top = tk.Frame(self.window, bg=self.theme.bg_top)
        top.pack(fill="x", padx=18, pady=(16, 10))

        self.question = tk.Label(
            top,
            textvariable=self.question_var,
            bg=self.theme.question_bg,
            fg=self.theme.question_text,
            font=("Segoe UI", 16),
            wraplength=1100,
            justify="center",
            relief="solid",
            bd=2,
            padx=16,
            pady=10,
            highlightthickness=0,
        )
        self.question.pack(fill="x")

        mid = tk.Frame(self.window, bg=self.theme.bg_top)
        mid.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        # ---- Фрейм для отображения выпавшего сектора ----
        result_frame = tk.Frame(mid, bg=self.theme.bg_top, height=40)
        result_frame.pack(fill="x", pady=5)
        self.result_label = tk.Label(result_frame, text="", font=("Segoe UI", 20, "bold"),
                                     bg=self.theme.bg_top, fg="#ffdd99")
        self.result_label.pack()

        self.board = tk.Canvas(mid, height=150, bg=self.theme.bg_top, highlightthickness=0)
        self.board.pack(fill="x", pady=(0, 10))

        self.scene = tk.Canvas(mid, bg=self.theme.bg_top, highlightthickness=0)
        self.scene.pack(fill="both", expand=True)
        self.scene.bind("<Button-1>", self._on_scene_click)

        bottom = tk.Frame(self.window, bg=self.theme.bg_top)
        bottom.pack(fill="x", padx=18, pady=(0, 16))

        self.keyboard = tk.Frame(bottom, bg=self.theme.bg_top)
        self.keyboard.pack(fill="x")
        self._build_keyboard()

        self.window.bind("<Configure>", lambda _e: self._redraw_all())

    def _build_keyboard(self) -> None:
        rows = ["ЙЦУКЕНГШЩЗХЪ", "ФЫВАПРОЛДЖЭ", "ЯЧСМИТЬБЮ"]
        for row in rows:
            fr = tk.Frame(self.keyboard, bg=self.theme.bg_top)
            fr.pack(pady=4)
            for ch in row:
                tk.Button(
                    fr,
                    text=ch,
                    width=5,  # шире, чем раньше (~+70%)
                    font=("Segoe UI", 14),
                    bg=self.theme.key_bg,
                    fg=self.theme.key_text,
                    relief="solid",
                    bd=1,
                    activebackground=self.theme.key_active,
                    activeforeground=self.theme.key_text,
                    command=lambda c=ch: self._on_key(c),
                ).pack(side="left", padx=2)

    # -------------------- interaction (UI only) --------------------
    def _on_key(self, ch: str) -> None:
        ch = (ch or "").strip().upper()
        if not ch:
            return
        ch = "Е" if ch == "Ё" else ch
        new = []
        for a, m in zip(self.answer, self.mask):
            new.append(ch if a == ch else m)
        self.mask = "".join(new)
        self._draw_board()

    def _on_scene_click(self, e) -> None:
        # click on wheel region toggles spin
        w = max(1, self.scene.winfo_width())
        h = max(1, self.scene.winfo_height())
        cx, cy, rx, ry = self._wheel_geom(w, h)
        if abs(e.x - cx) <= rx * 1.05 and abs(e.y - cy) <= (ry + 120):
            if not self._wheel_running:
                self._wheel_running = True
                self._wheel_omega = random.uniform(7.5, 10.5)
            else:
                # soft stop
                self._wheel_omega *= 0.35

    # -------------------- animation --------------------
    def _tick(self) -> None:
        dt = 1 / 60
        if self._wheel_running:
            self._wheel_angle = (self._wheel_angle + self._wheel_omega * dt) % (2 * math.pi)
            # friction
            self._wheel_omega *= 0.985
            if self._wheel_omega < 0.25:
                if self._wheel_running:
                    self._wheel_running = False
                    self._wheel_omega = 0.0
                    sector = self._get_current_sector()
                    self._show_result(sector)

        self._redraw_all()
        self._after = self.window.after(16, self._tick)

    # -------------------- drawing --------------------
    def _redraw_all(self) -> None:
        self._draw_board()
        self._draw_scene()

    def _draw_board(self) -> None:
        c = self.board
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())

        pad = 10
        x0, y0, x1, y1 = pad, pad, w - pad, h - pad
        c.create_rectangle(x0, y0, x1, y1, fill=self.theme.board_bg, outline=self.theme.board_border, width=2)

        cols = 14
        rows = 3  # добавили ещё один ряд пустых клеток над словом
        gx0, gy0, gx1, gy1 = x0 + 18, y0 + 18, x1 - 18, y1 - 18
        cell_w = (gx1 - gx0) / cols
        cell_h = (gy1 - gy0) / rows

        text = self.mask.replace(" ", "")
        start = max(0, (cols - len(text)) // 2)
        row_idx = 1  # слово по‑прежнему в среднем ряду; верх/низ — пустые

        for r in range(rows):
            for col in range(cols):
                cx0 = gx0 + col * cell_w
                cy0 = gy0 + r * cell_h
                cx1 = cx0 + cell_w - 2
                cy1 = cy0 + cell_h - 2
                c.create_rectangle(int(cx0), int(cy0), int(cx1), int(cy1), fill=self.theme.cell_bg, outline=self.theme.cell_border, width=1)
                if r == row_idx and start <= col < start + len(text):
                    ch = text[col - start]
                    if ch == "•":
                        c.create_rectangle(int(cx0) + 1, int(cy0) + 1, int(cx1) - 1, int(cy1) - 1, fill=self.theme.cell_hidden, outline="")
                    else:
                        c.create_text(int((cx0 + cx1) / 2), int((cy0 + cy1) / 2), text=ch, fill=self.theme.cell_text, font=("Segoe UI Black", int(cell_h * 0.62)))

    def _draw_scene(self) -> None:
        c = self.scene
        c.delete("all")
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())

        # sky/stage gradient
        for i in range(24):
            y0 = int(i * h / 24)
            y1 = int((i + 1) * h / 24)
            c.create_rectangle(0, y0, w, y1, fill=_mix(self.theme.bg_top, self.theme.bg_bottom, i / 23), outline="")

        # stage floor (сплошной, без клеток)
        floor_y = int(h * 0.70)
        c.create_rectangle(0, floor_y, w, h, fill="#0c6f8f", outline="")

        base_scale = max(0.85, min(1.2, w / 1400))

        for slot in self._player_arc_slots(w, h, floor_y):
            hw, hh = self._steve_head_badge_steps(base_scale * slot["scale_mul"])
            bx, by = slot["x"], slot["badge_y"]
            i = slot["i"]
            if i == 0:  # Виктория: вниз на голову, вправо на две ширины
                bx += 4 * hw
                by += hh
            elif i == 1:  # Андрей: вверх на голову (размер таблички не трогаем)
                by += hh
            elif i == 2:  # Егор: вверх на полголовы, влево на две ширины
                bx -= 4 * hw
            self._draw_player_badge(
                c,
                bx,
                by,
                self.player_names[i],
                self.player_scores[i],
            )
            self._draw_steve(c, bx, by + 5 * hh, scale=base_scale * slot["scale_mul"])

        self._draw_wheel(c, w, h, floor_y=floor_y)

        hx = int(w * 0.82)
        self._draw_host(c, hx, floor_y, scale=max(0.95, w / 1400))


    def _steve_head_badge_steps(self, scale: float) -> tuple[int, int]:
        """
        Единицы сдвига таблички: «одна голова» по Y, «одна ширина головы» по X.
        От реального спрайта Стива или от векторной заглушки при том же scale.
        """
        if self._steve_photo is not None:
            sh = self._steve_photo.height()
            sw = self._steve_photo.width()
            # в типичном скине голова ~четверть роста по высоте и по ширине тела
            head_h = max(14, sh // 4)
            head_w = max(14, sw // 4)
            return head_w, head_h
        ps = max(3, min(6, int(4 * scale)))
        u = ps
        s = max(14, 8 * u)
        return s, s

    def _player_arc_slots(self, w: int, h: int, floor_y: int) -> list[dict]:
        """
        Три слота по ширине сцены (не кучей в углу): слева → центр → правее,
        лёгкая «дуга» по Y — крайние чуть выше, средний у линии пола.
        """
        xs = [int(w * 0.10), int(w * 0.26), int(w * 0.42)]
        lifts = [16, 0, 14]
        slots: list[dict] = []
        for i in range(3):
            px = xs[i]
            gy = floor_y - lifts[i]
            scale_mul = 1.04 if i == 1 else 0.98
            badge_y = int(h * 0.042) + (14 if i != 1 else 5)
            slots.append({"i": i, "x": px, "ground_y": gy, "scale_mul": scale_mul, "badge_y": badge_y})
        return slots

    def _draw_player_badge(self, c: tk.Canvas, x: int, y: int, name: str, score: int) -> None:
        """Одна табличка: имя и счёт."""
        line1 = name
        line2 = str(score)
        bw = max(100, int(len(line1) * 7.5 + 28))
        bh = 40
        c.create_rectangle(x - bw // 2, y - bh // 2, x + bw // 2, y + bh // 2, fill="#0b1f2a", outline="#ffffff", width=2)
        c.create_text(x, y - 9, text=line1, fill="#fff4c1", font=("Segoe UI Semibold", 11))
        c.create_text(x, y + 9, text=line2, fill="#ffdd99", font=("Consolas", 12, "bold"))

    def _draw_steve(self, c: tk.Canvas, x: int, foot_y: int, *, scale: float) -> None:
        """
        Стив: при наличии assets/player_steve.png — ваш спрайт; иначе векторная заглушка.
        """
        if self._steve_photo is not None:
            c.create_image(int(x), int(foot_y), image=self._steve_photo, anchor="s")
            return

        ps = max(3, min(6, int(4 * scale)))
        u = ps
        total_gy = 22  # строк сетки от макушки до ступней

        HAIR = "#3d2817"
        SKIN = "#d4a574"
        SHIRT = "#00aaaa"
        ARM = "#009c9c"
        PANTS = "#30309c"
        SHOE = "#6b4423"
        WHITE = "#ffffff"
        PUPIL = "#253192"

        hw = 4 * u

        def rect(gx: int, gy: int, gw: int, gh: int, fill: str, outline: str = "#1a1208") -> None:
            x0 = x - hw + gx * u
            y0 = foot_y - total_gy * u + gy * u
            c.create_rectangle(x0, y0, x0 + gw * u, y0 + gh * u, fill=fill, outline=outline, width=1)

        c.create_oval(x - hw - 4, foot_y - 4, x + hw + 4, foot_y + 6, fill=self.theme.shadow, outline="")

        # ноги / обувь
        rect(0, 16, 3, 3, PANTS)
        rect(5, 16, 3, 3, PANTS)
        rect(0, 19, 3, 3, SHOE)
        rect(5, 19, 3, 3, SHOE)

        # торс и рукава
        rect(2, 8, 4, 8, SHIRT)
        rect(0, 10, 2, 6, ARM)
        rect(6, 10, 2, 6, ARM)

        # голова — сначала кожа 8×8
        for gy in range(8):
            for gx in range(8):
                rect(gx, gy, 1, 1, SKIN)
        # волосы и боковые пряди
        for gx in range(8):
            rect(gx, 0, 1, 2, HAIR)
        rect(0, 2, 1, 2, HAIR)
        rect(7, 2, 1, 2, HAIR)
        # лицо
        rect(2, 3, 1, 1, WHITE)
        rect(5, 3, 1, 1, WHITE)
        rect(2, 4, 1, 1, PUPIL)
        rect(5, 4, 1, 1, PUPIL)
        rect(3, 5, 2, 1, SKIN)
        rect(3, 6, 2, 1, "#b88a5e")

    def _wheel_geom(self, w: int, h: int) -> tuple[int, int, int, int]:
        cx = int(w * 0.46)
        cy = int(h * 0.58)
        rx = max(1, int(w * 0.24))   # минимум 1, чтобы не было деления на ноль
        ry = max(1, int(h * 0.22))
        return cx, cy, rx, ry

    def _draw_wheel(self, c: tk.Canvas, w: int, h: int, *, floor_y: int) -> None:
        cx, cy, rx, ry = self._wheel_geom(w, h)
        if rx <= 0 or ry <= 0:
            return

        aspect = ry / rx
        body_h = int(h * 0.20)
        bottom_y = cy + body_h

        # ---- тень ----
        c.create_oval(cx - rx + 26, floor_y - 6, cx + rx - 18, floor_y + 28,
                      fill=self.theme.shadow, outline="")

        # ---- корпус цилиндра ----
        c.create_rectangle(cx - rx, cy, cx + rx, cy + body_h,
                           fill=self.theme.wheel_base_dark,
                           outline=self.theme.wheel_outline, width=2)
        c.create_oval(cx - rx, bottom_y - ry, cx + rx, bottom_y + ry,
                      fill=self.theme.wheel_base_dark, outline="")
        c.create_arc(cx - rx, bottom_y - ry, cx + rx, bottom_y + ry,
                     start=180, extent=180, style="arc",
                     outline=self.theme.wheel_outline, width=2)


        # ---- верх барабана: внешнее кольцо, затем внутреннее (как в _get_current_sector) ----
        n = len(self.sectors)
        extent = 360.0 / n
        start = self._wheel_start_deg()
        mid_r = 0.72

        for i in range(n):
            # Цвет внешнего кольца: противоположный внутреннему
            if i % 2 == 0:
                outer_color = "#0a6bc2"   # синий
            else:
                outer_color = "#f0f9ff"   # белый

            # Рисуем полную дугу от центра до края (временно, потом перекроем)
            c.create_arc(
                cx - rx, cy - ry, cx + rx, cy + ry,
                start=start + i * extent,
                extent=extent,
                fill=outer_color,
                outline="",
                width=0,
            )

        # Теперь рисуем внутреннее кольцо (от inner_r до mid_r) поверх, чтобы перекрыть центр
        for i in range(n):
            # Цвет внутреннего кольца (основной)
            if i % 2 == 0:
                inner_color = "#f0f9ff"   # белый
            else:
                inner_color = "#0a6bc2"   # синий

            # Рисуем дугу, ограниченную внутренним радиусом mid_r. Для этого используем масштабирование
            # эллипса: внутренний эллипс будет в (mid_r) раз меньше.
            # Создаём bounding box внутреннего эллипса:
            inner_rx = rx * mid_r
            inner_ry = ry * mid_r
            inner_bbox = (cx - inner_rx, cy - inner_ry, cx + inner_rx, cy + inner_ry)

            c.create_arc(
                *inner_bbox,
                start=start + i * extent,
                extent=extent,
                fill=inner_color,
                outline="",
                width=0,
            )

        # ---- Текст на внешнем кольце ----
        text_radius = 0.85   # чуть ближе к краю, но всё ещё на внешнем кольце
        for i in range(n):
            sec = self.sectors[i]
            mid_deg = (start + i * extent + extent / 2) % 360
            mid_rad = math.radians(mid_deg)

            lx = cx + rx * text_radius * math.cos(mid_rad)
            ly = cy - ry * text_radius * math.sin(mid_rad)

            # Цвет текста: контрастный к цвету внешнего кольца в этом секторе
            if i % 2 == 0:   # внешнее кольцо синее -> текст белый
                text_color = "#ffffff"
            else:            # внешнее кольцо белое -> текст синий
                text_color = "#0a6bc2"

            c.create_text(
                int(lx), int(ly),
                text=sec.label,
                fill=text_color,
                font=("Segoe UI Semibold", 10),
            )

        # ---- Звезда (вращается) ----
        star_angle = self._wheel_angle
        core_rx = int(rx * 0.18)
        core_ry = int(core_rx * aspect)

        pts = []
        for k in range(16):
            ang = math.radians(k * 22.5 + math.degrees(star_angle))
            r = core_rx * (0.92 if (k % 2 == 0) else 0.42)
            x = cx + r * math.cos(ang)
            y = cy + (r * aspect) * math.sin(ang)
            pts.extend([int(x), int(y)])
        c.create_polygon(*pts, fill="#ffdd99", outline="#c79b1a", width=1)

        # ---- Указатель (аккуратная стрелка) ----
        px = cx + rx - 6
        py = cy - int(ry * 0.15)   # чуть выше
        # Тень
        c.create_polygon(px + 28, py, px - 4, py + 10, px+28, py + 20,
                 fill="#4a1f1f", outline="")
        # Основная стрелка
        c.create_polygon(px + 28, py, px - 4, py + 10, px+28, py + 20,
                 fill="#d33131", outline="#ffffff", width=1)
        # Маленький кружок на конце (для красоты)
        c.create_oval(px + 28, py + 8, px + 36, py + 12, fill="#ffffff", outline="")                   



    def _draw_host(self, c: tk.Canvas, x: int, ground_y: int, *, scale: float) -> None:
        if self._host_photo is not None:
            c.create_image(x, ground_y, image=self._host_photo, anchor="s")
            return

        head_r = int(42 * scale)
        body_w = int(110 * scale)
        body_h = int(160 * scale)
        y = ground_y - int(20 * scale)

        c.create_oval(x - body_w // 2 + 8, y - 10, x + body_w // 2 - 8, y + 10, fill=self.theme.shadow, outline="")

        c.create_rectangle(x - body_w // 2, y - body_h, x + body_w // 2, y, fill="#2f5f7a", outline="#0b1f2a", width=2)
        c.create_polygon(x, y - body_h + 40, x - 18, y - body_h + 66, x + 18, y - body_h + 66, fill="#d33131", outline="#7a1f1f")

        head_y = y - body_h - head_r + 30
        c.create_oval(x - head_r, head_y - head_r, x + head_r, head_y + head_r, fill="#f1caa6", outline="#0b1f2a", width=2)
        c.create_arc(x - head_r, head_y - head_r - 8, x + head_r, head_y + head_r, start=10, extent=160, fill="#9da6ad", outline="")
        c.create_oval(x - 16, head_y - 8, x - 8, head_y, fill="#0b1f2a", outline="")
        c.create_oval(x + 8, head_y - 8, x + 16, head_y, fill="#0b1f2a", outline="")
        c.create_arc(x - 22, head_y - 6, x + 22, head_y + 26, start=200, extent=140, style="arc", outline="#0b1f2a", width=3)
        c.create_oval(x - 28, head_y + 6, x + 28, head_y + 22, fill="#5c463a", outline="")
        c.create_oval(x - 6, head_y + 8, x + 6, head_y + 22, fill="#f1caa6", outline="")

        mx = x - int(34 * scale)
        my = y - int(62 * scale)
        c.create_oval(mx - 18, my - 18, mx + 18, my + 18, fill="#1a222a", outline="#ffffff", width=1)
        c.create_line(mx, my + 14, mx + 10, my + 44, fill="#1a222a", width=6)


def _mix(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

