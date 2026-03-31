from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog

from app.game_logic import GameLogic, parse_puzzles
from app.ui_control_panel import ControlPanel
from app.ui_display_window import DisplayWindow


DEFAULT_PUZZLES = """\
Столица Франции | Париж | Классический вопрос на разогрев
Кошка из книги про Маугли | Багира | Персонаж произведения Редьярда Киплинга
Самая длинная река в мире (в школьной версии) | Нил | Часто используется в викторинах
"""


def ask_puzzles(root: tk.Tk) -> str | None:
    prompt = (
        "Введите вопросы в формате:\n"
        "Вопрос | Ответ | Пояснение\n\n"
        "Каждая запись — с новой строки."
    )
    return simpledialog.askstring(
        title="Старт игры",
        prompt=prompt,
        initialvalue=DEFAULT_PUZZLES,
        parent=root,
    )


def bootstrap_logic(root: tk.Tk) -> GameLogic:
    while True:
        raw = ask_puzzles(root)
        if raw is None:
            raise SystemExit(0)
        try:
            puzzles = parse_puzzles(raw)
            return GameLogic(puzzles)
        except ValueError as err:
            messagebox.showerror("Ошибка в списке вопросов", str(err), parent=root)


def main() -> None:
    root = tk.Tk()
    root.withdraw()

    logic = bootstrap_logic(root)

    display = DisplayWindow(root, logic)
    control = ControlPanel(root, logic)

    try:
        display.window.geometry("+40+40")
        control.window.geometry("+1080+40")
    except Exception:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()
