import pytest

from src.agent import main

pytestmark = pytest.mark.anyio


@pytest.mark.langsmith
async def test_agent_simple_passthrough() -> None:
    inputs = {"changeme": "some_val"}
    res = await main.ainvoke(inputs)
    assert res is not None
