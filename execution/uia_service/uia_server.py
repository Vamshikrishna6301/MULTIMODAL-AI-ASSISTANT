import socket
import json
import threading
import pythoncom
from pywinauto import Desktop

HOST = "127.0.0.1"
PORT = 56789

desktop = None

# =====================================================
# GLOBAL ELEMENT CACHE
# =====================================================

ELEMENT_CACHE = []

# =====================================================
# CONTROL TYPES WE WANT
# =====================================================

INTERACTIVE_TYPES = {
    "Button",
    "Hyperlink",
    "MenuItem",
    "Edit",
    "TabItem",
    "CheckBox",
    "RadioButton",
    "ComboBox",
    "ListItem",
    "TreeItem",
    "Document",
    "Pane",
    "Group",
    "Custom",
    "Text",
    "MenuBar",
    "ToolBar",
}
NOISE_WORDS = {
    "x", "|", "+", "€", "-", ".", "•"
}

MAX_DEPTH = 7
MAX_ELEMENTS = 60


# =====================================================
# ACTIVE WINDOW
# =====================================================

def get_active_window():
    try:
        return desktop.window(active_only=True)
    except Exception:
        return None


# =====================================================
# ELEMENT VALIDATION
# =====================================================

def is_valid_element(element):

    try:
        name = element.window_text()
        role = element.element_info.control_type

        if role not in INTERACTIVE_TYPES:
            return False

        if name:
            name = name.strip()

            if name.lower() in NOISE_WORDS:
                return False

        return True

    except Exception:
        return False
    
def element_priority(element):

    role = element.element_info.control_type

    high = {"Button", "Hyperlink", "Edit", "MenuItem"}
    medium = {"TabItem", "ListItem", "TreeItem"}

    if role in high:
        return 0

    if role in medium:
        return 1

    return 2

# =====================================================
# BREADTH-FIRST TREE TRAVERSAL
# =====================================================

def collect_elements(window):

    elements = []
    queue = [(window, 0)]
    seen = set()

    while queue:

        element, depth = queue.pop(0)

        if depth > MAX_DEPTH:
            continue

        if len(elements) >= MAX_ELEMENTS:
            return elements

        try:
            children = element.children()
        except Exception:
            continue

        # Limit extremely large containers
        if len(children) > 80:
            children = children[:80]

        for child in children:

            try:

                name = child.window_text()
                role = child.element_info.control_type
                print("UIA NODE:", role, "|", name)

                key = (name.lower(), role)

                if key not in seen and is_valid_element(child):

                    elements.append(child)
                    seen.add(key)

                    if len(elements) >= MAX_ELEMENTS:
                        return elements

                queue.append((child, depth + 1))

            except Exception:
                continue

    return elements
# =====================================================
# SERIALIZE ELEMENT
# =====================================================

def serialize_element(element, index):

    try:

        rect = element.rectangle()

        bbox = [rect.left, rect.top, rect.right, rect.bottom]

    except Exception:

        bbox = None

    try:

        name = element.window_text().strip()

    except Exception:

        name = ""

    try:

        role = element.element_info.control_type

    except Exception:

        role = "Unknown"

    return {
        "index": index,
        "name": name,
        "role": role,
        "bbox": bbox
    }


# =====================================================
# READ SCREEN
# =====================================================

def read_screen():

    global ELEMENT_CACHE

    window = get_active_window()

    if not window:
        return {"status": "error", "message": "No active window"}

    try:

        title = window.window_text()

        elements = collect_elements(window)

        ELEMENT_CACHE = elements

        serialized = []
        elements = sorted(
    elements,
    key=lambda e: (
        element_priority(e),
        e.rectangle().top,
        e.rectangle().left
    )
)
        elements = elements[:MAX_ELEMENTS]

        for idx, element in enumerate(elements, start=1):

            serialized.append(
                serialize_element(element, idx)
            )

        return {
            "status": "success",
            "window": title,
            "elements": serialized
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# =====================================================
# CLICK INDEX
# =====================================================

def click_index(index):

    global ELEMENT_CACHE

    if not isinstance(index, int):
        return {"status": "error", "message": "Invalid index"}

    if index < 1 or index > len(ELEMENT_CACHE):
        return {"status": "error", "message": "Invalid index"}

    target = ELEMENT_CACHE[index - 1]

    try:

        target.invoke()

    except Exception:

        try:
            target.click_input()
        except Exception:
            return {
                "status": "error",
                "message": "Element not clickable"
            }

    return {
        "status": "success",
        "message": "Element activated"
    }


# =====================================================
# CLICK BY NAME
# =====================================================

def click_by_name(name_query):

    global ELEMENT_CACHE

    if not name_query:
        return {"status": "error", "message": "Invalid name"}

    name_query = name_query.lower()

    for element in ELEMENT_CACHE:

        try:

            element_name = element.window_text().lower()

            if name_query in element_name:

                try:
                    element.invoke()
                except Exception:
                    element.click_input()

                return {
                    "status": "success",
                    "message": f"Clicked {element.window_text()}"
                }

        except Exception:
            continue

    return {"status": "error", "message": "No matching element found"}


# =====================================================
# REQUEST ROUTER
# =====================================================

def handle_request(data):

    action = data.get("action")

    if action == "read_screen":
        return read_screen()

    if action == "click_index":
        return click_index(data.get("index"))

    if action == "click_by_name":
        return click_by_name(data.get("name"))

    return {"status": "error", "message": "Unknown action"}


# =====================================================
# CLIENT HANDLER
# =====================================================

def client_thread(conn):

    pythoncom.CoInitialize()

    try:

        data = conn.recv(8192).decode()

        if not data:
            return

        request = json.loads(data)

        response = handle_request(request)

        conn.sendall(json.dumps(response).encode())

    except Exception as e:

        conn.sendall(json.dumps({
            "status": "error",
            "message": str(e)
        }).encode())

    finally:

        conn.close()
        pythoncom.CoUninitialize()


# =====================================================
# SERVER
# =====================================================

def start_server():

    global desktop

    pythoncom.CoInitialize()

    desktop = Desktop(backend="uia")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))

    server.listen(10)

    print("UIA Service Running on port", PORT)

    while True:

        conn, addr = server.accept()

        thread = threading.Thread(
            target=client_thread,
            args=(conn,),
            daemon=True
        )

        thread.start()


if __name__ == "__main__":
    start_server()