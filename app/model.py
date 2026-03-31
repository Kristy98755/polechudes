from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Literal
from enum import Enum

class GamePhase(Enum):
    ROUND1 = "Тур 1"
    ROUND2 = "Тур 2"
    ROUND3 = "Тур 3"
    FINAL = "Финал"
    SUPER = "Суперигра"

class PlayerStatus(Enum):
    ACTIVE = "играет"
    ELIMINATED = "выбыл"
    WON_ROUND = "победитель тура"   # для финалистов

class RoundState:
    def __init__(self, name: str, players: list[Player], puzzle: Puzzle):
        self.name = name
        self.players = players   # 3 игрока
        self.puzzle = puzzle
        self.active_players = players.copy()  # кто ещё не выбыл
        self.consecutive_hits = 0  # для правила трёх ходов
        self.winner: Player | None = None

class GameState:
    def __init__(self):
        self.phase = GamePhase.ROUND1
        self.rounds: list[RoundState] = []  # три тура + финал
        self.current_round_idx = 0
        self.finalists: list[Player] = []   # победители трёх туров
        self.current_player_idx = 0         # кто ходит в текущем туре
        self.last_sector: WheelSector | None = None
        self.last_letter_found = False
        self.prize_offer = None  # для сектора Приз

    def get_current_round(self):
        """Возвращает текущий объект RoundState (или аналогичный)."""
        return self.rounds[self.current_round_idx] if hasattr(self, 'rounds') else None

    def current_player(self):
        """Возвращает текущего активного игрока."""
        round_ = self.get_current_round()
        if round_ and round_.active_players:
            return round_.active_players[self.current_player_idx]
        return None

    def eliminate_player(self, player):
        """Вывести игрока из текущего тура."""
        round_ = self.get_current_round()
        if player in round_.active_players:
            round_.active_players.remove(player)
        # Если это был текущий игрок, переключить ход
        if self.current_player() == player:
            self.next_player()

    def try_reveal_letter(self, letter, multiplier=1):
        """Попытка открыть букву с учётом множителя. Возвращает dict с результатами."""
        # ... логика, возвращает {"letter_found": bool, "game_over": bool, "eliminated": bool}
        pass

    def guess_word(self, word):
        """Проверка угадывания слова. Возвращает {"correct": bool}."""
        pass

    def get_consecutive_hits(self):
        """Возвращает количество подряд верных букв текущим игроком."""
        return self._consecutive_hits

    def add_finalist(self, player):
        """Добавить победителя тура в список финалистов."""
        self.finalists.append(player)

    def init_final_round(self):
        """Создать финальный раунд с финалистами и вопросом."""
        pass

    def get_final_winner(self):
        """Вернуть победителя финала."""
        return self.final_winner if hasattr(self, 'final_winner') else None

    def reset_round(self):
        """Сбросить состояние для нового тура (revealed_letters, счётчики ходов)."""
        self.revealed_letters.clear()
        self._recompute_mask()
        self._consecutive_hits = 0
        # и т.д.

Category = Literal["regular", "final", "super"]


@dataclass
class Puzzle:
    question: str
    answer: str
    explanation: str = ""
    category: Category = "regular"  # hardcoded categories; operator doesn't choose manually


@dataclass
class Player:
    name: str
    score: int = 0


@dataclass
class Trio:
    label: str
    players: list[Player] = field(default_factory=list)


@dataclass
class LogEvent:
    ts: datetime
    text: str


