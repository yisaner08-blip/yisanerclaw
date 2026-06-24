"""测试记忆模块"""

from src.core.memory import ConversationMemory


def test_basic_memory():
    m = ConversationMemory(max_turns=5)
    m.set_system("test system")
    m.add_message({"role": "user", "content": "hello"})
    msgs = m.to_messages()
    assert len(msgs) == 2  # system + user
    assert msgs[0]["content"] == "test system"

def test_sliding_window():
    m = ConversationMemory(max_turns=1)  # 1 turn = 4 messages
    m.set_system("sys")
    for i in range(10):
        m.add_message({"role": "user", "content": str(i)})
    msgs = m.to_messages()
    # system + last 4 messages
    assert len(msgs) <= 5

def test_reset():
    m = ConversationMemory()
    m.set_system("sys")
    m.add_message({"role": "user", "content": "hello"})
    m.reset()
    msgs = m.to_messages()
    assert len(msgs) == 1  # only system remains

def test_token_cap():
    m = ConversationMemory(max_tokens=20)
    m.set_system("sys")
    m.add_message({"role": "user", "content": "x" * 1000})
    msgs = m.to_messages()
    # 应该会裁剪
    assert len(msgs) <= 2
