class DOMRegionAnalyzer:
    """
    Extracts semantic regions from a webpage.
    Detects sidebar, main content, navigation and form areas.
    """

    def analyze(self, driver):

        script = """
        function extractRegion(root, selector) {
            let region = root.querySelector(selector);
            if(!region) return null;

            let items = [];
            let nodes = region.querySelectorAll("a,button,input,textarea");

            nodes.forEach(el => {

                let text =
                    el.innerText ||
                    el.value ||
                    el.placeholder ||
                    el.getAttribute("aria-label");

                if(text && text.trim().length > 1){
                    items.push({
                        role: el.tagName,
                        name: text.trim()
                    });
                }
            });

            return items;
        }

        let result = {};

        result.sidebar = extractRegion(document, "aside, nav");

        result.main = extractRegion(document, "main, article");

        result.forms = extractRegion(document, "form");

        return result;
        """

        try:
            return driver.execute_script(script)
        except Exception:
            return {}