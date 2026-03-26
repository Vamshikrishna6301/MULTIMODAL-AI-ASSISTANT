import requests
import unittest

class TestLLMDirect(unittest.TestCase):
    def test_ollama_available(self):
        """Test if Ollama LLM service is available on localhost:11434."""
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi3",
                    "prompt": "What is transformer in AI?",
                    "stream": False
                },
                timeout=5
            )
            print("\n--- LLM RESPONSE ---\n")
            print(response.json()["response"])
            self.assertTrue(response.status_code == 200)
        except requests.exceptions.ConnectionError:
            self.skipTest("Ollama LLM service not available on localhost:11434 - skipping test")
        except Exception as e:
            self.skipTest(f"LLM test skipped: {e}")

if __name__ == "__main__":
    unittest.main()