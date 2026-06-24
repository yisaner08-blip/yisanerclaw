"""测试工具系统和注册表"""

# 导入工具模块触发自注册
import src.tools.calculator  # noqa: F401
import src.tools.file_ops    # noqa: F401
import src.tools.web_search  # noqa: F401
import src.tools.shell       # noqa: F401
import src.tools.system_info # noqa: F401
from src.tools.registry import get_registry


def test_registry_has_tools():
    registry = get_registry()
    tools = registry.list_all()
    tool_names = [t.name for t in tools]
    assert "calculator" in tool_names
    assert "run_shell" in tool_names
    assert "web_search" in tool_names
    assert "get_current_time" in tool_names
    assert "get_environment" in tool_names

def test_registry_lookup():
    registry = get_registry()
    tool = registry.get("calculator")
    assert tool is not None
    assert tool.name == "calculator"

def test_registry_missing():
    registry = get_registry()
    tool = registry.get("nonexistent")
    assert tool is None

def test_execute_valid():
    registry = get_registry()
    result = registry.execute("calculator", {"expression": "2+2"})
    assert "4" in result

def test_execute_invalid():
    registry = get_registry()
    result = registry.execute("nonexistent", {})
    assert "错误" in result

def test_openai_format():
    registry = get_registry()
    fmt = registry.to_openai_format()
    assert len(fmt) >= 5
    assert fmt[0]["type"] == "function"
    assert "name" in fmt[0]["function"]
