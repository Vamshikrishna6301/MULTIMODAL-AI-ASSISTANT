WINDOW_NOISE = {
    "Minimize",
    "Restore",
    "Maximize",
    "Close"
}

ROLE_PRIORITY = {
    "Edit": 10,
    "Button": 9,
    "Hyperlink": 9,
    "MenuItem": 8,
    "ListItem": 7,
    "Text": 5
}


def filter_elements(elements):

    filtered = []
    seen = set()

    for el in elements:

        name = el.name.strip()

        if not name:
            continue

        if name in WINDOW_NOISE:
            continue

        key = el.key()

        if key in seen:
            continue

        seen.add(key)
        filtered.append(el)

    filtered.sort(
        key=lambda x: ROLE_PRIORITY.get(x.role, 0),
        reverse=True
    )

    return filtered