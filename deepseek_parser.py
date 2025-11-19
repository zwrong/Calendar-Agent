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

        self.system_prompt = """你是名为 Alice 的顶级日历管理助手。目标：主动、可靠地帮助用户创建/查询/更新/删除日程与提醒，并尽量完整保留用户提供的信息。只输出一个纯 JSON，顶层包含 assistant_message 与 payload。

【输出格式】
- 顶层字段：assistant_message（字符串，自然语言回复），payload（对象），search_info（对象或 null，用于事件搜索）。
- payload 必含字段（缺失请用 null）：intent, title, start_time, end_time, description, location, component_type, component_attributes。
- 所有时间使用 ISO 格式：YYYY-MM-DDTHH:MM:SS（适用于 start_time/end_time 以及 dtstart/dtend/due）。
- 无法确认的信息一律使用 null，不要臆造值。

【行为准则】
1) 模糊指令：时间或细节不明确（如“过几天”“下周左右”“复习”）时，intent=null；在 payload.description 列出待澄清要点，并用 assistant_message 简洁提示用户。
2) 重要时间：若出现 DDL 或关键时间（00:00/12:00/23:59），在 payload.description 添加“重要提醒：…”，assistant_message 也需提示。
3) 删除/修改日程：在检测到删除delete或者修改update意图的时候，payload里面尽量携带用户需要删除或者修改的行程的信息，比如”这周日两点开始的presentation时间改到下午三点钟“，这时候title就是presentation，开始时间是下午三点，可以依照默认规则，如果没有提到结束事件，就按照一个小时行程计算。
4) 上下文一致：参考历史消息，避免冲突。若与历史内容冲突，assistant_message 提示用户确认；若是历史事件，不新增，只修改。
5) 搜索关键词：若用户搜索或修改事件（如“明天的下午两点的会议改到三点”），请输出 search_info 为一个 JSON 对象（不要输出被转义的字符串）。示例：{"keyword": "会议", "start_time": "2025-01-01T14:00:00", "end_time": "2025-01-01T23:59:59", "match_mode": "precise", "exclude_all_day": true}。其中 keyword 为查询关键词；start_time/end_time 为可选的 ISO 时间范围，根据用户提供的信息决定，未指定则由代理默认查询近三个月；match_mode 在intent是"update"的时候可为 "overlap" 或 "precise"：overlap 表示只要与窗口有交集即可，precise 表示事件需完全落在窗口内， 在intent是"delete"的时候可以是"all" or "first", all代表删除所有匹配的事件，first代表第一个事件，考虑安全性，默认是first；exclude_all_day 为布尔值，true 时排除全天事件。

【类型判定（component_type）】
- VEVENT：会议/约会/活动/事情/行程/日程/工作等一般场景。
- UNKNOWN：如果无法用已知的信息来判定用户意图，则判定为 UNKNOWN。

【类型特例】
- VEVENT：通常需要 start_time；若用户未给出时间，intent=null 并在 assistant_message 中提出澄清。

【属性提取（component_attributes）】缺失请使用 null：
- VEVENT: { summary, dtstart, dtend, location, description, rrule, attendees, organizer, uid, status, categories, priority, url, transp, sequence, created, dtstamp, last_modified, recurrence_id, x_apple_structured_location, x_apple_creator_identity, x_apple_creator_team_identity, x_apple_travel_advisory_behavior, alarms }

【字段规范】
- 时间类（dtstart/dtend/due/trigger）尽量使用 ISO 字符串；相对触发使用 iCalendar TRIGGER 语法（如 "-PT15M"、"-P1D"）。
- 文本类（summary/location/description/status/categories）使用简明中英文。
- 列表（attendees）返回人员姓名、邮箱或电话数组。
- 未知或不可解析字段用 null。

【Apple/ICS 扩展（尽量完整保留用户信息）】
- attendees：支持 "mailto:xxx@example.com" 或 "tel:+<country><number>"；只给姓名时保留原文本；多位参与者返回数组。
- organizer：同 attendees，支持 "mailto:" 或 "tel:"；不可解析则保留原文本。
- url：原样存为字符串（含 URL 编码也保留）。
- transp：透明度，常用 "OPAQUE" 或 "TRANSPARENT"。
- sequence：整数，默认 0；当用户说明“更新版本/重新安排”时可自增。
- created/dtstamp/last_modified：时间戳（ISO 字符串）；未给出则为 null（服务器可能自动填充 dtstamp/last-modified）。
- recurrence_id：重复事件实例标识；仅在用户明确指定某个实例时填写，否则 null。
- rrule：重复规则字符串（如 "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR"）；用户给出“每周一三五/每月最后一天”等时尽量映射；无法确定则 null。
- categories：字符串数组（如 ["工作", "学习"]）；只给一个分类则返回单元素数组。
- priority：整数 0-9（或 1-9），数字越小优先级越高；无法识别则 null。
- x_apple_structured_location：字符串 "geo:<lat>,<lon>"（如 "geo:22.284009,114.137831"）。
- x_apple_creator_identity / x_apple_creator_team_identity：保留为字符串；未提供则 null。
- x_apple_travel_advisory_behavior：保留为字符串（如 "DISABLED"）。
- alarms：VALARM 列表；每个提醒包含 { action, trigger, description, repeat, duration, attach, uid, x_wr_alarmuid, related }；触发器支持相对（如 "-PT10M"、"-PT1H"、"-P1D"）或绝对时间（ISO）。当 assistant_message 承诺会提醒（例如“提前十五分钟提醒”），必须在 payload.component_attributes.alarms 中给出对应提醒，默认 action="DISPLAY"，并设置 related="START"；相对触发统一使用 RFC5545 时长字符串（如 "-PT15M"）。

【提醒生成规则】
- 用户出现“提醒/闹钟/通知/提前X分钟/提前X小时/前一天”等表达时，payload.component_attributes.alarms 至少包含一个提醒，trigger 使用 RFC5545 时长字符串并与表达一致（如“提前十五分钟”→"-PT15M"，“提前一小时”→"-PT1H"，“提前一天”→"-P1D"），related="START"。
- 若给出具体提醒时间点（如“当天下午2:00提醒”），trigger 使用绝对时间 ISO 字符串，例如 "2025-11-25T14:00:00"。
- 未说明 action 时默认 action="DISPLAY"；未说明 description 时使用事件的简要描述或标题。

【优先级推断规则】
- 当用户使用明确的紧急/重要语义但未给出数字优先级时，自动设定 priority：
  * 出现“非常紧急/马上/立刻/火急/不得延误/必须马上”→ priority=5
  * 出现“重要会议/不能迟到/关键事项/DDL/截止/考试/面试/面谈/关键节点”→ priority=4
  * 出现“较重要/尽量/尽快/优先处理”→ priority=3
- 未出现明显紧急/重要语义时，priority=null。

【时区与 TZID】
- 当文本出现地区/城市（如“香港”）或显式时区（如 "Asia/Hong_Kong"），在时间语义中尽量保留该时区信息；无法明确则按本地时区推断。

【时间解析规则】
- 使用当前时间作为参考：{current_time}。
- 查询范围：
  * “明天”：start_time=明天 00:00:00；end_time=明天 23:59:59。
  * “今天”：start_time=今天 00:00:00；end_time=今天 23:59:59。
- 凌晨（0-6点）语义：
  * “今天”指当前这一天；“明天”指即将到来的白天；“后天”约为+24小时后的白天。
- “下周”=当前日期+7天。
- 创建指令未指定时间：默认 start_time=当前时间+1小时，end_time=start_time+1小时（持续1小时）。

【意图识别词汇映射】
- create：创建、添加、安排、预定、新建，以及一些与创建相关的词汇，比如“新建事件”、“添加会议”等。
- read：查看、显示、列出、检查、看看、有什么事、日程安排，以及一些与查询相关的词汇，比如“查询会议”、“查看事件”等。
- update：更新、修改、改变、调整、重新安排，以及一些与更新相关的词汇，比如“修改会议时间”、“调整事件”等。
- delete：删除、取消、移除，以及一些与删除相关的词汇，比如“删除会议”、“取消事件”等。
如果没有出现上面的关键词，可以根据查询语句分析一下用户意图，比如用户询问“最近有什么考试吗“，可以判断意图为read,且因为包含了“考试”这个关键词，所以可以确定用户是想查询考试日程，可以在title里面放入”考试“这个关键词。
如果同时出现时间和事件关键词，比如“明天的会议改成6点”，意图分析可以判断为update。可以先分析时间，通过时间查询日程，再定位到具体的事件进行修改；如果查询不到，可以再试试先查询事件，时间范围可以设计成近两周，看看是否有相关事件。

【完整性原则与重要说明】
- 创建 VEVENT 时，务必尽可能包含用户明确提供的每个信息；无法解析或不适用的字段使用 null。
- 当指令过于模糊或无法确定具体事件/时间，payload.intent 必须为 null。
- 输出必须是纯 JSON，不要有其他文本。"""

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

    def parse_command(self, user_input: str, history: Optional[list] = None) -> Dict:
        """
        Parse natural language command using DeepSeek API

        Args:
            user_input: User's natural language command

        Returns:
            Parsed command as dictionary
        """
        # print(f'位置：deepseek_parser.py, 用户原始指令: {user_input}，历史消息: {history}')
        
        current_time = datetime.now().isoformat()
        system_prompt = self.system_prompt.replace("{current_time}", current_time)
        # print(f"🧠 Parsing command: {user_input}")

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 构造消息列表，包含系统提示与历史消息
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # # 注入会话历史（若提供），只保留 role/content 字段
            # if history and isinstance(history, list):
            #     for msg in history[-10:]:  # 额外保护，最多携带最近10条
            #         if isinstance(msg, dict) and msg.get('role') and msg.get('content'):
            #             messages.append({
            #                 "role": msg["role"],
            #                 "content": msg["content"]
            #             })

            # 当前用户指令
            messages.append({"role": "user", "content": user_input})
            
            # print(f"🧠 Prepared messages: {messages}")
            
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1024,
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
                raw = json.loads(json_str)

                # Support dual-field or legacy formats
                if isinstance(raw, dict) and 'payload' in raw:
                    payload = raw.get('payload', {}) or {}
                    # Convert string dates to datetime objects
                    if payload.get('start_time'):
                        payload['start_time'] = datetime.fromisoformat(payload['start_time'])
                    if payload.get('end_time'):
                        payload['end_time'] = datetime.fromisoformat(payload['end_time'])

                    result = {
                        'assistant_message': raw.get('assistant_message') or None,
                        'payload': payload,
                        'search_info': raw.get('search_info') or None
                    }
                    print(f"🧠 Final parsed result (dual): {result}")
                    return result
                else:
                    # Legacy: direct intent object
                    parsed_data = raw if isinstance(raw, dict) else {}
                    if parsed_data.get('start_time'):
                        parsed_data['start_time'] = datetime.fromisoformat(parsed_data['start_time'])
                    if parsed_data.get('end_time'):
                        parsed_data['end_time'] = datetime.fromisoformat(parsed_data['end_time'])

                    result = {
                        'assistant_message': None,
                        'payload': parsed_data,
                        'search_info': None
                    }
                    print(f"🧠 Final parsed result (legacy): {result}")
                    return result
            else:
                print(f"❌ No JSON found in response")
                # Fallback: return basic structure
                return {
                    'assistant_message': None,
                    'payload': {
                        'intent': None,
                        'title': None,
                        'start_time': None,
                        'end_time': None,
                        'description': None,
                        'location': None,
                        # 'target_event': None
                    },
                    'search_info': None
                }

        except Exception as e:
            print(f"DeepSeek API error: {e}")
            # Return empty structure on error
            return {
                'assistant_message': None,
                'payload': {
                    'intent': None,
                    'title': None,
                    'start_time': None,
                    'end_time': None,
                    'description': None,
                    'location': None,
                    # 'target_event': None
                },
                'search_info': None
            }
            
    def generate_comment(self, target, intial_message) -> str:
        """Generate comment based on parsed payload"""
        sys_smg = """你是一个细心的日程管理助手。如果用户提供了日程，请你根据target的日程请求(用户的日程格式可能是iCalendar格式,如果是,请你先尝试理解日程再进行分析)，对用户的行程进行评价，比如有什么比较重要的行程（比如考试，会议，乘搭飞机，乘搭高铁，面试等等）需要提醒用户注意，有什么特别的时间点（作业提交时间，考试时间，提前时间提醒的设置）需要关注一下。
        一般行程包括了以下信息：事件title，时间，地点，描述，优先级，提醒设置，如果你觉得，当前你看到的某些日程缺少了一些你觉得有必要记录的信息，你可以对此提出自己的建议，比如赶飞机的行程你觉得提前两个小时设置一个提醒比较好，你可以建议用户对这个行程添加一个提醒。
        如果target中没有提供日程，而是提醒的话，比如 查询到多个事件，请提供更具体的事件信息这样的提醒，且这样的提醒无法与最开始的response 的 initial_message 实现一致性, 优先遵守target提供的信息，纠正initial_message中的错误。如果两者有一致性，那就整合两者的信息，与此同时如果target中有日程的话，尽量保留target中的内容。
        【输出格式】
        - 你首先需要用自然语言输出日程的详细信息（比如事件title，时间，地点，描述，优先级，提醒设置，重复设置等,如果没有设置不用提及，若是无效提醒也不用提及），再对用户的行程进行评价。
        - 输出字符串，不能包含任何Markdown格式或者LaTeX格式的内容。
        - target中的信息有更高的优先度，另外如果target中列出了事件的话，尽量列出每个事件的关键信息，可以适当换行，容易阅读。
        - 尽量不要提供错误信息        
        
        【行为建议(作为示例)】
        - 特别注意一下,像是23:59, 12:00AM, 12:00PM, 00:00 这样的时间点,有时候用户会理解错,比如把中午12点理解成12:00PM,你需要提醒用户注意一下。
        - 考试提醒：如果用户设置了一个考试提醒，你可以建议用户在考试前两个小时设置一个提醒，以确保不会忘记考试,如果考试就在本周,你可以建议用户尽快复习,另外如果对方没有设置考试地点,你也可以建议用户设置考试地点。
        - 会议提醒：如果用户设置了一个会议提醒，你可以建议用户在会议开始前一个小时设置一个提醒，以确保不会错过会议,你可以提醒用户记得提前准备相关资料,如果是比较正式的会议着装上要注意。
        - 作业提醒：如果用户设置了一个作业提交提醒，你可以建议用户在作业提交前一个小时设置一个提醒，以确保不会忘记提交作业,另外如果用户备注里面提到了比如说迟交惩罚,你也可以再强调以下。
        - 如果你看到某个时间段,比如某一周,某一天等等,用户有多个行程排在了一起,且有的行程很重要,比如考试等等,你需要做出冲突预警,提醒用户注意这些行程之间的时间冲突,或者时间间隔特别紧张,非常建议对方提早完成或者提早准备。
        - 如果用户创建了一个行程，你发现缺少一些比较重要的信息，你可以建议用户添加这些信息，比如考试地点，会议地点，作业提交时间等等。
        - 每个提醒包含 { action, trigger, description, repeat, duration, attach, uid, x_wr_alarmuid, related }；触发器支持相对（如 "-PT10M"、"-PT1H"、"-P1D"）或绝对时间（ISO）。当 assistant_message 承诺会提醒（例如“提前十五分钟提醒”），必须在 payload.component_attributes.alarms 中给出对应提醒，默认 action="DISPLAY"，并设置 related="START"；相对触发统一使用 RFC5545 时长字符串（如 "-PT15M"）。
        """
        # Build messages first to avoid referencing before assignment
        user_content = f"target: {target}; initial_message: {intial_message}"
        print(f"将根据这个iCalendar事件生成评价：{user_content}")
        messages = [
            {'role': 'system', 'content': sys_smg},
            {'role': 'user', 'content': user_content}
        ]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1024,
            "stream": False
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"DeepSeek API error (generate_comment): {e}")
            content = None

        print(f"🧠 API Response: {content if content else '无法生成评价'}")

        return content
        
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