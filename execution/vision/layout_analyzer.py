# vision/layout_analyzer.py

class LayoutAnalyzer:
    """
    Basic screen layout analyzer.
    Determines UI zones like menus, toolbars, and content areas.
    """

    def analyze(self, elements):

        layout = {
            "menu_candidates": [],
            "toolbar_candidates": [],
            "content_candidates": []
        }

        for e in elements:

            x1, y1, x2, y2 = e.bbox
            width = x2 - x1
            height = y2 - y1

            # menu bar usually small height at top
            if y1 < 100 and height < 40:
                layout["menu_candidates"].append(e)

            # toolbars slightly larger buttons
            elif height < 80 and width < 200:
                layout["toolbar_candidates"].append(e)

            else:
                layout["content_candidates"].append(e)

        return layout