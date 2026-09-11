from typing import Annotated
import json
from dataclasses import dataclass
from typing import Dict, Callable, Any,List

from langchain_core.tools import StructuredTool

@dataclass
class Tool:
    name: str
    description: str
    handler: Callable
    parameters: dict  = None

class ToolRegistry:
    """工具注册表：维护所有可用工具及其执行函数"""
    
    def __init__(self):
        """
        初始化工具注册表
        每个工具都有一个名称、描述和执行函数。
        {"tool_name": {"description": "工具描述", "func": <function_object>, "parameters": <参数字典>}}
        """
        self.tools: Dict[str, Tool] = {}
    
    def register(self, name: str = None):
        """注册工具

        工具的描述与参数 schema 全部由被装饰函数自身提供：
        - 工具描述：函数 docstring
        - 参数名 / 类型 / 是否必填：函数类型注解
        - 参数说明：Annotated[str, "说明"]
        """
        def decorator(fn):
            tool_name = name or fn.__name__
            # 由函数签名与 docstring 自动生成 langchain StructuredTool（含 bind_tools 需要的 schema）
            tool = StructuredTool.from_function(func=fn, name=tool_name)
            schema = tool.get_input_schema().model_json_schema()
            self.tools[tool_name] = Tool(
                name=tool_name,
                description=tool.description,
                handler=tool,
                parameters=schema.get("properties", {}),
            )
            return fn
        return decorator
    
    def get_tool(self, name: str) -> Callable:
        """获取工具执行函数"""
        if name in self.tools:
            return self.tools[name].handler
        raise ValueError(f"工具 '{name}' 未注册")

    def get_tool_func(self) -> List[Any]:
        """获取工具执行函数"""
        return [tool.handler for tool in self.tools.values()]
    
    def list_tool_definitions(self) -> list:
        """列出所有已注册工具的定义"""
        return [{"name": tool.name, "description": tool.description, "parameters": tool.parameters} for tool in self.tools.values()]
    
    def execute(self, name, args=None):
        """按名称调度工具并调用，结果统一包装，成功失败都返回可反馈的结构。"""
        tool = self.tools.get(name)
        if tool is None:
            return {"tool": name, "success": False, "data": None,
                    "error": f"沙箱内没有注册工具: {name}"}
        args = args or {}
        unknown = set(args) - set(tool.parameters or {})
        if unknown:
            return {"tool": tool.name, "success": False, "data": None,
                    "error": f"工具 {tool.name} 不认识参数: {sorted(unknown)}"}
        try:
            data = tool.handler.invoke(args)
            return {"tool": tool.name, "success": True, "data": data, "error": None}
        except Exception as e:  # 工具运行异常也要吞掉，统一反馈，避免沙箱崩溃
            return {"tool": tool.name, "success": False, "data": None,
                    "error": f"工具 {tool.name} 执行失败: {type(e).__name__}: {e}"}


tool_registry = None

if tool_registry is None:
    tool_registry = ToolRegistry()

if __name__ == "__main__":
    @tool_registry.register()
    def test_tool(b: Annotated[int, "第一个整数参数"], c: Annotated[int, "第二个整数参数"]) -> int:
        """测试工具"""
        return b + c
    
    print(tool_registry.test("test_tool"))
    # print(tool_registry.list_tool_definitions())