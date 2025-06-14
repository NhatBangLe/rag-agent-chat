import asyncio
import logging
import os

import jsonpickle

from src.config.configurer import Configurer
from src.config.configurer.search_tool import SearchToolConfigurer
from src.config.configurer.vector_store import VectorStoreConfigurer
from src.config.model.agent import AgentConfiguration
from src.config.model.recognizer.image.main import ImageRecognizerConfiguration
from src.process.recognizer.image.main import ImageRecognizer
from src.util.function import get_config_folder_path


def _get_config_file_path():
    config_file_name = "config.json"
    config_path = os.path.join(get_config_folder_path(), config_file_name)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f'Missing {config_file_name} file in {config_path}')
    return config_path


class AgentConfigurer(Configurer):
    _config: AgentConfiguration | None = None
    _vs_configurer: VectorStoreConfigurer | None = None
    _search_configurer: SearchToolConfigurer | None = None
    _image_recognizer: ImageRecognizer | None = None
    _logger = logging.getLogger(__name__)

    ENSEMBLE_RETRIEVER_DESCRIPTION = (
        "A highly robust and comprehensive tool designed to retrieve the most relevant and "
        "accurate information from a vast knowledge base by combining multiple advanced search algorithms."
        "**USE THIS TOOL WHENEVER THE USER ASKS A QUESTION REQUIRING EXTERNAL KNOWLEDGE,"
        "FACTUAL INFORMATION, CURRENT EVENTS, OR DATA BEYOND YOUR INTERNAL TRAINING.**"
        "**Examples of when to use this tool:**"
        "- \"the capital of France?\""
        "- \"the history of the internet.\""
        "- \"the latest developments in AI?\""
        "- \"quantum entanglement.\""
        "**Crucially, use this tool for any query that cannot be answered directly from your"
        "pre-trained knowledge, especially if it requires up-to-date, specific, or detailed factual data.**"
        "The tool takes a single, concise search query as input."
        "If you cannot answer after using this tool, you can use another tool to retrieve more information.")

    def configure(self, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_configure(**kwargs))

    async def async_configure(self, **kwargs):
        self._config = self._load_config()
        self._image_recognizer = self._configure_image_recognizer(self._config.image_recognizer)

    def destroy(self, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_destroy(**kwargs))

    async def async_destroy(self, **kwargs):
        pass

    def _load_config(self):
        """
        Loads the agent configuration from the configuration file.

        This method reads the JSON content from the config file and
        validates it against the `AgentConfiguration` Pydantic model.
        The loaded configuration is then stored in the `self._config` attribute.

        Raises:
            FileNotFoundError: If the `DEFAULT_CONFIG_PATH` does not exist.
            pydantic.ValidationError: If the content of the configuration file
                does not conform to the structure defined by the `AgentConfiguration` model.
            Exception: For other potential errors during file reading.

        Returns:
            None
        """
        config_file_path = _get_config_file_path()
        self._logger.info(f'Loading configuration...')
        with open(config_file_path, mode="r") as config_file:
            json = config_file.read()
        return AgentConfiguration.model_validate(jsonpickle.decode(json))

    def _configure_image_recognizer(self, config: ImageRecognizerConfiguration) -> ImageRecognizer | None:
        self._logger.debug("Configuring image recognizer...")

        if config is None or config.enable is False:
            self._logger.info("Image recognizer is disabled.")
            return None

        max_workers = os.getenv("IMAGE_RECOGNIZER_MAX_WORKERS", "4")
        recognizer = ImageRecognizer(config=self._config.image_recognizer, max_workers=int(max_workers))
        recognizer.configure()

        self._logger.debug("Configured image recognizer successfully.")
        return recognizer

    @property
    def config(self):
        return self._config

    @property
    def image_recognizer(self):
        return self._image_recognizer

    @property
    def vector_store_configurer(self):
        return self._vs_configurer
