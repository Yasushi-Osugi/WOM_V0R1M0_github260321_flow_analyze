#pysi/gui/business_animation_demo.py

import tkinter as tk

from pysi.gui.business_animation.business_animation_panel import BusinessAnimationPanel


def main() -> None:
    root = tk.Tk()
    root.title("WOM Business Performance Animation v0.1")
    root.geometry("1280x720")

    BusinessAnimationPanel(root)

    root.mainloop()


if __name__ == "__main__":
    main()
