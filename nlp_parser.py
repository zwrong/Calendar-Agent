import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dateutil.parser import parse
import pytz

class CalendarNLPParser:
    def __init__(self):
        self.intent_patterns = {
            'create': [
                r'(?:create|add|schedule|make|book)\s+(?:a\s+)?(?:meeting|event|appointment)',
                r'(?:安排|创建|添加|预定|新建)\s*(?:会议|事件|日程|约会)?',
                r'(?:set\s+up|plan)\s+(?:a\s+)?(?:meeting|event)'
            ],
            'read': [
                r'(?:show|list|display|view|check|what\s+is)\s+(?:my\s+)?(?:schedule|calendar|events|meetings)',
                r'(?:查看|显示|列出|检查|看看)\s*(?:日程|日历|事件|会议|安排)?',
                r'(?:when\s+is|when\s+do\s+I\s+have)'
            ],
            'update': [
                r'(?:update|change|modify|reschedule|move)\s+(?:a\s+)?(?:meeting|event|appointment)',
                r'(?:更新|修改|改变|调整|重新安排)\s*(?:会议|事件|日程)?',
                r'(?:edit|alter)\s+(?:the\s+)?(?:event|meeting)'
            ],
            'delete': [
                r'(?:delete|remove|cancel|clear)\s+(?:a\s+)?(?:meeting|event|appointment)',
                r'(?:删除|取消|移除)\s*(?:会议|事件|日程)?',
                r'(?:drop|scratch)\s+(?:the\s+)?(?:event|meeting)'
            ]
        }

    def parse_intent(self, text: str) -> Dict:
        """Parse user intent from natural language text"""
        text = text.lower().strip()

        result = {
            'intent': None,
            'title': None,
            'start_time': None,
            'end_time': None,
            'description': None,
            'location': None,
            'target_event': None,
            'confidence': 0.0
        }

        # Determine intent
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    intent_scores[intent] = intent_scores.get(intent, 0) + 1

        if intent_scores:
            result['intent'] = max(intent_scores, key=intent_scores.get)
            result['confidence'] = max(intent_scores.values()) / len(self.intent_patterns[result['intent']])

        # Extract event details
        result.update(self._extract_event_details(text))

        return result

    def _extract_event_details(self, text: str) -> Dict:
        """Extract event details from text"""
        details = {}

        # Extract title (usually the main subject)
        title = self._extract_title(text)
        if title:
            details['title'] = title

        # Extract time information
        time_info = self._extract_time_info(text)
        details.update(time_info)

        # Extract location
        location = self._extract_location(text)
        if location:
            details['location'] = location

        # Extract description (remaining text after removing time/location)
        description = self._extract_description(text, time_info, location)
        if description:
            details['description'] = description

        return details

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract event title from text"""
        # Remove common command phrases
        cleaned_text = re.sub(
            r'(?:create|add|schedule|make|book|安排|创建|添加|预定|新建|show|list|display|view|check|update|change|modify|delete|remove|cancel|查看|显示|列出|检查|看看|更新|修改|删除|取消)\s*(?:a\s+)?(?:meeting|event|appointment|会议|事件|日程|约会)?',
            '',
            text,
            flags=re.IGNORECASE
        ).strip()

        # Remove time phrases
        cleaned_text = re.sub(
            r'(?:at|on|from|to|until|between|\d{1,2}(?::\d{2})?\s*(?:am|pm)?|今天|明天|下周|上午|下午|点|分|点钟)',
            '',
            cleaned_text,
            flags=re.IGNORECASE
        ).strip()

        # Remove location phrases
        cleaned_text = re.sub(
            r'(?:in|at|location|地点|位置|会议室|room|office|房间)',
            '',
            cleaned_text,
            flags=re.IGNORECASE
        ).strip()

        # Remove common connectors
        cleaned_text = re.sub(r'(?:和|与|with|for|about)', '', cleaned_text, flags=re.IGNORECASE).strip()

        return cleaned_text if cleaned_text else None

    def _extract_time_info(self, text: str) -> Dict:
        """Extract start and end time from text"""
        time_info = {}

        # Common time patterns
        time_patterns = [
            # English patterns
            r'(?:at|from)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
            r'(?:from\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|until|-)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
            r'(?:tomorrow|today|next\s+week)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',

            # Chinese patterns
            r'(?:今天|明天|下周)\s*(?:上午|下午)?(\d{1,2})点(?:\s*(\d{1,2})分)?',
            r'(?:从)?(\d{1,2})点(?:\s*(\d{1,2})分)?\s*(?:到|至)\s*(\d{1,2})点(?:\s*(\d{1,2})分)?'
        ]

        base_date = datetime.now()

        # Check for date references
        if 'tomorrow' in text.lower() or '明天' in text:
            base_date = base_date + timedelta(days=1)
        elif 'next week' in text.lower() or '下周' in text:
            base_date = base_date + timedelta(weeks=1)

        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        if len(match) == 2:  # Single time
                            time_str = match[0] if match[0] else match[1]
                            start_time = self._parse_time_string(time_str, base_date)
                            if start_time:
                                time_info['start_time'] = start_time
                                # Default duration: 1 hour
                                time_info['end_time'] = start_time + timedelta(hours=1)
                        elif len(match) >= 3:  # Time range
                            start_time = self._parse_time_string(match[0], base_date)
                            end_time = self._parse_time_string(match[2], base_date)
                            if start_time and end_time:
                                time_info['start_time'] = start_time
                                time_info['end_time'] = end_time
                    else:  # Single match
                        start_time = self._parse_time_string(match, base_date)
                        if start_time:
                            time_info['start_time'] = start_time
                            time_info['end_time'] = start_time + timedelta(hours=1)

        return time_info

    def _parse_time_string(self, time_str: str, base_date: datetime) -> Optional[datetime]:
        """Parse time string into datetime object"""
        try:
            # Handle Chinese time format
            if '点' in time_str:
                hour_match = re.search(r'(\d{1,2})点', time_str)
                minute_match = re.search(r'(\d{1,2})分', time_str)

                hour = int(hour_match.group(1)) if hour_match else 0
                minute = int(minute_match.group(1)) if minute_match else 0

                # Adjust for AM/PM equivalent in Chinese
                if '下午' in time_str and hour < 12:
                    hour += 12

                return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Handle English time format
            else:
                time_obj = parse(time_str, default=base_date)
                return time_obj

        except:
            return None

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text"""
        location_patterns = [
            r'(?:in|at|location|地点|位置)\s+([^.,!?]+)',
            r'(?:会议室|room|office)\s+([^.,!?]+)'
        ]

        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_description(self, text: str, time_info: Dict, location: str) -> Optional[str]:
        """Extract description from remaining text"""
        # Remove already extracted information
        cleaned_text = text

        if time_info.get('start_time'):
            # Remove time-related phrases
            cleaned_text = re.sub(r'(?:at|on|from|to|until|between|\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', '', cleaned_text, flags=re.IGNORECASE)

        if location:
            cleaned_text = cleaned_text.replace(location, '')

        # Remove command words
        cleaned_text = re.sub(r'(?:create|add|schedule|make|book|安排|创建|添加|预定)', '', cleaned_text, flags=re.IGNORECASE)

        cleaned_text = cleaned_text.strip()

        return cleaned_text if cleaned_text and len(cleaned_text) > 3 else None