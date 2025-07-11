import logging
from logging import Logger
from typing import Literal, Any, Sequence
from uuid import uuid4, UUID

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_experimental.text_splitter import SemanticChunker
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import StateSnapshot

from src.agent import StateConfiguration, State, AgentStatus
from src.config.configurer.agent import AgentConfigurer
from src.util import FileInformation, Progress
from src.util.constant import SUPPORTED_LANGUAGE_DICT
from src.util.function import get_documents


def _routing_function(state: State) -> Literal["suggest_questions", "query_or_respond"]:
    latest_messages = state["messages"][-1]

    if not isinstance(latest_messages, HumanMessage) or len(latest_messages.content.strip()) == 0:
        return "suggest_questions"
    return "query_or_respond"


ATTACHMENT_INSTRUCTION = ("You are given an attachment. There is the attachment information {attachment}."
                          "\nYou must do the following steps:"
                          "\nStep 1. Specify what attachment type you have by looking at a value of `mime_type` field of the attachment information."
                          "\nStep 2. Select the correct recognition tool to use based on the attachment type."
                          "\nStep 3. Call the selected recognition tool.")


class Agent:
    _status: Literal["ON", "OFF", "RESTART"]
    _configurer: AgentConfigurer
    _graph: CompiledStateGraph | None
    _is_configured: bool
    _logger: Logger

    def __init__(self, configurer: AgentConfigurer):
        self._status = "ON"
        self._configurer = configurer
        self._graph = None
        self._is_configured = False
        self._logger = logging.getLogger(__name__)

    def stream(self, input_state: State, config: RunnableConfig | None = None, *,
               stream_mode: Literal["values", "updates", "messages"] | None = None):
        """
        Args:
            input_state: The input to the graph.
            config: The configuration to use for the run.
            stream_mode: The mode to stream output, defaults to `self.stream_mode`.
                Options are:

                - `"values"`: Emit all values in the state after each step, including interrupts.
                    When used with functional API, values are emitted once at the end of the workflow.
                - `"updates"`: Emit only the node or task names and updates returned by the nodes or tasks after each step.
                    If multiple updates are made in the same step (e.g., multiple nodes are run), then those updates are emitted separately.
                - `"messages"`: Emit LLM messages token-by-token together with metadata for any LLM invocations inside nodes or tasks.
                    Will be emitted as 2-tuples `(LLM token, metadata)`.

                You can pass a list as the `stream_mode` parameter to stream multiple modes at once.
                The streamed outputs will be tuples of `(mode, data)`.
        """
        self.check_graph_available()

        graph: CompiledStateGraph = self._graph
        for state in graph.stream(input_state, config, stream_mode=stream_mode):
            yield state

    async def astream(self, input_state: State, config: RunnableConfig | None = None, *,
                      stream_mode: Literal["values", "updates", "messages"] | None = None):
        """
        Args:
            input_state: The input to the graph.
            config: The configuration to use for the run.
            stream_mode: The mode to stream output, defaults to `self.stream_mode`.
                Options are:

                - `"values"`: Emit all values in the state after each step, including interrupts.
                    When used with functional API, values are emitted once at the end of the workflow.
                - `"updates"`: Emit only the node or task names and updates returned by the nodes or tasks after each step.
                    If multiple updates are made in the same step (e.g., multiple nodes are run), then those updates are emitted separately.
                - `"messages"`: Emit LLM messages token-by-token together with metadata for any LLM invocations inside nodes or tasks.
                    Will be emitted as 2-tuples `(LLM token, metadata)`.

                You can pass a list as the `stream_mode` parameter to stream multiple modes at once.
                The streamed outputs will be tuples of `(mode, data)`.
        """
        self.check_graph_available()

        graph: CompiledStateGraph = self._graph
        async for state in graph.astream(input_state, config, stream_mode=stream_mode):
            yield state

    async def get_state_history(self,
                                config: RunnableConfig,
                                *,
                                use_filter: dict[str, Any] | None = None,
                                before: RunnableConfig | None = None,
                                limit: int | None = None) -> Sequence[StateSnapshot]:
        """Get the state history of the graph."""
        self.check_graph_available()

        graph: CompiledStateGraph = self._graph
        states: list[StateSnapshot] = []
        async for state in graph.aget_state_history(config, filter=use_filter, before=before, limit=limit):
            states.append(state)
        return states

    def get_state(self, config: RunnableConfig, *, sub_graphs: bool = False):
        self.check_graph_available()

        graph: CompiledStateGraph = self._graph
        return graph.get_state(config, subgraphs=sub_graphs)

    def delete_thread(self, thread_id: UUID):
        checkpointer = self._configurer.checkpointer
        if checkpointer is None:
            raise RuntimeError("Checkpointer is still not configured yet.")
        checkpointer.delete_thread(thread_id=str(thread_id))

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
        self.build_graph()
        self._status = "ON"
        yield statuses[2]

        self._logger.info("Agent restarted successfully!")

    async def embed_document(self, store_name: str, file_info: FileInformation):
        """
        Embeds a document into a specified vector store.

        This method takes a document's file information, loads it, splits it into
        chunks, and then embeds these chunks into the designated vector store.
        It generates unique UUIDs for each chunk to serve as their identifiers
        within the vector store.

        Args:
            store_name (str): The name of the vector store where the document
                chunks will be embedded. This name must correspond to a
                configured vector store.
            file_info (FileInformation): A dictionary containing information about
                the file to be embedded, including its 'path' and 'mime_type'.

        Raises:
            ValueError: If the `store_name` provided does not correspond
                to any vector store configured in the system.
        """
        self._logger.debug("Embedding document...")

        vector_store = self._configurer.vector_store_configurer.get_store(store_name)
        if vector_store is not None:
            self._logger.debug(f'Retrieving content from {file_info["name"]} document...')
            documents = await get_documents(file_info["path"], file_info["mime_type"])

            chunker = SemanticChunker(vector_store.embeddings)
            self._logger.debug(f'Splitting documents by using semantic similarity...')
            chunks = chunker.split_documents(documents)

            self._logger.debug(f'Adding chunks to vector store {store_name}...')
            uuids = [str(uuid4()) for _ in range(len(chunks))]
            added_ids = await vector_store.aadd_documents(documents=chunks, ids=uuids)

            self._logger.debug("Document embedded successfully!")
        else:
            raise ValueError(f"No vector store {store_name} configured.")
        return added_ids

    async def unembed_document(self, store_name: str, chunk_ids: Sequence[str]):
        self._logger.debug("Unembedding documents...")

        vector_store = self._configurer.vector_store_configurer.get_store(store_name)
        if vector_store is not None:
            await vector_store.adelete(ids=chunk_ids)
            self._logger.debug("Documents have been unembedded successfully!")
        else:
            raise ValueError(f"No vector store {store_name} configured.")

    async def sync_bm25(self):
        self._status = "RESTART"
        await self._configurer.sync_bm25()
        self._status = "ON"

    async def shutdown(self):
        self._logger.info("Shutting down Agent...")
        await self._configurer.async_destroy()
        self._logger.info("Good bye! See you later.")

    def build_graph(self):
        self._logger.info("Building graph...")

        self._logger.debug("Adding nodes to the graph...")
        graph = StateGraph(state_schema=State, config_schema=StateConfiguration)
        graph.add_node("query_or_respond", self._query_or_respond)
        graph.add_node("suggest_questions", self._suggest_questions)

        tools = self._configurer.tools
        if tools is not None and len(tools) != 0:
            self._logger.debug("Add tools to the graph...")
            graph.add_node("tools_1", ToolNode(tools))
            graph.add_conditional_edges("query_or_respond", tools_condition,
                                        {
                                            "tools": "tools_1",
                                            END: END,
                                        })
            graph.add_edge("tools_1", "query_or_respond")

            graph.add_node("tools_2", ToolNode(tools))
            graph.add_conditional_edges("suggest_questions", tools_condition,
                                        {
                                            "tools": "tools_2",
                                            END: END,
                                        })
            graph.add_edge("tools_2", "suggest_questions")

        graph.add_conditional_edges(START, _routing_function)

        self._logger.debug("Compiling the graph...")

        self._graph = graph.compile(name=self._configurer.config.agent_name,
                                    checkpointer=self._configurer.checkpointer)
        self._logger.info("Graph built successfully!")

    def check_graph_available(self):
        """
        Ensures that the agent's internal graph is properly initialized and that the agent
        is in an operational state before proceeding with any operations that require the graph.

        Raises:
            RuntimeError: If `self.is_configured` is `False`, indicating the agent has not been
                          configured. Users should call `configure()` to configure it.
            RuntimeError: If `self._graph` is `None`, indicating the agent graph has not been
                          initialized. Users should call `build_graph()` to initialize it.
            RuntimeError: If `self._status` is `"OFF"`, meaning the agent is currently turned off.
            RuntimeError: If `self._status` is `"RESTART"`, indicating the agent is in the process
                          of restarting.
        """
        if not self.is_configured:
            raise RuntimeError("The agent has not been configured yet. Please call `configure()` first.")
        if self._graph is None:
            raise RuntimeError("The agent graph has not been initialized yet. Please call `build_graph()` first.")
        if self._status == "OFF":
            raise RuntimeError("The agent is turned off.")
        if self._status == "RESTART":
            raise RuntimeError("The agent is restarting.")

    async def _query_or_respond(self, state: State):
        lang = self._configurer.config.language
        attachment = state["attachment"]
        image_recognizer_configurer = self._configurer.image_recognizer_configurer
        system_msgs: list[SystemMessage] = [
            SystemMessage(content=f'You must answer in {SUPPORTED_LANGUAGE_DICT[lang]}.'),
            SystemMessage(content=f'Queries for using tools purpose must be in {SUPPORTED_LANGUAGE_DICT[lang]}.'),
        ]

        if attachment is not None and (image_recognizer_configurer is None
                                       or image_recognizer_configurer.tool is None):
            self._logger.warning('Image recognizer has not been configured yet. Skipping attachment recognition.')
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                HumanMessage(content="You must only say the following sentence: I cannot recognize the attachment. "
                                     "Because I have not been configured the image recognizer yet."),
            ])
        elif attachment is not None:
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                SystemMessage(content=self._configurer.config.prompt.respond_prompt),
                MessagesPlaceholder(variable_name="messages"),
                HumanMessage(content=ATTACHMENT_INSTRUCTION.format(attachment=str(attachment))),
            ])
        elif isinstance(state["messages"][-1], ToolMessage):
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                MessagesPlaceholder(variable_name="messages"),
                SystemMessage(content="You should not repeat the received recognition result, "
                                      "you just need to extract related information to doing your tasks."),
                HumanMessage(content="Tell me what you think about the attachment "
                                     "based on the received recognition result "
                                     "and the provided questions."),
            ])
        else:
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                SystemMessage(content=self._configurer.config.prompt.respond_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ])

        # Create a prompt
        prompt = await prompt_template.ainvoke({"messages": state["messages"]})
        self._logger.debug(f'Constructed prompt:\n{prompt}\n')

        response = await self._configurer.chat_model.ainvoke(prompt)
        self._logger.debug(f"Response: {response}")

        return {"messages": [response]}

    async def _suggest_questions(self, state: State):
        lang = self._configurer.config.language
        attachment = state["attachment"]
        image_recognizer_configurer = self._configurer.image_recognizer_configurer
        system_msgs: list[SystemMessage] = [
            SystemMessage(content=f'You must answer in {SUPPORTED_LANGUAGE_DICT[lang]}.'),
            SystemMessage(content=f'Queries for using tools purpose must be in {SUPPORTED_LANGUAGE_DICT[lang]}.'),
        ]

        if attachment is None:
            self._logger.warning('Attachment has not been provided yet. Skipping attachment recognition.')
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                HumanMessage(content="You must only say the following sentence:"
                                     "An error occurred while processing the attachment."),
            ])
        elif image_recognizer_configurer is None or image_recognizer_configurer.tool is None:
            self._logger.warning('Image recognizer has not been configured yet. Skipping attachment recognition.')
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                HumanMessage(content="You must only say the following sentence: I cannot recognize the attachment. "
                                     "Because I have not been configured the image recognizer yet."),
            ])
        elif isinstance(state["messages"][-1], ToolMessage):
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                MessagesPlaceholder(variable_name="messages"),
                SystemMessage(content="You should not repeat the received recognition result, "
                                      "you just need to extract related information to doing your tasks."),
                HumanMessage(content="Based on the received recognition result, you must do the following things:\n"
                                     "1. Tell me what you think about the attachment.\n"
                                     "2. Suggest some questions about the attachment."),
            ])
        else:
            prompt_template = ChatPromptTemplate.from_messages([
                *system_msgs,
                SystemMessage(content=self._configurer.config.prompt.suggest_questions_prompt),
                MessagesPlaceholder(variable_name="messages"),
                HumanMessage(content=ATTACHMENT_INSTRUCTION.format(attachment=str(attachment))),
            ])

        # Create a prompt
        prompt = await prompt_template.ainvoke({"messages": state["messages"]})
        self._logger.debug(f'Constructed prompt:\n{prompt}\n')

        response = await self._configurer.chat_model.ainvoke(prompt)
        self._logger.debug(f"Response: {response}")

        return {"messages": [response]}

    @property
    def configurer(self):
        return self._configurer

    @property
    def status(self) -> AgentStatus:
        bm25_configurer = self._configurer.bm25_configurer
        bm25_last_sync = bm25_configurer.last_sync if bm25_configurer is not None else None

        vs_configurer = self._configurer.vector_store_configurer
        if vs_configurer is None:
            available_vector_stores = []
        else:
            all_store_configs = vs_configurer.get_all_configs()
            available_vector_stores = [config.name for config in all_store_configs]

        return AgentStatus(status=self._status,
                           bm25_last_sync=bm25_last_sync,
                           available_vector_stores=available_vector_stores)

    @status.setter
    def status(self, value: Literal["ON", "OFF"]):
        self._status = value

    @property
    def is_configured(self):
        return self._is_configured

    @property
    def graph(self):
        return self._graph
