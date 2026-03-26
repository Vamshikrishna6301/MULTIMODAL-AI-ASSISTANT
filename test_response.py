from core.response_model import UnifiedResponse

response = UnifiedResponse.success_response(
    category="execution",
    spoken_message="Opening Chrome."
)

print(response)