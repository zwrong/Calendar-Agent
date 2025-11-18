import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime


from urllib3 import response

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

    def process_command(self, user_input: str, selected_calendar: str = None, history: Optional[list] = None) -> str:
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
            now = datetime.now().astimezone()
            current_time_zone = now.tzinfo
            UTC_offset = now.utcoffset()
            # user_input = user_input + f"当前时区为{current_time_zone}，UTC偏移为{UTC_offset}"
            parsed = self.nlp_parser.parse_command(user_input, history=history)
            print(f"🔍 Parsed: {parsed}")

            assistant_message = parsed.get('assistant_message') if isinstance(parsed, dict) else None
            payload = parsed.get('payload') if isinstance(parsed, dict) else parsed
            # normalize search_info from top-level or payload, and parse if stringified
            search_info = None
            if isinstance(parsed, dict) and parsed.get('search_info') is not None:
                search_info = parsed.get('search_info')
            elif isinstance(payload, dict) and payload.get('search_info') is not None:
                search_info = payload.get('search_info')
            try:
                if isinstance(search_info, str):
                    import json as _json
                    search_info = _json.loads(search_info)
            except Exception:
                pass

            # 多轮对话：当 intent 为空时，不执行任何增删查改，仅返回 assistant_message
            if not payload or payload.get('intent') is None:
                return assistant_message or ""

            operation_result = None

            if payload.get('intent') is not None:

                intent = payload['intent']
                
                if intent == 'create':
                    needComment, origin, operation_result = self._handle_create_event(payload, selected_calendar)
                elif intent == 'read':
                    needComment, origin, operation_result = self._handle_read_events(payload, selected_calendar, search_info)
                elif intent == 'update':
                    needComment, origin, operation_result = self._handle_update_event(payload, selected_calendar, search_info)
                elif intent == 'delete':
                    needComment, origin, operation_result = self._handle_delete_event(payload, selected_calendar, search_info)

            # Build final response in order: KB -> assistant -> operation
            # final_parts = []
            # if kb_msg:
            #     final_parts.append(kb_msg)
            # if assistant_message:
            #     final_parts.append(assistant_message)
            # if operation_result:
            #     final_parts.append(operation_result)
            # 生成日程评价 - 添加一些温馨提醒
            if needComment:
                comment = self.nlp_parser.generate_comment(operation_result, assistant_message)
                # if comment:
                #     final_parts.append(comment)
            # return "\n\n".join(final_parts)
            return comment

        except Exception as e:
            return f"处理指令时出现错误: {str(e)}"
        
    def _handle_create_event(self, parsed_intent: Dict, selected_calendar: str = None) -> Tuple[bool, List, str]:
        """Handle event creation"""
        from datetime import datetime, timedelta
        needComment = True
        # Validate title
        if not parsed_intent.get('title'):
            return needComment, [], "请提供标题，例如：'创建和张三的会议' 或 '添加提交作业的待办'"

        attrs = parsed_intent.get('component_attributes') or {}

        # Default VEVENT creation
        if not parsed_intent.get('start_time'):
            return needComment, [], "请提供事件的时间，例如：'明天下午3点'"

        start_time = parsed_intent['start_time']
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        if parsed_intent.get('end_time'):
            end_time = parsed_intent['end_time']
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)
        else:
            # by default, set end time to 1 hour after start time
            end_time = start_time.replace(hour=start_time.hour + 1)

        alarms = attrs.get('alarms') if isinstance(attrs.get('alarms'), list) else (attrs.get('alarms') and [attrs.get('alarms')])
        if alarms:
            ical_data = self.calendar_client.create_event_with_alarm(
                title=parsed_intent['title'],
                start_time=start_time,
                end_time=end_time,
                alarm=alarms,
                description=parsed_intent.get('description', ''),
                location=parsed_intent.get('location', ''),
                calendar_name=selected_calendar if selected_calendar is not None else None,
                priority=attrs.get('priority')
            )
            alarms = list(ical_data.walk('VALARM'))
        else:
            ical_data = self.calendar_client.create_event(
                title=parsed_intent['title'],
                start_time=start_time,
                end_time=end_time,
                description=parsed_intent.get('description', ''),
                location=parsed_intent.get('location', ''),
                calendar_name=selected_calendar if selected_calendar is not None else None,
                priority=attrs.get('priority'),
            )
        print(f"the created event data is {ical_data}")
        response = f"✅ 已成功创建事件: {parsed_intent['title']}\n" \
                f"📅 时间: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}\n" \
                f"📍 地点: {parsed_intent.get('location', '未指定')}\n" \
                f"📝 描述: {parsed_intent.get('description', '无')} \n " \
                f"🔔 提醒: {alarms if alarms else '无'}\n" \
                f"优先级: {attrs.get('priority', '无')}\n" \

        return needComment, ical_data, response

    def _handle_read_events(self, parsed_intent: Dict, selected_calendar: str = None, search_info: Dict = None) -> Tuple[bool, List, str]:
        """Handle event reading/listing"""
        print(f"🔍 Reading events with parsed intent: {parsed_intent}")
        needComment = True
        # Determine time range for search
        if search_info.get('start_time'):
            start_date = search_info['start_time']
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date)

            # Use provided end_time if available, otherwise default to end of day
            if search_info.get('end_time'):
                end_date = search_info['end_time']
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
            ical_data, parse_events = self.calendar_client.search_events(
                search_info,
                calendar_name=selected_calendar if selected_calendar is not None else None
            )
        else:
            ical_data, parse_events = self.calendar_client.get_events(
                start_date=start_date,
                end_date=end_date,
                calendar_name=selected_calendar if selected_calendar is not None else None
            )
            
        if not parse_events:
            # Determine which day we're querying for the message
            query_date = start_date.date()
            today = datetime.now().date()
            return needComment, [], "📅 查询时间范围内没有安排任何事件或日程"
        
        needComment = True
        response = "📅 您的日程安排:\n\n"
        for i, event in enumerate(parse_events):
            start_str = event['start'].strftime('%Y-%m-%d %H:%M') if event['start'] else '未知时间'
            end_str = event['end'].strftime('%Y-%m-%d %H:%M') if event['end'] else '未知时间'

            response += f"{i+1}. {event['title']}\n"
            response += f"   时间: {start_str} - {end_str}\n"
            if event.get('location'):
                response += f"   地点: {event['location']}\n"
            if event.get('description'):
                response += f"   描述: {event['description']}\n"
            if event.get('priority'):
                response += f"   优先级: {event['priority']}\n"
            if event.get('alarm'):
                response += f"   提醒: {event['alarm']}\n"
            response += "\n"

        return needComment, ical_data, response.strip()

    def _handle_update_event(self, parsed_intent: Dict, selected_calendar: str = None, search_info: Dict = None) -> Tuple[bool, List, str]:
        """Handle event updates"""
        needComment = True
        from datetime import datetime
        if parsed_intent.get('title'):
            original_ical_data, parse_events = self.calendar_client.search_events(
                search_info,
                calendar_name=selected_calendar if selected_calendar is not None else None
            )

            print(f"🔍 搜索到的事件: {parse_events}")  # 调试信息
            if len(original_ical_data) > 1:
                response = f"查询到的可能的事件如下：\n"
                for i, event in enumerate(parse_events):
                    start_str = event['start'].strftime('%Y-%m-%d %H:%M') if event['start'] else '未知时间'
                    end_str = event['end'].strftime('%Y-%m-%d %H:%M') if event['end'] else '未知时间'

                    response += f"{i+1}. {event['title']}\n"
                    response += f"   时间: {start_str} - {end_str}\n"
                    if event.get('location'):
                        response += f"   地点: {event['location']}\n"
                    if event.get('description'):
                        response += f"   描述: {event['description']}\n"
                    if event.get('priority'):
                        response += f"   优先级: {event['priority']}\n"
                    if event.get('alarm'):
                        response += f"   提醒: {event['alarm']}\n"
                    response += "\n"
                response += "请提供更具体的事件信息。"
                print(f"response: {response}")
                return needComment, [], response.strip()
            
            if parse_events and original_ical_data:
                success = False
                # 优先使用事件对象（包含url）
                first_obj = parse_events[0] if parse_events else None 
                success = False
                if first_obj is not None:
                    event_id = first_obj.get('id')
                    print(f"🔄 目标事件URL: {event_id}")
                    st = parsed_intent.get('start_time')
                    en = parsed_intent.get('end_time')
                    if isinstance(st, datetime):
                        pass
                    elif isinstance(st, str):
                        try:
                            st = datetime.fromisoformat(st)
                        except Exception:
                            st = parsed_intent.get('start_time')
                    if isinstance(en, datetime):
                        pass
                    elif isinstance(en, str):
                        try:
                            en = datetime.fromisoformat(en)
                        except Exception:
                            en = parsed_intent.get('end_time')

                    success = self.calendar_client.update_event(
                        event_id=event_id,
                        title=parsed_intent.get('title'),
                        start_time=st,
                        end_time=en,
                        alarm=parsed_intent.get('component_attributes').get('alarms'),
                        description=parsed_intent.get('description'),
                        location=parsed_intent.get('location'),
                        calendar_name=selected_calendar if selected_calendar is not None else None,
                        priority=(parsed_intent.get('priority') or (parsed_intent.get('component_attributes') or {}).get('priority')),
                    )

                if success:
                    new_title = parsed_intent.get('title') or first_obj.get('title') if first_obj else None
                    start_val = st if st else (first_obj.get('start') if first_obj else None)
                    end_val = en if en else (first_obj.get('end') if first_obj else None)
                    desc_val = parsed_intent.get('description') or (first_obj.get('description') if first_obj else None)
                    loc_val = parsed_intent.get('location') or (first_obj.get('location') if first_obj else None)
                    pri_val = parsed_intent.get('priority') or (first_obj.get('priority') if first_obj else None)
                    response = f"✅ 事件已成功更新 \n更新内容:\n"
                    if new_title is not None:
                        response += f"   标题: {str(new_title)}\n"
                    if start_val is not None:
                        try:
                            response += f"   开始时间: {start_val.strftime('%Y-%m-%d %H:%M')}\n"
                        except Exception:
                            response += f"   开始时间: {str(start_val)}\n"
                    if end_val is not None:
                        try:
                            response += f"   结束时间: {end_val.strftime('%Y-%m-%d %H:%M')}\n"
                        except Exception:
                            response += f"   结束时间: {str(end_val)}\n"
                    if desc_val is not None:
                        response += f"   描述: {str(desc_val)}\n"
                    if loc_val is not None:
                        response += f"   地点: {str(loc_val)}\n"
                    if pri_val is not None:
                        response += f"   优先级: {str(pri_val)}\n"
                    return needComment, [], response.strip()
            else:
                return needComment, [], "找不到指定的事件，请提供更具体的信息" 
        else:
            return needComment, [], "请指定要更新的事件，例如：'修改和张三的会议时间'"
        
    def _handle_delete_event(self, parsed_intent: Dict, selected_calendar: str = None, search_info: Dict = None) -> Tuple[bool, List, str]:
        """Handle event deletion"""
        print(f"尝试删除事件: {parsed_intent.get('target_event')}")
        needComment = True
        # Delete all events with matching title
        original_ical_data, parsed_events = self.calendar_client.search_events(
            search_info,
            calendar_name=selected_calendar if selected_calendar is not None else None
        )
        events = parsed_events
        if events:
            mode = ((search_info or {}).get('match_mode') or '').lower()
            if mode == 'all':
                deleted_count = 0
                for event in events:
                    eid = event.get('id')
                    print(f"找到事件，开始删除: {eid}")
                    if eid and self.calendar_client.delete_event(
                        eid,
                        calendar_name=selected_calendar if selected_calendar is not None else None
                    ):
                        deleted_count += 1

                if deleted_count > 0:
                    return needComment, [], f"✅ 已成功删除 {deleted_count} 个事件"
                else:
                    return needComment, [], "❌ 删除事件失败"
            else:
                first = events[0]
                eid = first.get('id')
                if eid and self.calendar_client.delete_event(
                            eid,
                            calendar_name=selected_calendar if selected_calendar is not None else None
                        ):
                    return needComment, [], "✅ 已成功删除事件"
                else:
                    return needComment, [], "❌ 删除事件失败"
        else:
            return needComment, [], "找不到指定的事件，请提供更具体的信息"

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