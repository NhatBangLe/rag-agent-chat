from logging import Logger, getLogger

from src.config.configurer import ToolConfigurer
from src.config.model.tool.search import SearchToolConfiguration


class SearchToolConfigurer(ToolConfigurer):
    _logger: Logger = getLogger(__name__)

    def configure(self, config: SearchToolConfiguration, /, **kwargs):
        """
        Configures and registers a search tool based on the provided configuration.

        This method inspects the type of `config` to determine which search tool
        to initialize. The configured tool is then stored internally for later use.

        Args:
            config: The configuration object for the search tool. This object
                    specifies the type of search tool to be set up and includes
                    all necessary parameters for its initialization.

        Raises:
            NotImplementedError:
                If the `config` type is not supported. Currently, only
                `DuckDuckGoSearchToolConfiguration` is supported.
        """
        self._logger.debug("Configuring search tool...")

        self._logger.debug("Configured search tool successfully.")

    async def async_configure(self, config: SearchToolConfiguration, /, **kwargs):
        """
        Async-configures and registers a search tool based on the provided configuration.

        This method inspects the type of `config` to determine which search tool
        to initialize. The configured tool is then stored internally for later use.

        Args:
            config: The configuration object for the search tool. This object
                    specifies the type of search tool to be set up and includes
                    all necessary parameters for its initialization.

        Raises:
            NotImplementedError:
                If the `config` type is not supported. Currently, only
                `DuckDuckGoSearchToolConfiguration` is supported.
        """
        self.configure(config)

    def destroy(self, **kwargs):
        pass

    async def async_destroy(self, **kwargs):
        pass
