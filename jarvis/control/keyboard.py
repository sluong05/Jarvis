import pyautogui


def hotkey(*keys):
    """Press a keyboard shortcut. E.g. hotkey('ctrl', 'c')"""
    pyautogui.hotkey(*keys)


def press(key):
    """Press a single key."""
    pyautogui.press(key)


def typewrite(text):
    """Type a string of text."""
    pyautogui.typewrite(text, interval=0.05)
