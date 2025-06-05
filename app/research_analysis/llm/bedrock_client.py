from logging import getLogger
from typing import Optional

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import config

logger = getLogger(__name__)

_bedrock_llm: Optional[ChatBedrock] = None


def get_bedrock_llm() -> ChatBedrock:
    """Get Bedrock LLM client instance."""
    global _bedrock_llm
    if _bedrock_llm is None:
        _bedrock_llm = ChatBedrock(
            model_id=config.bedrock_model_id,
            region_name=config.bedrock_region,
            temperature=0,
            max_tokens=4000,
        )
        logger.info(
            "Initialized Bedrock LLM client with model %s", config.bedrock_model_id
        )
    return _bedrock_llm


async def chat_with_bedrock(system_prompt: str, user_prompt: str) -> str:
    """
    Send a chat request to Bedrock.

    Args:
        system_prompt: System message content
        user_prompt: User message content

    Returns:
        LLM response content
    """
    llm = get_bedrock_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    logger.debug(
        "Sending Bedrock request - System prompt length: %d, User prompt length: %d",
        len(system_prompt),
        len(user_prompt),
    )

    try:
        response = await llm.ainvoke(messages)
        logger.debug(
            "Bedrock response received, length: %d, content preview: %s",
            len(response.content),
            response.content[:200] + "..."
            if len(response.content) > 200
            else response.content,
        )
        return response.content
    except Exception as e:
        logger.error("Bedrock LLM call failed: %s", e)
        raise
