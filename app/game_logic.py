from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class PuzzleItem:
    question: str
    answer: str
    explanation: str = ""


class GameLogic:
    def __init__(self, puzzles: list[PuzzleItem]) -> None:
        if not puzzles:
            raise ValueError("Нужен хотя бы один вопрос")
        self.puzzles = puzzles
        self.current_index = 0
        self.revealed_letters: set[str] = set()
        self._subscribers: list[Callable[[], None]] = []

    def subscribe(self, cb: Callable[[], None]) -> None:
        self._subscribers.append(cb)

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            cb()

    @property
    def current(self) -> PuzzleItem:
        return self.puzzles[self.current_index]

    @property
    def solved(self) -> bool:
        return self.masked_answer == self.current.answer

    @property
    def masked_answer(self) -> str:
        out: list[str] = []
        for ch in self.current.answer:
            if ch == " ":
                out.append(" ")
            elif ch in self.revealed_letters:
                out.append(ch)
            else:
                out.append("•")
        return "".join(out)

    def reveal_letter(self, letter: str) -> int:
        letter = self._normalize_letter(letter)
        if not letter:
            return 0
        if letter in self.revealed_letters:
            return 0
        count = self.current.answer.count(letter)
        if count:
            self.revealed_letters.add(letter)
            self._notify()
        return count

    def try_guess(self, guess: str) -> bool:
        guess = self._normalize_text(guess)
        if not guess:
            return False
        if guess == self.current.answer:
            for ch in self.current.answer:
                if ch != " ":
                    self.revealed_letters.add(ch)
            self._notify()
            return True
        return False

    def set_puzzle(self, index: int) -> None:
        if not (0 <= index < len(self.puzzles)):
            raise IndexError("Индекс вопроса вне диапазона")
        self.current_index = index
        self.revealed_letters.clear()
        self._notify()

    def next_puzzle(self) -> None:
        nxt = (self.current_index + 1) % len(self.puzzles)
        self.set_puzzle(nxt)

    @staticmethod
    def _normalize_letter(letter: str) -> str:
        text = GameLogic._normalize_text(letter)
        return text[:1]

    @staticmethod
    def _normalize_text(text: str) -> str:
        return (text or "").strip().upper().replace("Ё", "Е")


def parse_puzzles(raw: str) -> list[PuzzleItem]:
    """
    Формат:
    Вопрос | Ответ | Пояснение
    ...
    """
    items: list[PuzzleItem] = []
    for i, line in enumerate((raw or "").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            raise ValueError(f"Строка {i}: нужен формат 'Вопрос | Ответ | Пояснение'")
        question, answer = parts[0], parts[1]
        explanation = parts[2] if len(parts) >= 3 else ""
        if not question or not answer:
            raise ValueError(f"Строка {i}: вопрос и ответ не должны быть пустыми")
        items.append(
            PuzzleItem(
                question=question,
                answer=GameLogic._normalize_text(answer),
                explanation=explanation,
            )
        )
    if not items:
        raise ValueError("Список вопросов пуст")
    return items
