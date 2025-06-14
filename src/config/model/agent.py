from src.config.model import Configuration
from src.config.model.chat_model.main import LLMConfiguration
from src.config.model.prompt.main import PromptConfiguration
from src.config.model.recognizer.image import ImageRecognizerConfiguration
from src.config.model.retriever import RetrieverConfiguration
from src.config.model.tool import ToolConfiguration


class AgentConfiguration(Configuration):
    """
    Agent configuration class for deserialize configuration files to pydantic object.
    """
    agent_name: str
    version: str | None = None
    description: str | None = None
    image_recognizer: ImageRecognizerConfiguration | None = None
    retrievers: list[RetrieverConfiguration] | None = None
    tools: list[ToolConfiguration] | None = None
    llm: LLMConfiguration
    prompt: PromptConfiguration
