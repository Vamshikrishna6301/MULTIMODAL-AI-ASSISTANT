from execution.accessibility.nvda_bridge import NVDABridge

nvda = NVDABridge()

print("\nREAD SCREEN\n")

items = nvda.read_screen()

for item in items:
    print(item)

print("\nNEXT ITEM\n")

print(nvda.next_item())

print("\nACTIVATE\n")

print(nvda.activate())