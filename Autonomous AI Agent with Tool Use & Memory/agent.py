"""
agent.py
--------
The brain of the project: a LangGraph agent.

A LangGraph "graph" is a small state machine. Here it has two nodes:

    agent  -> the LLM. Looks at the conversation and decides either to
              answer directly OR to call one or more tools.
    tools  -> runs whatever tools the LLM asked for, then sends the
              results back to the agent node.

The conditional edge (tools_condition) is what makes it "multi-step":
    - if the LLM requested tools  -> go to the tools node, then loop back
    - if the LLM gave a final text answer -> stop (END)

So the agent can: think -> search the web -> think -> run code -> think ->
answer, all on its own. That loop is the whole point of an "agent".
"""

import os

from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from tools import ALL_TOOLS

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are an autonomous assistant. Break the user's request into steps "
        "and use the available tools (web search, code execution, file I/O, "
        "math, Wikipedia, etc.) whenever they help you get a correct, "
        "up-to-date answer. Think step by step, call tools as needed, and only "
        "give your final answer once you have everything you need."
    )
)


def build_agent():
    """Build and compile the LangGraph agent."""
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # bind_tools tells the LLM which tools exist and how to call them.
    llm = ChatOpenAI(model=model_name, temperature=0).bind_tools(ALL_TOOLS)

    def call_model(state: MessagesState):
        # Prepend the system prompt to the running conversation, then ask the LLM.
        messages = [SYSTEM_PROMPT] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    # MessagesState automatically appends new messages to state["messages"].
    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "agent")
    # tools_condition returns "tools" if the LLM asked for tools, else END.
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")  # after running tools, think again

    return graph.compile()


# A single compiled agent the rest of the app imports.
agent = build_agent()


if __name__ == "__main__":
    # Quick manual test:  python agent.py "your question here"
    import sys
    from langchain_core.messages import HumanMessage

    question = " ".join(sys.argv[1:]) or "What is the capital of France, and what is 25 * 17?"
    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    print(result["messages"][-1].content)
