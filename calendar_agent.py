import os
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from caldav_client import AppleCalendarClient, parse_natural_date
from nlp_parser import CalendarNLPParser

load_dotenv()

class CalendarAgent:
    def __init__(self):
        """Initialize the calendar agent with CalDAV client and NLP parser"""
        self.nlp_parser = CalendarNLPParser()

        # Get credentials from environment variables
        server_url = os.getenv('CALDAV_SERVER_URL', 'https://caldav.icloud.com/')
        username = os.getenv('APPLE_CALENDAR_USERNAME')
        password = os.getenv('APPLE_CALENDAR_PASSWORD')

        if not username or not password:
            raise ValueError("Please set APPLE_CALENDAR_USERNAME and APPLE_CALENDAR_PASSWORD environment variables")

        self.calendar_client = AppleCalendarClient(server_url, username, password)

    def process_command(self, user_input: str) -> str:
        """
        Process natural language command and execute calendar operation

        Args:
            user_input: Natural language command from user

        Returns:
            Response message to user
        """
        try:
            # Parse user intent and extract details
            parsed_intent = self.nlp_parser.parse_intent(user_input)

            if not parsed_intent['intent']:
                return "抱歉，我没有理解您的指令。请尝试使用更清晰的表达，比如：'创建明天下午3点的会议' 或 '查看今天的日程'"

            intent = parsed_intent['intent']

            if intent == 'create':
                return self._handle_create_event(parsed_intent)
            elif intent == 'read':
                return self._handle_read_events(parsed_intent)
            elif intent == 'update':
                return self._handle_update_event(parsed_intent)
            elif intent == 'delete':
                return self._handle_delete_event(parsed_intent)
            else:
                return f"暂不支持的操作: {intent}"

        except Exception as e:
            return f"处理指令时出现错误: {str(e)}"

    def _handle_create_event(self, parsed_intent: Dict) -> str:
        """Handle event creation"""
        # Validate required fields
        if not parsed_intent.get('title'):
            return "请提供事件的标题，例如：'创建和张三的会议'"

        if not parsed_intent.get('start_time'):
            return "请提供事件的时间，例如：'明天下午3点'"

        # Set default end time if not provided
        start_time = parsed_intent['start_time']
        end_time = parsed_intent.get('end_time', start_time.replace(hour=start_time.hour + 1))

        # Create the event
        event_id = self.calendar_client.create_event(
            title=parsed_intent['title'],
            start_time=start_time,
            end_time=end_time,
            description=parsed_intent.get('description', ''),
            location=parsed_intent.get('location', '')
        )

        return f"✅ 已成功创建事件: {parsed_intent['title']}\n" \
               f"📅 时间: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}\n" \
               f"📍 地点: {parsed_intent.get('location', '未指定')}"

    def _handle_read_events(self, parsed_intent: Dict) -> str:
        """Handle event reading/listing"""
        # Determine time range for search
        start_date = parsed_intent.get('start_time', datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
        end_date = start_date.replace(hour=23, minute=59, second=59)

        # If searching for specific event
        if parsed_intent.get('title'):
            events = self.calendar_client.search_events(parsed_intent['title'])
        else:
            events = self.calendar_client.get_events(start_date=start_date, end_date=end_date)

        if not events:
            return "📅 今天没有安排任何事件"

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

    def _handle_update_event(self, parsed_intent: Dict) -> str:
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
            location=parsed_intent.get('location')
        )

        if success:
            return "✅ 事件已成功更新"
        else:
            return "❌ 更新事件失败，请检查事件ID是否正确"

    def _handle_delete_event(self, parsed_intent: Dict) -> str:
        """Handle event deletion"""
        if not parsed_intent.get('target_event'):
            # Try to find event by title
            if parsed_intent.get('title'):
                events = self.calendar_client.search_events(parsed_intent['title'])
                if events:
                    parsed_intent['target_event'] = events[0]['id']
                else:
                    return "找不到指定的事件，请提供更具体的信息"
            else:
                return "请指定要删除的事件，例如：'删除和张三的会议'"

        # Delete the event
        success = self.calendar_client.delete_event(parsed_intent['target_event'])

        if success:
            return "✅ 事件已成功删除"
        else:
            return "❌ 删除事件失败，请检查事件ID是否正确"

    def get_calendar_list(self) -> str:
        """Get list of available calendars"""
        calendars = self.calendar_client.get_calendars()
        if calendars:
            return "📋 可用日历:\n" + "\n".join([f"• {cal}" for cal in calendars])
        else:
            return "未找到可用的日历"

# Example usage and testing
def main():
    """Test the calendar agent with example commands"""
    # Note: You need to set environment variables first
    # export APPLE_CALENDAR_USERNAME="your_apple_id"
    # export APPLE_CALENDAR_PASSWORD="your_app_specific_password"

    try:
        agent = CalendarAgent()

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
        print("请确保已设置正确的环境变量:")
        print("export APPLE_CALENDAR_USERNAME='your_apple_id'")
        print("export APPLE_CALENDAR_PASSWORD='your_app_specific_password'")

if __name__ == "__main__":
    main()