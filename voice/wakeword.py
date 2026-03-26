import difflib

def is_wake_word(text: str, wake_word: str, threshold=0.75) -> bool:
    text = text.lower()
    wake_word = wake_word.lower()

    words = text.split()
    for w in words:
        ratio = difflib.SequenceMatcher(None, w, wake_word).ratio()
        if ratio >= threshold:
            return True
    return False
