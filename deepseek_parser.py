import json
import os
import requests
from typing import Dict, Optional
from datetime import datetime

class DeepSeekCalendarParser:
    def __init__(self, api_key: str = None):
        """
        Initialize DeepSeek parser for calendar commands

        Args:
            api_key: DeepSeek API key. If None, will look for DEEPSEEK_API_KEY environment variable
        """
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable or pass api_key parameter")

        self.api_url = "https://api.deepseek.com/v1/chat/completions"

        # System prompt for calendar parsing
        self.system_prompt = """你是一个专业的日历助理，专门解析用户对日历事件的指令。

请将用户的自然语言指令解析为结构化的JSON格式，包含以下字段：
- intent: 操作意图 (create, read, update, delete)
- title: 事件标题
- start_time: 开始时间 (ISO格式: YYYY-MM-DDTHH:MM:SS)
- end_time: 结束时间 (ISO格式: YYYY-MM-DDTHH:MM:SS)
- description: 事件描述
- location: 事件地点
- target_event: 目标事件ID (用于更新/删除)

时间解析规则：
- 使用当前时间作为参考：{current_time}
- "今天" = 当前日期
- "明天" = 当前日期 + 1天
- "下周" = 当前日期 + 7天
- 如果没有指定时间，默认为当前时间+1小时开始，持续1小时

意图识别：
- create: 创建、添加、安排、预定、新建
- read: 查看、显示、列出、检查、看看
- update: 更新、修改、改变、调整、重新安排
- delete: 删除、取消、移除

请确保时间格式正确，如果用户没有提供完整的时间信息，请合理推断。

返回格式必须是纯JSON，不要有其他文本。"""

    def parse_command(self, user_input: str) -> Dict:
        """
        Parse natural language command using DeepSeek API

        Args:
            user_input: User's natural language command

        Returns:
            Parsed command as dictionary
        """
        current_time = datetime.now().isoformat()
        system_prompt = self.system_prompt.format(current_time=current_time)

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                "temperature": 0.1,
                "max_tokens": 500,
                "stream": False
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Try to find JSON in the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed_data = json.loads(json_str)

                # Convert string dates to datetime objects
                if parsed_data.get('start_time'):
                    parsed_data['start_time'] = datetime.fromisoformat(parsed_data['start_time'])
                if parsed_data.get('end_time'):
                    parsed_data['end_time'] = datetime.fromisoformat(parsed_data['end_time'])

                return parsed_data
            else:
                # Fallback: return basic structure
                return {
                    'intent': None,
                    'title': None,
                    'start_time': None,
                    'end_time': None,
                    'description': None,
                    'location': None,
                    'target_event': None
                }

        except Exception as e:
            print(f"DeepSeek API error: {e}")
            # Return empty structure on error
            return {
                'intent': None,
                'title': None,
                'start_time': None,
                'end_time': None,
                'description': None,
                'location': None,
                'target_event': None
            }

# Test function
def test_deepseek_parsing():
    """Test DeepSeek parsing with example commands"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("请设置 DEEPSEEK_API_KEY 环境变量")
        return

    parser = DeepSeekCalendarParser(api_key)

    test_commands = [
        "创建明天下午3点和张三的会议",
        "查看今天的日程",
        "添加今天下午2点的团队讨论，地点在会议室A",
        "删除和张三的会议",
        "更新明天上午10点的会议时间到11点",
        "create a meeting with John tomorrow at 3pm",
        "show my schedule for today",
        "add team discussion today at 2pm in conference room A",
        "delete the meeting with John",
        "update tomorrow's 10am meeting to 11am"
    ]

    print("🧪 Testing DeepSeek Parser")
    print("=" * 50)

    for cmd in test_commands:
        print(f"\n📝 Input: {cmd}")
        result = parser.parse_command(cmd)
        print(f"🎯 Intent: {result.get('intent', 'None')}")
        print(f"📋 Details:")
        for key, value in result.items():
            if key not in ['intent'] and value:
                print(f"   - {key}: {value}")

if __name__ == "__main__":
    test_deepseek_parsing()