import caldav
from icalendar import Calendar, Event, vCalAddress, vText
from datetime import datetime, timedelta
import pytz
import os
from typing import List, Dict, Optional

class AppleCalendarClient:
    def __init__(self, server_url: str, username: str, password: str):
        """
        Initialize CalDAV client for Apple Calendar

        Apple Calendar CalDAV URLs:
        - Primary: https://caldav.icloud.com/
        - Alternative: https://pXX-caldav.icloud.com/ (where XX is server number)
        """
        import requests

        # 设置更长的超时时间
        session = requests.Session()
        session.timeout = 30  # 30秒超时

        self.client = caldav.DAVClient(
            url=server_url,
            username=username,
            password=password
        )

        try:
            print("正在连接 CalDAV 服务器...")
            print(f"服务器URL: {server_url}")
            print(f"用户名: {username}")

            self.principal = self.client.principal()
            print("✓ 成功获取 principal")

            print("正在获取日历列表...")
            self.calendars = self.principal.calendars()
            print(f"✓ 成功连接，找到 {len(self.calendars)} 个日历")

            # Print calendar names for debugging
            for i, cal in enumerate(self.calendars):
                print(f"  日历 {i+1}: {cal.name}")

        except Exception as e:
            print(f"❌ CalDAV 连接失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            print(f"详细错误信息:\n{traceback.format_exc()}")
            raise

    def get_calendars(self) -> List[str]:
        """Get list of available calendars"""
        return [cal.name for cal in self.calendars]

    def get_default_calendar(self):
        """Get the default calendar"""
        return self.calendars[0] if self.calendars else None

    def create_event(self,
                    title: str,
                    start_time: datetime,
                    end_time: datetime,
                    description: str = "",
                    location: str = "",
                    calendar_name: str = None) -> str:
        """Create a new calendar event"""
        calendar = self.get_calendar_by_name(calendar_name) if calendar_name else self.get_default_calendar()

        if not calendar:
            raise ValueError("No calendar available")

        event = Event()
        event.add('summary', title)
        event.add('dtstart', start_time)
        event.add('dtend', end_time)

        if description:
            event.add('description', description)
        if location:
            event.add('location', location)

        # Add creation timestamp
        event.add('dtstamp', datetime.now(pytz.UTC))

        # Save event
        calendar_event = calendar.save_event(event.to_ical())
        return calendar_event.url

    def get_events(self,
                  start_date: datetime = None,
                  end_date: datetime = None,
                  calendar_name: str = None) -> List[Dict]:
        """Get events within a date range"""
        calendar = self.get_calendar_by_name(calendar_name) if calendar_name else self.get_default_calendar()

        if not calendar:
            return []

        # Default to today if no dates provided
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = start_date + timedelta(days=1)

        events = calendar.date_search(start=start_date, end=end_date)

        parsed_events = []
        for event in events:
            ical_data = event.icalendar_component
            event_data = {
                'id': event.url,
                'title': str(ical_data.get('summary', '')),
                'start': ical_data.get('dtstart').dt if ical_data.get('dtstart') else None,
                'end': ical_data.get('dtend').dt if ical_data.get('dtend') else None,
                'description': str(ical_data.get('description', '')),
                'location': str(ical_data.get('location', ''))
            }
            parsed_events.append(event_data)

        return parsed_events

    def update_event(self,
                    event_id: str,
                    title: str = None,
                    start_time: datetime = None,
                    end_time: datetime = None,
                    description: str = None,
                    location: str = None,
                    calendar_name: str = None) -> bool:
        """Update an existing event"""
        try:
            # If calendar_name is specified, only search in that calendar
            calendars_to_search = [self.get_calendar_by_name(calendar_name)] if calendar_name else self.calendars

            for calendar in calendars_to_search:
                if not calendar:
                    continue

                events = calendar.events()
                for event in events:
                    if event.url == event_id:
                        ical_data = event.icalendar_component

                        # Update fields
                        if title:
                            ical_data['summary'] = title
                        if start_time:
                            ical_data['dtstart'] = start_time
                        if end_time:
                            ical_data['dtend'] = end_time
                        if description is not None:
                            ical_data['description'] = description
                        if location is not None:
                            ical_data['location'] = location

                        # Save updated event
                        event.data = ical_data.to_ical()
                        return True

            print(f"Event not found: {event_id}")
            return False
        except Exception as e:
            print(f"Error updating event: {e}")
            return False

    def delete_event(self, event_id: str, calendar_name: str = None) -> bool:
        """Delete an event"""
        try:
            print(f"尝试删除事件: {event_id}")  # 调试信息

            # If calendar_name is specified, only search in that calendar
            calendars_to_search = [self.get_calendar_by_name(calendar_name)] if calendar_name else self.calendars

            for calendar in calendars_to_search:
                if not calendar:
                    continue

                events = calendar.events()
                for event in events:
                    if str(event.url) == str(event_id):
                        print(f"找到事件，开始删除: {event.url}")  # 调试信息
                        event.delete()
                        print("删除操作完成")  # 调试信息
                        return True

            print(f"Event not found: {event_id}")
            return False
        except Exception as e:
            print(f"Error deleting event: {e}")
            return False

    def search_events(self, query: str, calendar_name: str = None) -> List[Dict]:
        """Search events by title or description, only return future and today's events"""
        from datetime import datetime

        calendar = self.get_calendar_by_name(calendar_name) if calendar_name else self.get_default_calendar()

        if not calendar:
            return []

        # 只搜索近3个月及未来的事件，避免加载所有历史事件
        current_time = datetime.now()
        three_months_ago = current_time.replace(day=1) - timedelta(days=90)

        try:
            # 使用日期范围搜索，避免加载所有事件
            events = calendar.date_search(start=three_months_ago, end=current_time + timedelta(days=365))
            matching_events = []

            for event in events:
                ical_data = event.icalendar_component
                title = str(ical_data.get('summary', '')).lower()
                desc = str(ical_data.get('description', '')).lower()

                if query.lower() in title or query.lower() in desc:
                    event_data = {
                        'id': event.url,
                        'title': str(ical_data.get('summary', '')),
                        'start': ical_data.get('dtstart').dt if ical_data.get('dtstart') else None,
                        'end': ical_data.get('dtend').dt if ical_data.get('dtend') else None,
                        'description': str(ical_data.get('description', '')),
                        'location': str(ical_data.get('location', ''))
                    }
                    matching_events.append(event_data)

            return matching_events
        except Exception as e:
            print(f"搜索事件时出错: {e}")
            return []

    def get_calendar_by_name(self, name: str):
        """Get calendar by name"""
        for cal in self.calendars:
            if cal.name == name:
                return cal
        return None

# Helper functions for date parsing
def parse_natural_date(date_str: str) -> datetime:
    """Parse natural language dates like 'tomorrow 3pm', 'next Monday', etc."""
    from dateutil.parser import parse
    from dateutil.relativedelta import relativedelta

    date_str = date_str.lower().strip()

    # Handle common natural language patterns
    if 'tomorrow' in date_str:
        base_date = datetime.now() + timedelta(days=1)
        date_str = date_str.replace('tomorrow', base_date.strftime('%Y-%m-%d'))
    elif 'today' in date_str:
        base_date = datetime.now()
        date_str = date_str.replace('today', base_date.strftime('%Y-%m-%d'))
    elif 'next week' in date_str:
        base_date = datetime.now() + timedelta(weeks=1)
        date_str = date_str.replace('next week', base_date.strftime('%Y-%m-%d'))

    try:
        return parse(date_str)
    except:
        raise ValueError(f"Could not parse date: {date_str}")