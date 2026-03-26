def safe_scan(window):

    try:
        children = window.children()

    except Exception:
        return []

    results = []

    for child in children[:30]:

        try:
            name = child.window_text()
            role = child.friendly_class_name()

            results.append((role, name))

        except Exception:
            continue

    return results
