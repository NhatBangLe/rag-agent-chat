import logging
from datetime import timedelta

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StdioConnection, StreamableHttpConnection

from src.config.configurer.interface.mcp import MCPConfigurer
from src.config.model.mcp import MCPConfiguration, MCPTransport

SupportedConnection = StdioConnection | StreamableHttpConnection


class MCPConfigurerImpl(MCPConfigurer):
    _config: MCPConfiguration | None = None
    _client: MultiServerMCPClient | None = None
    _logger = logging.getLogger(__name__)

    def configure(self, config, /, **kwargs):
        self._config = config

        connections: dict[str, SupportedConnection] = {}
        for server, cfg in config.connections.items():
            if cfg.type == MCPTransport.STREAMABLE_HTTP:
                conn = StreamableHttpConnection(
                    transport="streamable_http",
                    url=cfg.url,
                    headers=cfg.headers,
                    timeout=timedelta(seconds=cfg.timeout),
                    sse_read_timeout=timedelta(seconds=cfg.sse_read_timeout),
                    terminate_on_close=cfg.terminate_on_close,
                    session_kwargs=None,
                    httpx_client_factory=None)
            elif cfg.type == MCPTransport.STDIO:
                conn = StdioConnection(
                    transport="stdio",
                    command=cfg.command,
                    args=cfg.args,
                    env=cfg.env,
                    cwd=cfg.cwd,
                    encoding=cfg.encoding,
                    encoding_error_handler=cfg.encoding_error_handler,
                    session_kwargs=None)
            else:
                raise ValueError(f'Unsupported connection type: {type(cfg)}')
            connections[server] = conn
        self._client = MultiServerMCPClient(connections)

    async def async_configure(self, config, /, **kwargs):
        self.configure(config, **kwargs)

    def destroy(self, **kwargs):
        pass

    async def async_destroy(self, **kwargs):
        self.destroy()

    async def get_tools(self):
        try:
            tools = await self._client.get_tools()
            return tools
        except Exception as e:
            self._logger.warning(f"Failed to get tools from MCP servers.")
            self._logger.debug(e)
            return []
