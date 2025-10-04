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
            api_key: DeepSeek API key. If None, will load from config.json
        """
        if api_key:
            self.api_key = api_key
        else:
            # Load from config.json
            config = self._load_config()
            self.api_key = config['deepseek']['api_key']

        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set deepseek.api_key in config.json or pass api_key parameter")

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
- 基于人类作息习惯合理判断"今天"和"明天"的含义
- 凌晨时段（0-6点）的特殊处理：
  - 如果用户在凌晨说"今天"，通常指的是已经开始的这一天
  - 如果用户在凌晨说"明天"，通常指的是即将到来的白天（即今天白天）
  - 如果用户在凌晨说"后天"，通常指的是24小时后的白天
- 对于查询指令（如"明天有什么事"）：
  - 必须提供准确的start_time和end_time
  - "明天"：start_time = 明天00:00:00，end_time = 明天23:59:59
  - "今天"：start_time = 今天00:00:00，end_time = 今天23:59:59
- "下周" = 当前日期 + 7天
- 对于创建指令，如果没有指定时间，默认为当前时间+1小时开始，持续1小时

意图识别：
- create: 创建、添加、安排、预定、新建
- read: 查看、显示、列出、检查、看看、有什么事、日程安排
- update: 更新、修改、改变、调整、重新安排
- delete: 删除、取消、移除

重要：对于查询类指令（如"明天有什么事"），必须提供准确的时间范围，不能留空。

返回格式必须是纯JSON，不要有其他文本。"""

    def _load_config(self) -> Dict:
        """Load configuration with priority: config_private.json > config.json"""
        # Try config_private.json first (private config)
        private_config_path = 'config_private.json'
        config_path = 'config.json'

        if os.path.exists(private_config_path):
            config_path = private_config_path
            print(f"使用私有配置文件: {config_path}")
        elif os.path.exists(config_path):
            print(f"使用默认配置文件: {config_path}")
        else:
            raise FileNotFoundError(
                f"配置文件不存在，请创建 {private_config_path} 或 {config_path} 并填写配置信息"
            )

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Validate required fields
            if 'deepseek' not in config or 'api_key' not in config['deepseek']:
                raise ValueError("配置文件中缺少 deepseek.api_key 字段")

            if not config['deepseek']['api_key']:
                raise ValueError("配置字段 deepseek.api_key 不能为空")

            return config

        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ValueError(f"读取配置文件失败: {e}")

    def _should_enable_reasoning(self, user_input: str) -> bool:
        """
        Determine whether to enable reasoning mode based on input complexity and time

        Returns:
            True if reasoning mode should be enabled
        """
        from datetime import datetime

        current_hour = datetime.now().hour

        # 凌晨时段 (0-6点) 且包含时间词汇
        if 0 <= current_hour <= 6:
            time_keywords = ['今天', '明天', '后天', '上午', '下午', '晚上', '凌晨', '早晨', '早上']
            if any(keyword in user_input for keyword in time_keywords):
                return True

        # 相对时间表达 (需要推理的)
        relative_time_patterns = [
            '下周', '下个月', '下个星期',
            '这周', '这个月', '这个星期',
            '月底', '月初', '年中', '年底', '年初',
            '工作日', '周末', '节假日', '假期'
        ]

        # 具体日期表达 (不需要推理的)
        specific_date_patterns = [
            '下周一', '下周二', '下周三', '下周四', '下周五', '下周六', '下周日',
            '这周一', '这周二', '这周三', '这周四', '这周五', '这周六', '这周日'
        ]

        # 检查是否有相对时间表达但排除具体日期
        has_relative_time = any(pattern in user_input for pattern in relative_time_patterns)
        has_specific_date = any(pattern in user_input for pattern in specific_date_patterns)

        if has_relative_time and not has_specific_date:
            return True

        # 模糊时间表达
        vague_time_patterns = [
            '最近', '过几天', '几天后', '下周左右', '大概', '大约', '左右', '前后', '差不多'
        ]

        if any(pattern in user_input for pattern in vague_time_patterns):
            return True

        return False

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
        print(f"🧠 Parsing command: {user_input}")

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

            # 只在需要时启用推理模式
            if self._should_enable_reasoning(user_input):
                payload["reasoning_effort"] = "medium"
                print("🔍 启用深度推理模式")  # 调试信息

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            print(f"🧠 API Response: {content}")

            # Try to find JSON in the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                print(f"🧠 Extracted JSON: {json_str}")
                parsed_data = json.loads(json_str)

                # Convert string dates to datetime objects
                if parsed_data.get('start_time'):
                    parsed_data['start_time'] = datetime.fromisoformat(parsed_data['start_time'])
                if parsed_data.get('end_time'):
                    parsed_data['end_time'] = datetime.fromisoformat(parsed_data['end_time'])

                print(f"🧠 Final parsed data: {parsed_data}")
                return parsed_data
            else:
                print(f"❌ No JSON found in response")
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