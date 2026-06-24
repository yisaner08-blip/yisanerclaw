"""测试计算器工具"""

from src.tools.calculator import calculator


def test_basic_ops():
    """测试基本运算"""
    assert "5" in calculator("2+3")
    assert "6" in calculator("2*3")
    assert "10" in calculator("100/10")

def test_math_funcs():
    """测试数学函数"""
    assert "4" in calculator("math.sqrt(16)")
    assert "1" in calculator("math.sin(math.pi/2)")[:4]

def test_errors():
    """测试错误输入"""
    assert "错误" in calculator("import os")
    assert "错误" in calculator("__import__('os')")

def test_complex():
    """测试复杂表达式"""
    result = calculator("2**10")
    assert "1024" in result
