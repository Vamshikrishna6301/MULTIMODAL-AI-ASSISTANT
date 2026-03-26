from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Start browser
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

driver.get("https://chatgpt.com")

# Wait for page load
driver.implicitly_wait(5)

print("\n--- BUTTONS ---\n")

buttons = driver.find_elements("tag name", "button")

for b in buttons[:10]:
    text = b.text.strip()
    if text:
        print("Button:", text)

print("\n--- INPUT FIELDS ---\n")

inputs = driver.find_elements("tag name", "textarea")

for i in inputs[:5]:
    print("Input detected")

print("\n--- LINKS ---\n")

links = driver.find_elements("tag name", "a")

for l in links[:10]:
    text = l.text.strip()
    if text:
        print("Link:", text)

driver.quit()