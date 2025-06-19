import asyncio
from logging import Logger, getLogger

from src.config.configurer import Configurer
from src.config.model.retriever.vector_store import VectorStoreConfiguration


class VectorStoreConfigurer(Configurer):
    _logger: Logger = getLogger(__name__)

    def configure(self, config: VectorStoreConfiguration, /, **kwargs):
        """
        Configures a vector store based on the provided configuration. This method supports
        various types of vector store configurations and manages their specific setup processes.

        Args:
            config: The configuration object for the vector store.
                    This object dictates the type of vector store to be configured
                    and includes all necessary parameters for its setup.

        Raises:
            NotImplementedError: If the provided `config` type is not supported. Currently,
                                 only `ChromaVSConfiguration` is explicitly supported.
        """
        pass

    async def async_configure(self, config: VectorStoreConfiguration, /, **kwargs):
        """
        Async-configures a vector store based on the provided configuration. This method supports
        various types of vector store configurations and manages their specific setup processes.

        Args:
            config: The configuration object for the vector store.
                    This object dictates the type of vector store to be configured
                    and includes all necessary parameters for its setup.

        Raises:
            NotImplementedError: If the provided `config` type is not supported. Currently,
                                 only `ChromaVSConfiguration` is explicitly supported.
        """
        pass

    def destroy(self, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_destroy(**kwargs))

    async def async_destroy(self, **kwargs):
        pass
