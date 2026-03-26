import webbrowser
from urllib.parse import quote_plus
from core.response_model import UnifiedResponse


class WindowsBrowserAdapter:
    """
    Production-Level Windows Browser Adapter

    Improvements:
    - URL normalization
    - safer domain detection
    - better error protection
    """

    def open_browser(self) -> UnifiedResponse:
        try:
            success = webbrowser.open("https://www.google.com", new=2)

            if not success:
                raise RuntimeError("Browser launch returned False")

            return UnifiedResponse.success_response(
                category="execution",
                spoken_message="Opening your browser."
            )

        except Exception as e:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="I was unable to open your browser.",
                error_code="BROWSER_OPEN_FAILED",
                technical_message=str(e)
            )

    # -----------------------------------------------------

    def search(self, query: str) -> UnifiedResponse:

        if not query:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="No search query was provided.",
                error_code="NO_QUERY"
            )

        try:
            query = query.strip()

            # Direct URL
            if query.startswith(("http://", "https://")):
                webbrowser.open(query, new=2)
                return UnifiedResponse.success_response(
                    category="execution",
                    spoken_message="Opening the requested website."
                )

            # Domain-like query (youtube.com)
            if "." in query and " " not in query:
                url = f"https://{query}"
                webbrowser.open(url, new=2)

                return UnifiedResponse.success_response(
                    category="execution",
                    spoken_message=f"Opening {query}."
                )

            # Google search
            encoded = quote_plus(query)
            url = f"https://www.google.com/search?q={encoded}"
            webbrowser.open(url, new=2)

            return UnifiedResponse.success_response(
                category="execution",
                spoken_message=f"Searching for {query}."
            )

        except Exception as e:
            return UnifiedResponse.error_response(
                category="execution",
                spoken_message="I was unable to perform the search.",
                error_code="SEARCH_FAILED",
                technical_message=str(e)
            )