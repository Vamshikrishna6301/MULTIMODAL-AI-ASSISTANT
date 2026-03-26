from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class BrowserDOMReader:

    def __init__(self):

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )

        self.driver.implicitly_wait(3)

    # ----------------------------------------

    def read_page(self):

        elements = []

        # Buttons
        buttons = self.driver.find_elements("tag name", "button")

        for b in buttons:
            text = b.text.strip()
            if text:
                elements.append(("Button", text))

        # Inputs
        inputs = self.driver.find_elements("tag name", "textarea")

        for _ in inputs:
            elements.append(("Input", "Text input field"))

        # Links
        links = self.driver.find_elements("tag name", "a")

        for l in links:
            text = l.text.strip()
            if text:
                elements.append(("Link", text))

        return elements