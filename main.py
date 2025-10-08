#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1: Launch default browser → focus it → click Blue Play button.

Requires:
    pip install pyautogui opencv-python pygetwindow

Make sure your screenshot of the Blue Play button is saved as:
    assets/blue_play_button.png
"""

import time
import webbrowser
import pyautogui as pag
import pygetwindow as gw
from datetime import datetime

# ───────────────────────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────────────────────
GAME_URL = "https://www.roblox.com/games/920587237/"
ASSET_PATH = "assets/blue_play_button.png"
BROWSER_TITLE_HINT = "Adopt Me"   # adjust if your browser tab shows differently
SEARCH_TIMEOUT = 8.0
CLICK_DELAY = 0.1

# ───────────────────────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────────────────────
def focus_window(title_hint: str, timeout: float = 5.0) -> bool:
    """Focus the first window containing `title_hint` (case-insensitive)."""
    t0 = time.time()
    title_hint = title_hint.lower()
    while time.time() - t0 < timeout:
        for w in gw.getAllWindows():
            try:
                if title_hint in w.title.lower():
                    if w.isMinimized:
                        w.restore()
                        time.sleep(0.1)
                    w.activate()
                    print(f"[{datetime.now().time()}] Focused window: {w.title}")
                    return True
            except Exception:
                continue
        time.sleep(0.2)
    print(f"[!] Could not find window containing: {title_hint}")
    return False


def locate_and_click(image_path: str, confidence: float = 0.84, timeout: float = 5.0) -> bool:
    """Locate an image on screen and click its center."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        box = pag.locateOnScreen(image_path, confidence=confidence, grayscale=True)
        if box:
            x, y = pag.center(box)
            pag.moveTo(x, y, duration=0.1)
            pag.click()
            time.sleep(CLICK_DELAY)
            print(f"[{datetime.now().time()}] Clicked on image: {image_path}")
            return True
        time.sleep(0.1)
    print(f"[!] Could not find image: {image_path}")
    return False


# ───────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────
def main():
    print("[+] Launching browser to:", GAME_URL)
    webbrowser.open(GAME_URL)
    time.sleep(3)  # give browser time to launch

    print("[+] Focusing browser window…")
    focus_window(BROWSER_TITLE_HINT, timeout=8.0)

    print("[+] Looking for Blue Play button…")
    if locate_and_click(ASSET_PATH, confidence=0.85, timeout=SEARCH_TIMEOUT):
        print("[✓] Blue Play button clicked!")
    else:
        print("[✗] Failed to locate Blue Play button.")


if __name__ == "__main__":
    main()
