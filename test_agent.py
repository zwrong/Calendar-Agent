#!/usr/bin/env python3
"""
Test script for Calendar Agent
This script tests the NLP parsing without requiring actual calendar credentials
"""

from deepseek_parser import DeepSeekCalendarParser

def test_nlp_parsing():
    """Test NLP parsing with various commands"""
    parser = DeepSeekCalendarParser()

    test_commands = [
        # Chinese commands
        "创建明天下午3点和张三的会议",
        "查看今天的日程",
        "添加今天下午2点的团队讨论，地点在会议室A",
        "删除和张三的会议",
        "更新明天上午10点的会议时间",

        # English commands
        "create a meeting with John tomorrow at 3pm",
        "show my schedule for today",
        "add team discussion today at 2pm in conference room A",
        "delete the meeting with John",
        "update tomorrow's 10am meeting"
    ]

    print("🧪 Testing NLP Parser")
    print("=" * 50)

    for cmd in test_commands:
        print(f"\n📝 Input: {cmd}")
        result = parser.parse_command(cmd)
        print(f"🎯 Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
        print(f"📋 Details:")
        for key, value in result.items():
            if key not in ['intent', 'confidence'] and value:
                print(f"   - {key}: {value}")

if __name__ == "__main__":
    test_nlp_parsing()