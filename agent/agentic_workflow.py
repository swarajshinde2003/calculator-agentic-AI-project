from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from tools.model_loader import ModelLoader
from prompt_library.prompt import SYSTEM_PROMPT
from tools.addition_tool import add_numbers
from tools.mul_tool import multiply_numbers
from tools.sub_tool import subtract_numbers


class GraphBuilder:
    def __init__(self):
        self.model_loader = ModelLoader()
        self.llm = self.model_loader.load_llm()

        self.tools = [
            multiply_numbers,
            add_numbers,
            subtract_numbers
        ]

        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.system_prompt = SYSTEM_PROMPT

    def agent_node(self, state: MessagesState):
        messages = [self.system_prompt] + state["messages"]
        response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def build(self):
        graph = StateGraph(MessagesState)

        graph.add_node("agent", self.agent_node)
        graph.add_node("tools", ToolNode(self.tools))

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
        graph.add_edge("agent", END)

        return graph.compile()   # ✅ FIXED
