import httpx
import loguru
from nemoguardrails.actions import action


@action(execute_async=True)
async def action_detect_injection(user_message: str) -> bool:
    """Check for prompt injection using ProtectAI model."""

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                "http://localhost:8000/v1/classify", json={"text": user_message}
            )

            if response.status_code == 200:
                result = response.json()
                loguru.logger.info(f"ProtectAI API response: {result}")
                is_injection = result.get("label") == "INJECTION"
                loguru.logger.info(f"Returning is injection: {is_injection}")
                return is_injection
        except Exception as e:
            loguru.logger.error(f"Error calling ProtectAI API: {e}")

    return False
