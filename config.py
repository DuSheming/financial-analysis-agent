"""
多 LLM 提供商配置工厂

支持 Claude (via intermediary), DeepSeek, Kimi, Qwen
所有提供商都使用 OpenAI 兼容 API
"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class LLMConfig:
    """多 LLM 提供商配置"""

    PROVIDERS = ["claude", "deepseek", "kimi", "qwen"]

    # 默认温度设置（可通过环境变量覆盖）
    DEFAULT_TEMPERATURES = {
        "planner": float(os.getenv("PLANNER_TEMPERATURE", "1")),
        "analyst": float(os.getenv("ANALYST_TEMPERATURE", "1")),
        "decider": float(os.getenv("DECIDER_TEMPERATURE", "1")),
    }

    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
    DATA_FETCH_TIMEOUT = int(os.getenv("DATA_FETCH_TIMEOUT", "30"))

    @staticmethod
    def get_llm(temperature: float = 0.5) -> ChatOpenAI:
        """
        获取配置的 LLM 实例

        Args:
            temperature: 0.0-1.0，默认 0.5

        Returns:
            ChatOpenAI 实例
        """
        provider = os.getenv("LLM_PROVIDER", "kimi").lower()

        if provider not in LLMConfig.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        if provider == "claude":
            api_key = os.getenv("CLAUDE_API_KEY")
            base_url = os.getenv("CLAUDE_BASE_URL")
            model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

            if not api_key or not base_url:
                raise ValueError("CLAUDE_API_KEY and CLAUDE_BASE_URL required")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )

        elif provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY required")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )

        elif provider == "kimi":
            api_key = os.getenv("KIMI_API_KEY")
            base_url = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
            model = os.getenv("KIMI_MODEL", "kimi-k2.5")

            if not api_key:
                raise ValueError("KIMI_API_KEY required")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )

        elif provider == "qwen":
            api_key = os.getenv("QWEN_API_KEY")
            base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            model = os.getenv("QWEN_MODEL", "qwen3.5-plus")

            if not api_key:
                raise ValueError("QWEN_API_KEY required")

            return ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=LLMConfig.MAX_TOKENS,
            )


# 全局配置实例
llm_config = LLMConfig()
