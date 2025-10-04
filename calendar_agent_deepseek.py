import os
import json
from typing import Dict, List, Optional
from datetime import datetime

from caldav_client import AppleCalendarClient
from deepseek_parser import DeepSeekCalendarParser

class CalendarAgentDeepSeek:
    def __init__(self):
        """Initialize the calendar agent with DeepSeek NLP and CalDAV client"""
        # Initialize DeepSeek parser
        self.nlp_parser = DeepSeekCalendarParser()

        # Get credentials from config.json
        config = self._load_config()

        server_url = config['caldav']['server_url']
        username = config['caldav']['username']
        password = config['caldav']['password']

        if not username or not password:
            raise ValueError("请在 config.json 文件中设置 caldav.username 和 caldav.password")

        try:
            self.calendar_client = AppleCalendarClient(server_url, username, password)
            print("✓ 日历客户端初始化成功")
        except Exception as e:
            print(f"❌ 日历客户端初始化失败: {e}")
            raise ValueError(f"日历代理初始化失败: {e}")

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
            required_fields = [
                'caldav.username',
                'caldav.password',
                'deepseek.api_key'
            ]

            for field in required_fields:
                keys = field.split('.')
                current = config
                for key in keys:
                    if key not in current:
                        raise ValueError(f"配置文件中缺少必要字段: {field}")
                    current = current[key]
                if not current:
                    raise ValueError(f"配置字段 {field} 不能为空")

            return config

        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ValueError(f"读取配置文件失败: {e}")

    def process_command(self, user_input: str, selected_calendar: str = None) -> str:
        """
        Process natural language command using DeepSeek and execute calendar operation

        Args:
            user_input: Natural language command from user

        Returns:
            Response message to user
        """
        try:
            print(f"🔍 Processing command: {user_input}")
            # Parse user intent and extract details using DeepSeek
            parsed_intent = self.nlp_parser.parse_command(user_input)
            print(f"🔍 Parsed intent: {parsed_intent}")

            if not parsed_intent.get('intent'):
                print(f"❌ No intent detected for: {user_input}")
                return "抱歉，我没有理解您的指令。请尝试使用更清晰的表达，比如：'创建明天下午3点的会议' 或 '查看今天的日程'"

            intent = parsed_intent['intent']

            if intent == 'create':
                return self._handle_create_event(parsed_intent, selected_calendar)
            elif intent == 'read':
                return self._handle_read_events(parsed_intent, selected_calendar)
            elif intent == 'update':
                return self._handle_update_event(parsed_intent, selected_calendar)
            elif intent == 'delete':
                return self._handle_delete_event(parsed_intent, selected_calendar)
            else:
                return f"暂不支持的操作: {intent}"

        except Exception as e:
            return f"处理指令时出现错误: {str(e)}"

    def _handle_create_event(self, parsed_intent: Dict, selected_calendar: str = None) -> str:
        """Handle event creation"""
        # Validate required fields
        if not parsed_intent.get('title'):
            return "请提供事件的标题，例如：'创建和张三的会议'"

        if not parsed_intent.get('start_time'):
            return "请提供事件的时间，例如：'明天下午3点'"

        # Set default end time if not provided
        from datetime import datetime

        # Handle both string and datetime objects
        start_time = parsed_intent['start_time']
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        if parsed_intent.get('end_time'):
            end_time = parsed_intent['end_time']
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)
        else:
            # Default: 1 hour duration
            end_time = start_time.replace(hour=start_time.hour + 1)

        # Create the event
        event_id = self.calendar_client.create_event(
            title=parsed_intent['title'],
            start_time=start_time,
            end_time=end_time,
            description=parsed_intent.get('description', ''),
            location=parsed_intent.get('location', ''),
            calendar_name=selected_calendar if selected_calendar is not None else None
        )

        return f"✅ 已成功创建事件: {parsed_intent['title']}\n" \
               f"📅 时间: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}\n" \
               f"📍 地点: {parsed_intent.get('location', '未指定')}\n" \
               f"📝 描述: {parsed_intent.get('description', '无')}"

    def _handle_read_events(self, parsed_intent: Dict, selected_calendar: str = None) -> str:
        """Handle event reading/listing"""
        print(f"🔍 Reading events with parsed intent: {parsed_intent}")

        # Determine time range for search
        if parsed_intent.get('start_time'):
            start_date = parsed_intent['start_time']
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)

            # Use provided end_time if available, otherwise default to end of day
            if parsed_intent.get('end_time'):
                end_date = parsed_intent['end_time']
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date)
            else:
                end_date = start_date.replace(hour=23, minute=59, second=59)
        else:
            # Default to today
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date.replace(hour=23, minute=59, second=59)

        print(f"🔍 Querying events from {start_date} to {end_date}")

        # If searching for specific event
        if parsed_intent.get('title'):
            events = self.calendar_client.search_events(
                parsed_intent['title'],
                calendar_name=selected_calendar if selected_calendar is not None else None
            )
        else:
            events = self.calendar_client.get_events(
                start_date=start_date,
                end_date=end_date,
                calendar_name=selected_calendar if selected_calendar is not None else None
            )

        if not events:
            # Determine which day we're querying for the message
            query_date = start_date.date()
            today = datetime.now().date()

            if query_date == today:
                return "📅 今天没有安排任何事件"
            elif query_date == today.replace(day=today.day + 1):
                return "📅 明天没有安排任何事件"
            else:
                return f"📅 {query_date.strftime('%Y年%m月%d日')} 没有安排任何事件"

        response = "📅 您的日程安排:\n\n"
        for i, event in enumerate(events, 1):
            start_str = event['start'].strftime('%H:%M') if event['start'] else '未知时间'
            end_str = event['end'].strftime('%H:%M') if event['end'] else '未知时间'

            response += f"{i}. {event['title']}\n"
            response += f"   时间: {start_str} - {end_str}\n"
            if event.get('location'):
                response += f"   地点: {event['location']}\n"
            if event.get('description'):
                response += f"   描述: {event['description']}\n"
            response += "\n"

        return response.strip()

    def _handle_update_event(self, parsed_intent: Dict, selected_calendar: str = None) -> str:
        """Handle event updates"""
        if not parsed_intent.get('target_event'):
            # Try to find event by title
            if parsed_intent.get('title'):
                events = self.calendar_client.search_events(parsed_intent['title'])
                if events:
                    parsed_intent['target_event'] = events[0]['id']
                else:
                    return "找不到指定的事件，请提供更具体的信息"
            else:
                return "请指定要更新的事件，例如：'修改和张三的会议时间'"

        # Update the event
        success = self.calendar_client.update_event(
            event_id=parsed_intent['target_event'],
            title=parsed_intent.get('title'),
            start_time=parsed_intent.get('start_time'),
            end_time=parsed_intent.get('end_time'),
            description=parsed_intent.get('description'),
            location=parsed_intent.get('location'),
            calendar_name=selected_calendar if selected_calendar is not None else None
        )

        if success:
            return "✅ 事件已成功更新"
        else:
            return "❌ 更新事件失败，请检查事件ID是否正确"

    def _handle_delete_event(self, parsed_intent: Dict, selected_calendar: str = None) -> str:
        """Handle event deletion"""
        print(f"尝试删除事件: {parsed_intent.get('target_event')}")

        # Handle "all" target_event (delete all matching events)
        if parsed_intent.get('target_event') == 'all':
            if parsed_intent.get('title'):
                # Delete all events with matching title
                events = self.calendar_client.search_events(
                    parsed_intent['title'],
                    calendar_name=selected_calendar if selected_calendar is not None else None
                )
                if events:
                    deleted_count = 0
                    for event in events:
                        print(f"找到事件，开始删除: {event['id']}")
                        if self.calendar_client.delete_event(
                            event['id'],
                            calendar_name=selected_calendar if selected_calendar is not None else None
                        ):
                            deleted_count += 1

                    if deleted_count > 0:
                        return f"✅ 已成功删除 {deleted_count} 个事件"
                    else:
                        return "❌ 删除事件失败"
                else:
                    return "找不到指定的事件"
            else:
                return "请指定要删除的事件标题，例如：'删除所有会议'"

        # Handle specific event deletion
        if not parsed_intent.get('target_event'):
            # Try to find event by title
            if parsed_intent.get('title'):
                events = self.calendar_client.search_events(
                    parsed_intent['title'],
                    calendar_name=selected_calendar if selected_calendar is not None else None
                )
                if events:
                    print(f"找到事件: {events}")
                    deleted_count = 0
                    for event in events:
                        print(f"找到事件，开始删除: {event['id']}")
                        if self.calendar_client.delete_event(
                            event['id'],
                            calendar_name=selected_calendar if selected_calendar is not None else None
                        ):
                            deleted_count += 1

                    if deleted_count > 0:
                        return f"✅ 已成功删除 {deleted_count} 个事件"
                    else:
                        return "❌ 删除事件失败"
                else:
                    return "找不到指定的事件，请提供更具体的信息"
            else:
                return "请指定要删除的事件，例如：'删除和张三的会议'"

        # Delete specific event by ID
        success = self.calendar_client.delete_event(
            parsed_intent['target_event'],
            calendar_name=selected_calendar if selected_calendar is not None else None
        )

        if success:
            return "✅ 事件已成功删除"
        else:
            return "❌ 删除事件失败，请检查事件ID是否正确"

    def get_calendar_list(self) -> List[str]:
        """Get list of available calendars"""
        calendars = self.calendar_client.get_calendars()
        return calendars if calendars else []

    def get_calendar_list_formatted(self) -> str:
        """Get formatted list of available calendars for display"""
        calendars = self.calendar_client.get_calendars()
        if calendars:
            return "📋 可用日历:\n" + "\n".join([f"• {cal}" for cal in calendars])
        else:
            return "未找到可用的日历"

# Example usage and testing
def main():
    """Test the calendar agent with example commands"""
    # Note: You need to set configuration in config.json first

    try:
        agent = CalendarAgentDeepSeek()

        # Test commands
        test_commands = [
            "查看今天的日程",
            "创建明天下午3点和张三的会议",
            "添加今天下午2点的团队讨论，地点在会议室A",
            "删除和张三的会议"
        ]

        for cmd in test_commands:
            print(f"\n输入: {cmd}")
            response = agent.process_command(cmd)
            print(f"响应: {response}")

    except Exception as e:
        print(f"初始化失败: {e}")
        print("请确保已设置正确的配置文件:")
        print("请编辑 config.json 文件，填写您的 Apple ID 和 DeepSeek API 密钥")

if __name__ == "__main__":
    main()