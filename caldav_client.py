import caldav
from icalendar import Calendar, Event, Todo, Alarm, vCalAddress, vText
from datetime import datetime, timedelta
import pytz
import os
from typing import List, Dict, Optional
from datetime import datetime as _dt

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
                    calendar_name: str = None,
                    priority: str = None) -> str:
        """Create a new calendar event"""
        calendar = self.get_calendar_by_name(calendar_name) if calendar_name else self.get_default_calendar()

        if not calendar:
            raise ValueError("No calendar available")

        event = Event()
        event.add('summary', title)
        event.add('dtstart', self._to_utc(start_time))
        event.add('dtend', self._to_utc(end_time))

        if description:
            event.add('description', description)
        if location:
            event.add('location', location)
        if priority is not None:
            event.add('priority', priority)

        # Add creation timestamp
        event.add('dtstamp', datetime.now(pytz.UTC))

        # Save event
        calendar_event = calendar.save_event(event.to_ical())
        print(f"event的形式是{event}") # 调试
        return event

    def create_event_with_alarm(self,
                    title: str,
                    start_time: datetime,
                    end_time: datetime,
                    alarm: Dict = None,
                    description: str = "",
                    location: str = "",
                    calendar_name: str = None,
                    priority: str = None) -> str:
        """Create a new calendar event with VALARM subcomponent"""
        calendar = self.get_calendar_by_name(calendar_name) if calendar_name else self.get_default_calendar()

        if not calendar:
            raise ValueError("No calendar available")

        event = Event()
        event.add('summary', title)
        event.add('dtstart', self._to_utc(start_time))
        event.add('dtend', self._to_utc(end_time))

        if description:
            event.add('description', description)
        if location:
            event.add('location', location)
        if priority is not None:
            event.add('priority', priority)

        # Add creation timestamp
        event.add('dtstamp', datetime.now(pytz.UTC))

        alarms = alarm if isinstance(alarm, list) else ([alarm] if isinstance(alarm, dict) else [])
        for a in alarms:
            try:
                cal_alarm = Alarm()
                cal_alarm.add('action', (a.get('action') or 'DISPLAY'))
                trig_value, trig_params = self._parse_trigger(a.get('trigger'))
                from datetime import datetime as dt
                if isinstance(trig_value, dt) and trig_value.tzinfo is None:
                    try:
                        local_tz = datetime.now().astimezone().tzinfo
                        tz_to_use = start_time.tzinfo or local_tz
                        trig_value = trig_value.replace(tzinfo=tz_to_use)
                    except Exception:
                        pass
                if trig_value is not None:
                    if trig_params:
                        cal_alarm.add('trigger', trig_value, parameters={'related': trig_params.get('related')})
                    else:
                        cal_alarm.add('trigger', trig_value)
                if a.get('description'):
                    cal_alarm.add('description', a.get('description'))
                if a.get('repeat') is not None:
                    cal_alarm.add('repeat', a.get('repeat'))
                if a.get('duration'):
                    cal_alarm.add('duration', a.get('duration'))
                if a.get('attach'):
                    cal_alarm.add('attach', a.get('attach'))
                event.add_component(cal_alarm)
                print(f"infomation of event: {event}")
            except Exception as e:
                print(f"附加 VALARM 失败: {e}")

        # Save event
        calendar_event = calendar.save_event(event.to_ical())
        return event

    def get_events(self,
                  start_date: datetime = None,
                  end_date: datetime = None,
                  calendar_name: str = None) -> List[Dict]:
        """Get events within a date range"""
        calendar = self.get_calendar_by_name(calendar_name) if calendar_name else self.get_default_calendar()

        if not calendar:
            return [], []

        # Default to today if no dates provided
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = start_date + timedelta(days=1)

        events = calendar.date_search(start=start_date, end=end_date)
        original_ical_data = []
        parsed_events = []
        for event in events:
            ical_data = event.icalendar_component
            original_ical_data.append(ical_data)
            print(f'原始ical数据: {ical_data}')
            event_data = {
                'id': event.url,
                'title': str(ical_data.get('summary', '')),
                'start': ical_data.get('dtstart').dt if ical_data.get('dtstart') else None,
                'end': ical_data.get('dtend').dt if ical_data.get('dtend') else None,
                'description': str(ical_data.get('description', '')) if ical_data.get('description') else None,
                'location': str(ical_data.get('location', '')) if ical_data.get('location') else None,
                'priority': str(ical_data.get('priority', '')) if ical_data.get('priority') else None,
                'alarms': list(ical_data.walk('valarm'))
            }
            parsed_events.append(event_data)

        return original_ical_data, parsed_events

    def update_event(self,
                    event_id: str,
                    title: str = None,
                    start_time: datetime = None,
                    end_time: datetime = None,
                    alarm: Optional[List[Dict]] = None,
                    description: str = None,
                    location: str = None,
                    calendar_name: str = None,
                    priority: Optional[int] = None) -> bool:
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
                            ical_data['dtstart'] = self._to_utc(start_time)
                        if end_time:
                            ical_data['dtend'] = self._to_utc(end_time)
                        if description is not None:
                            ical_data['description'] = description
                        if location is not None:
                            ical_data['location'] = location
                        if priority is not None:
                            ical_data['priority'] = priority
                        if alarm:
                            alarms = alarm
                        elif ical_data.walk('valarm'):
                            alarms = []
                            for al in ical_data.walk('valarm'):
                                new_alarm = {}
                                new_alarm['action'] = str(al.get('action')) if al.get('action') else 'DISPLAY'
                                trig = al.get('trigger')
                                new_alarm['trigger'] = trig.dt if getattr(trig, 'dt', None) is not None else trig
                                if al.get('description'):
                                    new_alarm['description'] = str(al.get('description'))
                                else:
                                    new_alarm['description'] = None
                                alarms.append(new_alarm)
                        else:
                            alarms = None
                    
                        try:
                            event.delete()
                            success = True
                        except Exception:
                            success = False

                        if not success:
                            return False
                        print(f'更新后的ical数据: {ical_data}')
                        if not alarms:
                            self.create_event(
                                title = str(ical_data.get('summary', '')),
                                start_time = (ical_data.get('dtstart') if ical_data.get('dtstart') else None),
                                end_time = (ical_data.get('dtend') if ical_data.get('dtend') else None),
                                description = (str(ical_data.get('description', '')) if ical_data.get('description') else None),
                                location = (str(ical_data.get('location', '')) if ical_data.get('location') else None),
                                priority = (int(str(ical_data.get('priority'))) if ical_data.get('priority') else None),
                                calendar_name = (calendar.name if hasattr(calendar, 'name') else None),
                            )
                        else:
                            self.create_event_with_alarm(
                                title = str(ical_data.get('summary', '')),
                                start_time = (ical_data.get('dtstart') if ical_data.get('dtstart') else None),
                                end_time = (ical_data.get('dtend') if ical_data.get('dtend') else None),
                                alarm = alarms,
                                description = (str(ical_data.get('description', '')) if ical_data.get('description') else None),
                                location = (str(ical_data.get('location', '')) if ical_data.get('location') else None),
                                priority = (int(str(ical_data.get('priority'))) if ical_data.get('priority') else None),
                                calendar_name = (calendar.name if hasattr(calendar, 'name') else None),
                            )
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

    def _filter_event(self, event, search_info: Dict, start, end, match_mode, exclude_all_day):
        """
        过滤单个事件，根据搜索条件判断是否匹配
        """
        ical_data = event.icalendar_component
        title = str(ical_data.get('summary', '')).lower()
        desc = str(ical_data.get('description', '')).lower()
        
        # 关键词过滤
        keyword = search_info.get('keyword') if search_info else None
        if keyword and not (str(keyword).lower() in title or str(keyword).lower() in desc):
            return None
        
        # 暂时不对比时间
        # # 提取事件时间
        # ev_start_prop = ical_data.get('dtstart')
        # ev_end_prop = ical_data.get('dtend')
        # ev_start = ev_start_prop.dt if ev_start_prop is not None else None
        # ev_end = ev_end_prop.dt if ev_end_prop is not None else None

        # # 时区对齐
        # ev_start, start_cmp = self._align_timezone(ev_start, start)
        # ev_end, end_cmp = self._align_timezone(ev_end, end)

        # # 时间范围匹配
        # if not self._is_event_in_range(ev_start, ev_end, start_cmp, end_cmp, match_mode):
        #     return None
        # print(f"事件数据：{event.data}")
        # 构建返回数据
        return ical_data

    def _is_all_day_event(self, ev_start, ev_end):
        """检测全天事件（支持date类型和datetime型全天事件）"""
        from datetime import datetime, date, time
        
        # 传统检测：date类型
        if ev_start is not None and not isinstance(ev_start, datetime):
            return True
        if ev_end is not None and not isinstance(ev_end, datetime):
            return True
            
        # iCloud风格检测：datetime类型但时间范围为00:00-23:59
        if (isinstance(ev_start, datetime) and isinstance(ev_end, datetime) and
            ev_start.time() == time(0, 0) and ev_end.time() == time(23, 59)):
            return True
            
        # 持续时间检测：接近24小时的事件
        if (isinstance(ev_start, datetime) and isinstance(ev_end, datetime) and
            (ev_end - ev_start).total_seconds() >= 86340):  # 23小时59分钟
            return True
            
        return False

    def _align_timezone(self, event_time, reference_time):
        """时区对齐，避免aware/naive比较错误"""
        from datetime import datetime
        
        if not isinstance(event_time, datetime) or not isinstance(reference_time, datetime):
            return event_time, reference_time
            
        if event_time.tzinfo is not None and reference_time.tzinfo is None:
            return event_time, reference_time.replace(tzinfo=event_time.tzinfo)
        if event_time.tzinfo is None and reference_time.tzinfo is not None:
            return event_time.replace(tzinfo=reference_time.tzinfo), reference_time
            
        return event_time, reference_time

    def _is_event_in_range(self, ev_start, ev_end, search_start, search_end, match_mode):
        """判断事件是否在搜索时间范围内"""
        print(f"事件开始时间是 {ev_start}, 结束时间是 {ev_end}")
        print(f"搜索开始时间是 {search_start}, 搜索结束时间是 {search_end}")
        if match_mode == 'precise':
            # 精确匹配：事件完全在搜索范围内
            if ev_start is not None and ev_end is not None:
                return (ev_start >= search_start) and (ev_end <= search_end)
            return False
        else:
            # 重叠匹配：事件与搜索范围有重叠
            if ev_start is not None and ev_end is not None:
                return (ev_start < search_end) and (ev_end > search_start)
            elif ev_start is not None and ev_end is None:
                return ev_start < search_end
            elif ev_end is not None and ev_start is None:
                return ev_end > search_start
            else:
                return False

    def search_events(self, search_info: Dict, calendar_name: str = None) -> tuple[List, List]:
        """
        根据关键词和时间范围搜索事件
        
        Args:
            search_info: 搜索参数，包含keyword、start_time、end_time、match_mode、exclude_all_day
            calendar_name: 日历名称，为空时使用默认日历
            
        Returns:
            List[Dict]: 匹配的事件列表
        """
        from datetime import datetime

        calendar = self.get_calendar_by_name(calendar_name) if calendar_name else self.get_default_calendar()
        if not calendar:
            return [], []

        # 解析时间范围
        info = search_info or {}
        
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
        
        
        print(f"搜索时间范围: {start_date} 到 {end_date}")  # 调试信息
        
        try:
            # 使用日期范围搜索，避免加载所有事件
            events = calendar.date_search(start=start_date, end=end_date)
            original_ical_data = []
            parsed_events = []

            # # 解析匹配模式和全天事件过滤设置
            # from datetime import datetime as _dt, timedelta as _td
            # match_mode = (info.get('match_mode') or 'overlap').lower()
            # exclude_all_day = info.get('exclude_all_day', False)
            
            # # 智能默认设置：短时间范围自动使用精确匹配和排除全天事件
            # if isinstance(start, _dt) and isinstance(end, _dt):
            #     duration = end - start
            #     if info.get('match_mode') is None and duration <= _td(hours=6):
            #         match_mode = 'precise'
            #     if info.get('exclude_all_day') is None and duration <= _td(hours=12):
            #         exclude_all_day = True

            # 过滤事件
            match_mode = search_info.get('match_mode') or 'overlap'
            exclude_all_day = search_info.get('exclude_all_day', False)
            
            for event in events:
                print(event.data)
                ical_data = self._filter_event(event, search_info, start_date, end_date, match_mode, exclude_all_day)
                if ical_data:
                    parsed_data = {
                        'id': event.url,
                        'title': str(ical_data.get('summary', '')),
                        'start': ical_data.get('dtstart').dt if ical_data.get('dtstart') else None,
                        'end': ical_data.get('dtend').dt if ical_data.get('dtend') else None,
                        'description': str(ical_data.get('description', '')) if ical_data.get('description') else None,
                        'location': str(ical_data.get('location', '')) if ical_data.get('location') else None,
                        'priority': str(ical_data.get('priority', '')) if ical_data.get('priority') else None,
                        'alarm': list(ical_data.walk('VALARM')) if ical_data.walk('VALARM') else None,
                    }
                    parsed_events.append(parsed_data)
                    original_ical_data.append(ical_data)

            return original_ical_data, parsed_events
        except Exception as e:
            print(f"搜索事件时出错: {e}")
            return [], []

    def add_alarm_to_item(self, event_id: str, alarm: Dict, calendar_name: str = None) -> bool:
        """Attach a VALARM to an existing VEVENT identified by URL."""
        try:
            calendars_to_search = [self.get_calendar_by_name(calendar_name)] if calendar_name else self.calendars
            for calendar in calendars_to_search:
                if not calendar:
                    continue
                items = []
                # Search both events and todos
                if hasattr(calendar, 'events'):
                    try:
                        items.extend(calendar.events())
                    except Exception:
                        pass

                for item in items:
                    if item.url == event_id:
                        ical_data = item.icalendar_component
                        try:
                            cal_alarm = Alarm()
                            cal_alarm.add('action', alarm.get('action') or 'DISPLAY')
                            trig_value, trig_params = self._parse_trigger(alarm.get('trigger'))
                            from datetime import datetime as dt
                            if isinstance(trig_value, dt) and trig_value.tzinfo is None:
                                try:
                                    ev_start = None
                                    try:
                                        ev_start_prop = ical_data.get('dtstart')
                                        ev_start = ev_start_prop.dt if ev_start_prop is not None else None
                                    except Exception:
                                        ev_start = None
                                    local_tz = datetime.now().astimezone().tzinfo
                                    tz_to_use = (ev_start.tzinfo if isinstance(ev_start, dt) and ev_start.tzinfo is not None else local_tz)
                                    trig_value = trig_value.replace(tzinfo=tz_to_use)
                                except Exception:
                                    pass
                            if trig_value is not None:
                                if trig_params:
                                    cal_alarm.add('trigger', trig_value, parameters={'related': trig_params.get('related')})
                                else:
                                    cal_alarm.add('trigger', trig_value)
                            if alarm.get('description'):
                                cal_alarm.add('description', alarm.get('description'))
                            if alarm.get('repeat') is not None:
                                cal_alarm.add('repeat', alarm.get('repeat'))
                            if alarm.get('duration'):
                                cal_alarm.add('duration', alarm.get('duration'))
                            if alarm.get('attach'):
                                cal_alarm.add('attach', alarm.get('attach'))

                            ical_data.add_component(cal_alarm)
                            item.data = ical_data.to_ical()
                            return True
                        except Exception as e:
                            print(f"添加 VALARM 失败: {e}")
                            return False
            print(f"未找到可添加提醒的项目: {event_id}")
            return False
        except Exception as e:
            print(f"Error adding VALARM: {e}")
            return False

    def get_calendar_by_name(self, name: str):
        """Get calendar by name"""
        for cal in self.calendars:
            if cal.name == name:
                return cal
        return None

    def _to_utc(self, dt):
        from datetime import datetime as dtcls, date as dcls
        if isinstance(dt, dtcls):
            if dt.tzinfo is None:
                try:
                    local_tz = datetime.now().astimezone().tzinfo
                except Exception:
                    local_tz = pytz.UTC
                dt = dt.replace(tzinfo=local_tz)
            return dt.astimezone(pytz.UTC)
        return dt

    def _parse_trigger(self, value):
        try:
            from datetime import timedelta
            from datetime import datetime as dt
            import re
            if value is None:
                return None, {}
            if isinstance(value, timedelta):
                return value, {'related': 'START'}
            if isinstance(value, dt):
                return value, {}
            if isinstance(value, str):
                s = value.strip()
                sign = -1 if s.startswith('-') else 1
                if s.startswith('-'):
                    s = s[1:]
                if s.startswith('P'):
                    days = 0
                    hours = 0
                    minutes = 0
                    seconds = 0
                    m = re.search(r'P(\d+)D', s)
                    if m:
                        days = int(m.group(1))
                    if 'T' in s:
                        t = s.split('T')[1]
                        mh = re.search(r'(\d+)H', t)
                        mm = re.search(r'(\d+)M', t)
                        ms = re.search(r'(\d+)S', t)
                        hours = int(mh.group(1)) if mh else 0
                        minutes = int(mm.group(1)) if mm else 0
                        seconds = int(ms.group(1)) if ms else 0
                    td = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
                    td = timedelta(seconds=sign * td.total_seconds())
                    return td, {'related': 'START'}
                try:
                    from dateutil.parser import parse
                    dtv = parse(s)
                    return dtv, {}
                except Exception:
                    return None, {}
            return None, {}
        except Exception:
            return None, {}

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