"""DeepSeek 大模型 API 调用模块。"""

import os

import httpx


class LLMError(RuntimeError):
    """大模型调用失败。"""


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:

        self.api_key = (
            api_key
            or os.getenv("DEEPSEEK_API_KEY", "")
        )

        if not self.api_key:
            raise LLMError(
                "未配置 DEEPSEEK_API_KEY 环境变量。"
            )

        self.base_url = (
            base_url
            or os.getenv(
                "DEEPSEEK_BASE_URL",
                "https://api.deepseek.com",
            )
        ).rstrip("/")

        self.model = (
            model
            or os.getenv(
                "DEEPSEEK_MODEL",
                "deepseek-chat",
            )
        )

        self.timeout_seconds = (
            timeout_seconds
            or float(
                os.getenv(
                    "DEEPSEEK_TIMEOUT_SECONDS",
                    "180",
                )
            )
        )

    def review(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """调用模型并返回原始文本结果。"""

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
            "response_format": {
                "type": "json_object",
            },
            "temperature": 0.1,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
            ) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:2000]

            raise LLMError(
                f"DeepSeek API 返回 HTTP "
                f"{exc.response.status_code}: {body}"
            ) from exc

        except (httpx.HTTPError, ValueError) as exc:
            raise LLMError(
                f"调用 DeepSeek API 失败: {exc}"
            ) from exc

        try:
            content = (
                data["choices"][0]["message"]["content"]
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"DeepSeek 返回的数据结构不符合预期: {data}"
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError(
                "DeepSeek 返回了空结果。"
            )

        return content.strip()