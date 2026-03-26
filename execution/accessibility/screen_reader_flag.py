import ctypes

SPI_SETSCREENREADER = 0x0047


def enable_screen_reader_mode():
    """
    Tells Windows a screen reader is active.
    This makes Chrome, Electron apps, and many others
    expose full accessibility APIs automatically.
    """

    ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETSCREENREADER,
        True,
        None,
        0
    )                                                                                                                           