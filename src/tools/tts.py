"""TTS 文本转语音 —— 使用系统 espeak 或 gTTS"""

import os
import tempfile


def speak(text: str) -> str:
    """将文本转为语音并播放

    Args:
        text: 要朗读的文本
    Returns:
        状态信息
    """
    try:
        import subprocess
        # 1. 尝试 espeak（Linux 原生）
        subprocess.run(["espeak", "-v", "zh", text], capture_output=True, timeout=10)
        return "已朗读（espeak）"
    except FileNotFoundError:
        pass
    except Exception:
        pass

    try:
        # 2. 尝试 gTTS
        from gtts import gTTS
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tts = gTTS(text=text, lang="zh")
            tts.save(f.name)
            os.system(f"xdg-open {f.name} 2>/dev/null || mpg123 {f.name} 2>/dev/null")
            return f"已生成语音文件: {f.name}"
    except Exception as e:
        return f"TTS 失败：{e}"


# 自注册
from src.tools.registry import register
from src.core.tool import Tool
register(Tool(name="speak", description="文本转语音（espeak/gTTS）", parameters={"type": "object", "properties": {"text": {"type": "string", "description": "要朗读的文本"}}, "required": ["text"]}, function=speak))