class GameState:
    def __init__(self) -> None:
        self.trios_history: list[Trio] = []
        self.current_trio: Trio = Trio(label="Тройка 1", players=[Player("Игрок 1"), Player("Игрок 2"), Player("Игрок 3")])

        self.puzzles: list[Puzzle] = []
        self.current_puzzle_idx: int | None = None

        self.revealed_letters: set[str] = set()
        self.guess_mask: str = ""

        self._log: list[LogEvent] = []
        self._log_subscribers: list[Callable[[LogEvent], None]] = []

        self._phrase_subscribers: list[Callable[[str], None]] = []

    # -------------------- logging --------------------
    def subscribe_log(self, cb: Callable[[LogEvent], None]) -> None:
        self._log_subscribers.append(cb)

    def log(self, text: str) -> None:
        ev = LogEvent(ts=datetime.now(), text=text)
        self._log.append(ev)
        for cb in list(self._log_subscribers):
            cb(ev)

    def clear_log(self) -> None:
        self._log.clear()
        self.log("Лог очищен.")

    # -------------------- phrases --------------------
    def subscribe_phrase(self, cb: Callable[[str], None]) -> None:
        self._phrase_subscribers.append(cb)

    def play_phrase(self, phrase: str) -> None:
        # UI may choose how to render (text bubble, status line, audio later, etc.)
        self.log(f"Реплика: {phrase}")
        for cb in list(self._phrase_subscribers):
            cb(phrase)

    # -------------------- puzzle --------------------
    def add_puzzle(self, p: Puzzle) -> None:
        p.answer = normalize_answer(p.answer)
        self.puzzles.append(p)
        self.log(f"Добавлен вопрос: «{p.question}» (категория: {p.category})")
        if self.current_puzzle_idx is None:
            self.set_current_puzzle(0)

    def set_current_puzzle(self, idx: int) -> None:
        if not (0 <= idx < len(self.puzzles)):
            raise IndexError("Puzzle index out of range")
        self.current_puzzle_idx = idx
        self.revealed_letters.clear()
        self._recompute_mask()
        self.log(f"Выбран вопрос #{idx + 1}: «{self.puzzles[idx].question}»")

    def add_word_quick(self, word: str, category: Category = "regular") -> None:
        self.add_puzzle(Puzzle(question="(добавлено быстро)", answer=word, explanation="", category=category))

    def try_reveal_letter(self, letter: str) -> int:
        letter = normalize_letter(letter)
        p = self.current_puzzle()
        if not p:
            self.log("Нет активного вопроса.")
            return 0
        if letter in self.revealed_letters:
            self.log(f"Буква «{letter}» уже открыта.")
            return 0
        if letter not in p.answer:
            self.log(f"Буквы «{letter}» в слове нет.")
            return 0
        self.revealed_letters.add(letter)
        n = sum(1 for ch in p.answer if ch == letter)
        self._recompute_mask()
        self.log(f"Открыта буква «{letter}» ×{n}.")
        return n

    def current_puzzle(self) -> Puzzle | None:
        if self.current_puzzle_idx is None:
            return None
        if not (0 <= self.current_puzzle_idx < len(self.puzzles)):
            return None
        return self.puzzles[self.current_puzzle_idx]

    def _recompute_mask(self) -> None:
        p = self.current_puzzle()
        if not p:
            self.guess_mask = ""
            return
        mask_chars: list[str] = []
        for ch in p.answer:
            if ch == " ":
                mask_chars.append(" ")
            elif ch in self.revealed_letters:
                mask_chars.append(ch)
            else:
                mask_chars.append("•")
        self.guess_mask = "".join(mask_chars)

    # -------------------- trio / scores --------------------
    def set_player_name(self, idx: int, name: str) -> None:
        name = (name or "").strip() or f"Игрок {idx + 1}"
        self.current_trio.players[idx].name = name
        self.log(f"Имя игрока {idx + 1}: {name}")

    def add_score(self, idx: int, delta: int) -> None:
        self.current_trio.players[idx].score += int(delta)
        self.log(f"Очки игрока {idx + 1}: {self.current_trio.players[idx].score} (Δ {delta})")

    def set_score(self, idx: int, score: int) -> None:
        self.current_trio.players[idx].score = int(score)
        self.log(f"Очки игрока {idx + 1}: {self.current_trio.players[idx].score} (установлено)")

    def next_trio(self) -> None:
        # persist current trio to history
        self.trios_history.append(self.current_trio)
        next_idx = len(self.trios_history) + 1
        self.current_trio = Trio(
            label=f"Тройка {next_idx}",
            players=[Player("Игрок 1"), Player("Игрок 2"), Player("Игрок 3")],
        )
        self.revealed_letters.clear()
        self._recompute_mask()
        self.log(f"Переход к новой тройке: {self.current_trio.label}")


def normalize_letter(s: str) -> str:
    s = (s or "").strip().upper()
    if not s:
        return ""
    # take first user-perceived letter (simple)
    ch = s[0]
    if ch == "Ё":
        ch = "Е"
    return ch


def normalize_answer(s: str) -> str:
    s = (s or "").strip().upper()
    s = s.replace("Ё", "Е")
    # keep spaces, remove repeated whitespace
    s = " ".join(s.split())
    return s

