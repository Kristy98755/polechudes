from __future__ import annotations

import tkinter as tk

from app.ui_player_v2 import PlayerWindowV2


def main() -> None:
    root = tk.Tk()
    root.withdraw()  # we manage our own top-level windows

    player = PlayerWindowV2(root=root)
    try:
        player.window.geometry("+60+40")
    except Exception:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()

