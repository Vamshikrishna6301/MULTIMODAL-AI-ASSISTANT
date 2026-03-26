import win32gui

hwnd = win32gui.GetForegroundWindow()
title = win32gui.GetWindowText(hwnd)

print("Active Window Title:", title)