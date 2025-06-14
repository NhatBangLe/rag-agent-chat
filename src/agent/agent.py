import logging
from logging import Logger
from typing import Literal, Sequence

from src.agent.state import ClassifiedClass
from src.config.configurer.agent import AgentConfigurer
from src.util.main import Progress


def _convert_topics_to_str(topics: Sequence[tuple[ClassifiedClass, str]]):
    return [f'Topic: {desc} - Probability: {classified_class["probability"]}'
            for classified_class, desc in topics]


class Agent:
    _status: Literal["ON", "OFF", "RESTART"]
    _configurer: AgentConfigurer
    _is_configured: bool
    _logger: Logger

    def __init__(self, configurer: AgentConfigurer):
        self._status = "ON"
        self._configurer = configurer
        self._graph = None
        self._is_configured = False
        self._logger = logging.getLogger(__name__)

    async def configure(self, force: bool = False):
        if self._is_configured and not force:
            self._logger.debug("Not forcefully configuring the agent. Skipping...")
            return
        self._logger.info("Configuring agent...")
        await self._configurer.async_configure()
        self._is_configured = True
        self._logger.info("Agent configured successfully!")

    async def restart(self):
        """
        Triggers the process of restarting the agent, updates its status, reconfigures,
        and rebuilds its internal graph. The function yields progress updates
        throughout the restart process.

        Returns:
            The progress of the restart operation.
        """
        statuses: list[Progress] = [
            {
                "status": "RESTARTING",
                "percentage": 0.0
            },
            {
                "status": "RESTARTING",
                "percentage": 0.6
            },
            {
                "status": "RESTARTED",
                "percentage": 1.0
            }
        ]
        self._logger.info("Restarting agent...")
        yield statuses[0]

        self._status = "RESTART"
        await self.configure(force=True)
        yield statuses[1]
        self._status = "ON"
        yield statuses[2]

        self._logger.info("Agent restarted successfully!")

    async def shutdown(self):
        self._logger.info("Shutting down Agent...")
        await self._configurer.async_destroy()
        self._logger.info("Good bye! See you later.")

    @property
    def configurer(self):
        return self._configurer

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: Literal["ON", "OFF"]):
        self._status = value

    @property
    def is_configured(self):
        return self._is_configured
