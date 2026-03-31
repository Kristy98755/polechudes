from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog

from app.game_logic import GameLogic


class ControlPanel:
    def __init__(self, root: tk.Tk, logic: GameLogic) -> None:
        self.logic = logic
        self.window = tk.Toplevel(root)
        self.window.title("Поле чудес — Панель управления")
        self.window.configure(bg="#1d1f2b")
        self.window.minsize(680, 540)

        self.status_var = tk.StringVar()
        self._build()
        self.logic.subscribe(self.refresh)
        self.refresh()

    def _build(self) -> None:
        frame = tk.Frame(self.window, bg="#1d1f2b")
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        header = tk.Label(
            frame,
            text="ПАНЕЛЬ ВЕДУЩЕГО",
            font=("Segoe UI Black", 20),
            fg="#ffd35a",
            bg="#1d1f2b",
        )
        header.pack(anchor="w")

        top = tk.Frame(frame, bg="#1d1f2b")
        top.pack(fill="x", pady=(14, 8))

        tk.Label(top, text="Вопрос:", fg="#d8def5", bg="#1d1f2b", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.question_lbl = tk.Label(top, text="", wraplength=640, justify="left", fg="#ffffff", bg="#1d1f2b", font=("Segoe UI", 12))
        self.question_lbl.pack(anchor="w", pady=(2, 8))

        tk.Label(top, text="Текущее табло:", fg="#d8def5", bg="#1d1f2b", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.mask_lbl = tk.Label(top, text="", fg="#f3f6ff", bg="#1d1f2b", font=("Consolas", 24, "bold"))
        self.mask_lbl.pack(anchor="w", pady=(2, 8))

        list_fr = tk.Frame(frame, bg="#1d1f2b")
        list_fr.pack(fill="both", expand=True)

        tk.Label(list_fr, text="Список вопросов", fg="#d8def5", bg="#1d1f2b", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(list_fr, height=10, font=("Segoe UI", 10))
        self.listbox.pack(fill="both", expand=True, pady=(4, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        controls = tk.Frame(frame, bg="#1d1f2b")
        controls.pack(fill="x", pady=(4, 8))

        tk.Button(controls, text="Открыть букву", command=self._reveal_letter).pack(side="left")
        tk.Button(controls, text="Назвать слово", command=self._guess_word).pack(side="left", padx=8)
        tk.Button(controls, text="Следующий вопрос", command=self.logic.next_puzzle).pack(side="left")

        status = tk.Label(frame, textvariable=self.status_var, fg="#9ed9b6", bg="#1d1f2b", font=("Segoe UI", 11))
        status.pack(anchor="w", pady=(6, 0))

    def refresh(self) -> None:
        item = self.logic.current
        self.question_lbl.config(text=item.question)
        self.mask_lbl.config(text=self.logic.masked_answer)

        self.listbox.delete(0, tk.END)
        for i, p in enumerate(self.logic.puzzles, start=1):
            self.listbox.insert(tk.END, f"{i}. {p.question}")

        self.listbox.selection_set(self.logic.current_index)
        self.listbox.see(self.logic.current_index)

        if self.logic.solved:
            text = "Слово отгадано"
            if item.explanation:
                text += f". Пояснение: {item.explanation}"
            self.status_var.set(text)
        else:
            self.status_var.set("Ожидание действий ведущего")

    def _reveal_letter(self) -> None:
        letter = simpledialog.askstring("Буква", "Введите букву:", parent=self.window)
        if letter is None:
            return
        count = self.logic.reveal_letter(letter)
        if count <= 0:
            messagebox.showinfo("Результат", "Буква не найдена или уже была открыта.", parent=self.window)
        else:
            messagebox.showinfo("Результат", f"Открыто букв: {count}", parent=self.window)

    def _guess_word(self) -> None:
        guess = simpledialog.askstring("Слово", "Введите полный ответ:", parent=self.window)
        if guess is None:
            return
        ok = self.logic.try_guess(guess)
        if not ok:
            messagebox.showwarning("Ошибка", "Неверный ответ.", parent=self.window)

    def _on_select(self, _event) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx != self.logic.current_index:
            self.logic.set_puzzle(idx)
