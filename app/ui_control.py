# ui_control.py
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import random
from datetime import datetime

from app.model import GameState, GamePhase, Player, Puzzle
from app.wheel import WheelSector


class ControlWindow:
    def __init__(self, root: tk.Tk, state: GameState, game_window):
        self.state = state
        self.game_window = game_window

        self.window = tk.Toplevel(root)
        self.window.title("Поле чудес — Панель ведущего")
        self.window.configure(bg="#1e1e2f")
        self.window.minsize(1000, 750)
        self.window.geometry("1100x800")

        # Переменные для интерфейса
        self.current_phase_var = tk.StringVar(value="Тур 1")
        self.turn_info_var = tk.StringVar(value="Ожидание начала тура")
        self.multiplier = 1  # для сектора Удвоение

        # Построение интерфейса
        self._build()

        # Подписка на лог
        self.state.subscribe_log(self._on_log)

        # Обновление информации о текущем туре/игроках
        self._refresh_display()

    def _build(self):
        # Основной фрейм с вкладками
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Вкладка "Игра"
        self.tab_game = ttk.Frame(notebook)
        notebook.add(self.tab_game, text="Игра")
        self._build_game_tab()

        # Вкладка "Управление турами"
        self.tab_rounds = ttk.Frame(notebook)
        notebook.add(self.tab_rounds, text="Туры")
        self._build_rounds_tab()

        # Вкладка "Игроки"
        self.tab_players = ttk.Frame(notebook)
        notebook.add(self.tab_players, text="Игроки")
        self._build_players_tab()

        # Вкладка "Журнал"
        self.tab_log = ttk.Frame(notebook)
        notebook.add(self.tab_log, text="Журнал")
        self._build_log_tab()

    # ------------------ Вкладка "Игра" ------------------
    def _build_game_tab(self):
        # Статус
        status_frame = tk.LabelFrame(self.tab_game, text="Статус", bg="#1e1e2f", fg="white")
        status_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(status_frame, textvariable=self.current_phase_var, font=("Segoe UI", 14, "bold"), bg="#1e1e2f", fg="#ffd966").pack(pady=5)
        tk.Label(status_frame, textvariable=self.turn_info_var, font=("Segoe UI", 12), bg="#1e1e2f", fg="white").pack(pady=5)

        # Барабан и управление ходом
        wheel_frame = tk.LabelFrame(self.tab_game, text="Барабан", bg="#1e1e2f", fg="white")
        wheel_frame.pack(fill="x", padx=10, pady=10)

        btn_frame = tk.Frame(wheel_frame, bg="#1e1e2f")
        btn_frame.pack(pady=10)

        self.spin_btn = tk.Button(btn_frame, text="🎡 КРУТИТЬ БАРАБАН", font=("Segoe UI", 14, "bold"),
                                  bg="#2a6a3c", fg="white", command=self._spin_wheel)
        self.spin_btn.pack(side="left", padx=10, ipadx=10, ipady=5)

        self.stop_btn = tk.Button(btn_frame, text="🛑 ЭКСТРЕННЫЙ СТОП", font=("Segoe UI", 14, "bold"),
                                  bg="#8a2a2a", fg="white", command=self._emergency_stop)
        self.stop_btn.pack(side="left", padx=10, ipadx=10, ipady=5)

        # Сектор, который выпал
        self.sector_label = tk.Label(wheel_frame, text="", font=("Segoe UI", 16, "bold"), bg="#1e1e2f", fg="#ffaa44")
        self.sector_label.pack(pady=10)

        # Действия после вращения
        action_frame = tk.LabelFrame(self.tab_game, text="Действия игрока", bg="#1e1e2f", fg="white")
        action_frame.pack(fill="x", padx=10, pady=10)

        self.letter_entry = tk.Entry(action_frame, font=("Segoe UI", 14), width=5, justify="center")
        self.letter_entry.pack(pady=5)
        self.letter_btn = tk.Button(action_frame, text="Назвать букву", command=self._call_letter, state="disabled",
                                    bg="#3a3a4c", fg="white")
        self.letter_btn.pack(pady=5)

        self.word_btn = tk.Button(action_frame, text="Назвать слово", command=self._call_word, state="disabled",
                                  bg="#3a3a4c", fg="white")
        self.word_btn.pack(pady=5)

        # Кнопка принудительного выбывания (если игрок ошибся)
        self.eliminate_btn = tk.Button(action_frame, text="❌ Выбыть (неверное слово)", command=self._eliminate_current_player,
                                       bg="#6a2a2a", fg="white", state="disabled")
        self.eliminate_btn.pack(pady=5)

        # Информация о правиле трёх ходов
        self.three_hits_label = tk.Label(action_frame, text="", font=("Segoe UI", 10), bg="#1e1e2f", fg="#ffaa44")
        self.three_hits_label.pack(pady=5)

    # ------------------ Вкладка "Туры" ------------------
    def _build_rounds_tab(self):
        # Переключение между турами (для ведущего)
        control_frame = tk.Frame(self.tab_rounds, bg="#1e1e2f")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="Текущий этап:", bg="#1e1e2f", fg="white").pack(side="left")
        self.phase_combobox = ttk.Combobox(control_frame, values=[p.value for p in GamePhase], state="readonly")
        self.phase_combobox.pack(side="left", padx=5)
        self.phase_combobox.bind("<<ComboboxSelected>>", self._change_phase)

        tk.Button(control_frame, text="Начать тур", command=self._start_current_round, bg="#2a6a3c", fg="white").pack(side="left", padx=5)

        # Список финалистов (победители туров)
        finalists_frame = tk.LabelFrame(self.tab_rounds, text="Финалисты", bg="#1e1e2f", fg="white")
        finalists_frame.pack(fill="x", padx=10, pady=10)
        self.finalists_listbox = tk.Listbox(finalists_frame, height=3, bg="#2a2a3c", fg="white")
        self.finalists_listbox.pack(fill="x", padx=5, pady=5)

        # Кнопка запуска финала (после трёх туров)
        self.start_final_btn = tk.Button(self.tab_rounds, text="▶️ Начать финал", command=self._start_final,
                                         bg="#4a6a8a", fg="white", state="disabled")
        self.start_final_btn.pack(pady=10)

        # Кнопка суперигры (появляется после финала)
        self.supergame_btn = tk.Button(self.tab_rounds, text="✨ Суперигра ✨", command=self._start_supergame,
                                       bg="#8a6a2a", fg="white", state="disabled")
        self.supergame_btn.pack(pady=5)

    # ------------------ Вкладка "Игроки" ------------------
    def _build_players_tab(self):
        # Список игроков текущего тура
        players_frame = tk.LabelFrame(self.tab_players, text="Игроки текущего тура", bg="#1e1e2f", fg="white")
        players_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.players_tree = ttk.Treeview(players_frame, columns=("name", "score", "status"), show="headings")
        self.players_tree.heading("name", text="Имя")
        self.players_tree.heading("score", text="Очки")
        self.players_tree.heading("status", text="Статус")
        self.players_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Кнопки управления игроком
        btn_frame = tk.Frame(players_frame, bg="#1e1e2f")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Изменить имя", command=self._edit_player_name, bg="#3a3a4c", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="+100 очков", command=lambda: self._change_score(100), bg="#2a6a3c", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="-100 очков", command=lambda: self._change_score(-100), bg="#6a2a2a", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Выбыть", command=self._eliminate_selected_player, bg="#8a2a2a", fg="white").pack(side="left", padx=5)

        # История троек (для справки)
        history_frame = tk.LabelFrame(self.tab_players, text="История троек", bg="#1e1e2f", fg="white")
        history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.history_text = tk.Text(history_frame, height=8, bg="#2a2a3c", fg="white", wrap="word")
        self.history_text.pack(fill="both", expand=True, padx=5, pady=5)

    # ------------------ Вкладка "Журнал" ------------------
    def _build_log_tab(self):
        self.log_text = tk.Text(self.tab_log, bg="#0a0a12", fg="#00ffaa", wrap="word", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        tk.Button(self.tab_log, text="Очистить лог", command=self._clear_log, bg="#3a3a4c", fg="white").pack(pady=5)

    # ------------------ Логика ведущего ------------------
    def _spin_wheel(self):
        """Запуск вращения барабана."""
        if self.state.phase in [GamePhase.SUPER]:
            messagebox.showinfo("Информация", "Сейчас суперигра, барабан не крутится.")
            return
        current_round = self.state.get_current_round()
        if not current_round or not current_round.active_players:
            messagebox.showerror("Ошибка", "Нет активных игроков или тур не начат.")
            return
        self.state.log("Ведущий крутит барабан...")
        self.spin_btn.config(state="disabled")
        self.game_window.start_spin(on_stop=self._on_spin_stop)

    def _on_spin_stop(self, sector: WheelSector):
        """Обработка остановки барабана."""
        self.spin_btn.config(state="normal")
        self.sector_label.config(text=f"Выпало: {sector.label}")
        self.state.last_sector = sector
        self.multiplier = 1

        # Логика специальных секторов
        if sector.kind == "bankrupt":
            self._handle_bankrupt()
        elif sector.kind == "prize":
            self._handle_prize()
        elif sector.kind == "plus":
            self._handle_plus()
        elif sector.kind == "key":
            self._handle_key()
        elif sector.kind == "zero":
            self._handle_zero()
        elif sector.kind in ("x2", "x3"):
            self.multiplier = sector.value
            self.state.log(f"Выпал сектор ×{self.multiplier}. Очки за следующую букву умножатся.")
            # Разрешаем назвать букву
            self._enable_letter_mode()
        else:
            # Обычный сектор с очками
            self.state.last_points_value = sector.value
            self.state.log(f"Выпало {sector.value} очков. Игрок может назвать букву.")
            self._enable_letter_mode()

    def _enable_letter_mode(self):
        """После выпадения нормального сектора (или x2, x3) игрок может назвать букву."""
        self.letter_btn.config(state="normal")
        self.word_btn.config(state="normal")
        self.eliminate_btn.config(state="normal")
        self.turn_info_var.set("Игрок может назвать букву или слово")

    def _call_letter(self):
        """Игрок называет букву."""
        letter = self.letter_entry.get().strip().upper()
        if not letter:
            messagebox.showerror("Ошибка", "Введите букву")
            return
        if len(letter) > 1:
            letter = letter[0]
        # Нормализация
        if letter == "Ё":
            letter = "Е"
        # Проверка через модель
        result = self.state.try_reveal_letter(letter, multiplier=self.multiplier)
        self.letter_entry.delete(0, tk.END)
        self.letter_btn.config(state="disabled")
        self.word_btn.config(state="disabled")
        self.eliminate_btn.config(state="disabled")
        self.sector_label.config(text="")
        self._refresh_display()

        if result.get("game_over", False):
            # Тур завершён (победитель)
            self._end_tour()
        elif result.get("eliminated", False):
            # Игрок выбыл из-за неправильного слова или трёх ходов
            self._refresh_display()
            self._check_tour_end()
        else:
            # Ход перешёл к следующему игроку или остался у текущего (если буква верная)
            if not result.get("letter_found", False):
                self.state.next_player()
            self._refresh_display()
            # Если после хода в туре остался один игрок, обновляем правило трёх ходов
            self._update_three_hits_rule()

    def _call_word(self):
        """Игрок пытается назвать слово."""
        word = simpledialog.askstring("Назвать слово", "Введите слово (ответ):", parent=self.window)
        if not word:
            return
        word = word.strip().upper()
        result = self.state.guess_word(word)
        self.letter_btn.config(state="disabled")
        self.word_btn.config(state="disabled")
        self.eliminate_btn.config(state="disabled")
        self.sector_label.config(text="")
        self._refresh_display()

        if result.get("correct", False):
            self.state.log(f"Игрок {self.state.current_player().name} угадал слово! Победа в туре.")
            self._end_tour()
        else:
            self.state.log(f"Игрок {self.state.current_player().name} назвал неверное слово и выбывает.")
            self._eliminate_current_player()
            self._check_tour_end()

    def _handle_bankrupt(self):
        """Сектор Банкрот: игрок теряет все очки, ход переходит."""
        player = self.state.current_player()
        player.score = 0
        self.state.log(f"Банкрот! {player.name} теряет все очки.")
        self.state.next_player()
        self._refresh_display()
        self.sector_label.config(text="")
        # После банкрота ход сразу переходит, букву не называют
        self.letter_btn.config(state="disabled")
        self.word_btn.config(state="disabled")
        self.eliminate_btn.config(state="disabled")

    def _handle_prize(self):
        """Сектор Приз: чёрный ящик. Ведущий торгуется."""
        player = self.state.current_player()
        # Имитация чёрного ящика
        prizes = ["тыква", "капуста", "бутылка водки", "игрушечная машинка", "телевизор", "путёвка в Сочи", "ключи от квартиры"]
        prize = random.choice(prizes)
        answer = messagebox.askyesno("Чёрный ящик",
                                     f"В чёрном ящике: {prize}\n\nИгрок {player.name}, вы забираете приз и выходите из игры?\n"
                                     "Нажмите 'Да' - забрать приз и уйти.\n'Нет' - отказаться и получить 2000 очков за букву.")
        if answer:
            self.state.log(f"Игрок {player.name} забирает приз '{prize}' и покидает игру.")
            self._eliminate_current_player(reason="prize")
        else:
            self.state.log(f"Игрок {player.name} отказался от приза, получает 2000 очков за букву.")
            self.state.last_points_value = 2000
            self._enable_letter_mode()
        self._refresh_display()

    def _handle_plus(self):
        """Сектор Плюс: открыть любую букву по счёту."""
        puzzle = self.state.current_puzzle()
        if not puzzle:
            self.state.log("Нет активного вопроса, сектор Плюс не работает.")
            self.state.next_player()
            return
        # Спрашиваем ведущего, какую позицию открыть
        positions = [str(i+1) for i, ch in enumerate(puzzle.answer) if ch not in self.state.revealed_letters]
        if not positions:
            self.state.log("Все буквы уже открыты. Ход переходит.")
            self.state.next_player()
            return
        pos_str = simpledialog.askstring("Плюс", f"Какую букву по счёту открыть? (1..{len(puzzle.answer)})\nДоступные позиции: {', '.join(positions)}")
        if pos_str and pos_str.isdigit():
            pos = int(pos_str)
            if 1 <= pos <= len(puzzle.answer):
                letter = puzzle.answer[pos-1]
                if letter not in self.state.revealed_letters:
                    self.state.revealed_letters.add(letter)
                    self.state._recompute_mask()
                    self.game_window.refresh_from_state()
                    self.state.log(f"Сектор Плюс: открыта буква №{pos} — {letter}")
                    # После открытия буквы ход не переходит, игрок может крутить дальше
                    self.state.log("Игрок сохраняет ход и может крутить барабан.")
                    self._enable_letter_mode()
                    self._refresh_display()
                    return
        self.state.log("Неверная позиция или буква уже открыта. Ход переходит.")
        self.state.next_player()
        self._refresh_display()

    def _handle_key(self):
        """Сектор Ключ: выбор из 6 ключей, один от автомобиля."""
        player = self.state.current_player()
        # Имитация: ведущий выбирает, угадал ли игрок
        success = messagebox.askyesno("Ключ", f"Игрок {player.name}, вы выбираете ключ. Угадаете? (Нажмите Да, если повезло)")
        if success:
            self.state.log(f"Игрок {player.name} открывает автомобиль! Он выигрывает машину и покидает игру.")
            # Можно добавить логику начисления автомобиля, но для простоты - выбывает с призом
            self._eliminate_current_player(reason="car")
        else:
            self.state.log(f"Игрок {player.name} не угадал ключ. Ход переходит.")
            self.state.next_player()
        self._refresh_display()

    def _handle_zero(self):
        """Сектор 0: переход хода, очки не теряются."""
        self.state.log("Выпал сектор 0. Ход переходит следующему игроку.")
        self.state.next_player()
        self._refresh_display()

    def _eliminate_current_player(self, reason=None):
        """Выбывание текущего игрока."""
        player = self.state.current_player()
        self.state.eliminate_player(player)
        self.state.log(f"{player.name} выбывает из игры. Причина: {reason if reason else 'неверное слово/решение'}")
        self._refresh_display()

    def _eliminate_selected_player(self):
        """Выбыть выбранного игрока из списка (ручное управление)."""
        selected = self.players_tree.selection()
        if not selected:
            return
        item = selected[0]
        values = self.players_tree.item(item, "values")
        # Найти игрока по имени
        name = values[0]
        for p in self.state.get_current_round().active_players:
            if p.name == name:
                self.state.eliminate_player(p)
                self.state.log(f"Ведущий выводит из игры {p.name}.")
                break
        self._refresh_display()
        self._check_tour_end()

    def _change_score(self, delta):
        """Изменение очков выбранного игрока."""
        selected = self.players_tree.selection()
        if not selected:
            return
        item = selected[0]
        values = self.players_tree.item(item, "values")
        name = values[0]
        for p in self.state.get_current_round().active_players:
            if p.name == name:
                p.score += delta
                self.state.log(f"Очки {p.name}: {p.score} ({delta:+d})")
                break
        self._refresh_display()

    def _edit_player_name(self):
        """Редактирование имени выбранного игрока."""
        selected = self.players_tree.selection()
        if not selected:
            return
        item = selected[0]
        values = self.players_tree.item(item, "values")
        old_name = values[0]
        new_name = simpledialog.askstring("Изменить имя", "Новое имя:", initialvalue=old_name)
        if new_name:
            for p in self.state.get_current_round().players:
                if p.name == old_name:
                    p.name = new_name
                    self.state.log(f"Игрок {old_name} переименован в {new_name}")
                    break
            self._refresh_display()

    def _update_three_hits_rule(self):
        """Проверка и отображение правила трёх ходов."""
        round_state = self.state.get_current_round()
        if round_state and len(round_state.active_players) == 1:
            hits = self.state.get_consecutive_hits()
            remaining = max(0, 3 - hits)
            self.three_hits_label.config(text=f"ПРАВИЛО ТРЁХ ХОДОВ: осталось верных ходов до принудительного слова: {remaining}")
            if hits >= 3:
                self.three_hits_label.config(text="Игрок ОБЯЗАН назвать слово!")
                # Принудительно вызываем диалог слова
                self._call_word()
        else:
            self.three_hits_label.config(text="")

    def _end_tour(self):
        """Завершение текущего тура, определение победителя."""
        winner = self.state.get_current_round().winner
        if winner:
            self.state.log(f"Тур завершён. Победитель: {winner.name}")
            self.state.add_finalist(winner)
            self._refresh_finalists_list()
            # Переход к следующему туру
            if self.state.phase == GamePhase.ROUND1:
                self.state.phase = GamePhase.ROUND2
            elif self.state.phase == GamePhase.ROUND2:
                self.state.phase = GamePhase.ROUND3
            elif self.state.phase == GamePhase.ROUND3:
                self.state.phase = GamePhase.FINAL
            self.current_phase_var.set(self.state.phase.value)
            self._start_current_round()
        else:
            self.state.log("Тур завершён без победителя (все выбыли). Переход к следующему туру.")
            # Пропустить тур, но добавить никого?
            if self.state.phase == GamePhase.ROUND1:
                self.state.phase = GamePhase.ROUND2
            elif self.state.phase == GamePhase.ROUND2:
                self.state.phase = GamePhase.ROUND3
            elif self.state.phase == GamePhase.ROUND3:
                self.state.phase = GamePhase.FINAL
            self.current_phase_var.set(self.state.phase.value)
            self._start_current_round()

    def _check_tour_end(self):
        """Проверить, остались ли активные игроки в туре."""
        round_state = self.state.get_current_round()
        if not round_state.active_players:
            self.state.log("Все игроки выбыли, тур завершается без победителя.")
            self._end_tour()

    def _start_current_round(self):
        """Инициализация текущего тура (загрузка игроков, вопроса)."""
        if self.state.phase == GamePhase.FINAL:
            self.start_final_btn.config(state="normal")
            return
        # Убедимся, что для тура есть вопрос
        if not self.state.puzzles:
            messagebox.showerror("Ошибка", "Нет вопросов для этого тура. Добавьте вопросы на вкладке 'Вопросы' (не реализовано, но можно через модель).")
            return
        self.state.reset_round()  # сброс счётчиков, revealed_letters и т.д.
        self.state.set_current_puzzle(0)
        self._refresh_display()
        self.state.log(f"Начат {self.state.phase.value}. Первый ход у игрока {self.state.current_player().name}")
        self.turn_info_var.set(f"Ход игрока: {self.state.current_player().name}")
        self.three_hits_label.config(text="")

    def _start_final(self):
        """Запуск финала."""
        if len(self.state.finalists) < 1:
            messagebox.showerror("Ошибка", "Нет финалистов. Сначала проведите три тура.")
            return
        self.state.phase = GamePhase.FINAL
        self.current_phase_var.set("Финал")
        # Создаём финальный раунд с финалистами
        self.state.init_final_round()
        self._refresh_display()
        self.state.log("Финал начат!")
        self.start_final_btn.config(state="disabled")
        self.supergame_btn.config(state="normal")

    def _start_supergame(self):
        """Запуск суперигры."""
        winner = self.state.get_final_winner()
        if not winner:
            messagebox.showerror("Ошибка", "Нет победителя финала.")
            return
        answer = messagebox.askyesno("Суперигра", f"Победитель {winner.name}, вы согласны сыграть в суперигру?\nРиск: потеря всех призов (очков).")
        if not answer:
            self.state.log("Игрок отказался от суперигры.")
            return
        # Здесь вызываем отдельное окно суперигры
        from app.ui_super import SuperGameWindow
        super_win = SuperGameWindow(self.window, self.state, winner, self.game_window)
        self.window.wait_window(super_win)
        # После суперигры игра завершена
        self.supergame_btn.config(state="disabled")

    # ------------------ Вспомогательные методы ------------------
    def _refresh_display(self):
        """Обновить все интерфейсные элементы (списки игроков, очки, статус)."""
        # Обновить дерево игроков
        for item in self.players_tree.get_children():
            self.players_tree.delete(item)
        round_state = self.state.get_current_round()
        if round_state:
            for player in round_state.players:
                status = "активен" if player in round_state.active_players else "выбыл"
                self.players_tree.insert("", "end", values=(player.name, player.score, status))
        # Обновить историю троек
        self.history_text.delete(1.0, tk.END)
        for trio in self.state.trios_history:
            self.history_text.insert(tk.END, f"{trio.label}\n")
            for p in trio.players:
                self.history_text.insert(tk.END, f"  {p.name}: {p.score}\n")
            self.history_text.insert(tk.END, "\n")
        # Обновить информацию о текущем игроке
        if round_state and round_state.active_players:
            current = self.state.current_player()
            if current:
                self.turn_info_var.set(f"Ход игрока: {current.name}")
            else:
                self.turn_info_var.set("Нет активных игроков")
        # Обновить список финалистов
        self._refresh_finalists_list()

    def _refresh_finalists_list(self):
        self.finalists_listbox.delete(0, tk.END)
        for p in self.state.finalists:
            self.finalists_listbox.insert(tk.END, f"{p.name} (очки: {p.score})")

    def _change_phase(self, event):
        """Ручное переключение фазы (для ведущего)."""
        phase_name = self.phase_combobox.get()
        for p in GamePhase:
            if p.value == phase_name:
                self.state.phase = p
                self.current_phase_var.set(p.value)
                break
        self._refresh_display()

    def _on_log(self, ev):
        self.log_text.insert(tk.END, f"[{ev.ts.strftime('%H:%M:%S')}] {ev.text}\n")
        self.log_text.see(tk.END)

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.state.clear_log()