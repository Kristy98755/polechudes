from __future__ import annotations

import tkinter as tk

from app.game_logic import GameLogic


class DisplayWindow:
    def __init__(self, root: tk.Tk, logic: GameLogic) -> None:
        self.logic = logic
        self.window = tk.Toplevel(root)
        self.window.title("Поле чудес — Экран игроков")
        self.window.configure(bg="#0b1020")
        self.window.minsize(980, 620)

        self.question_var = tk.StringVar()
        self.mask_var = tk.StringVar()
        self.explanation_var = tk.StringVar()

        self._build()
        self.logic.subscribe(self.refresh)
        self.refresh()

    def _build(self) -> None:
        container = tk.Frame(self.window, bg="#0b1020")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        title = tk.Label(
            container,
            text="ПОЛЕ ЧУДЕС",
            font=("Segoe UI Black", 30),
            fg="#ffd35a",
            bg="#0b1020",
        )
        title.pack(pady=(0, 12))

        question = tk.Label(
            container,
            textvariable=self.question_var,
            font=("Segoe UI", 17),
            wraplength=900,
            justify="center",
            fg="#d6e3ff",
            bg="#0b1020",
        )
        question.pack(fill="x", pady=(0, 20))

        mask = tk.Label(
            container,
            textvariable=self.mask_var,
            font=("Consolas", 44, "bold"),
            fg="#f2f6ff",
            bg="#0b1020",
        )
        mask.pack(pady=(0, 20))

        explanation = tk.Label(
            container,
            textvariable=self.explanation_var,
            font=("Segoe UI", 14),
            wraplength=900,
            justify="center",
            fg="#9ed9b6",
            bg="#0b1020",
        )
        explanation.pack(fill="x")

    def refresh(self) -> None:
        item = self.logic.current
        self.question_var.set(item.question)
        self.mask_var.set(self.logic.masked_answer)
        self.explanation_var.set(item.explanation if self.logic.solved else "")
