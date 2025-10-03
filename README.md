# 🤖 AI Calendar Agent

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-API-orange.svg)](https://www.deepseek.com/)
[![CalDAV](https://img.shields.io/badge/CalDAV-Apple_Calendar-lightgrey.svg)](https://developer.apple.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于DeepSeek API和CalDAV协议的智能日历管理助手，支持通过自然语言对Apple日历进行增删查改操作。

## 🌟 项目亮点

- 🎯 **对标产品**: Toki AI, Smore AI
- 🧠 **智能Agent**: 具备推理、规划、交互能力的LLM Agent
- 📱 **多平台支持**: Web界面，未来支持微信/iMessage
- 🌍 **双语交互**: 完美支持中文和英文指令

## 🎯 项目特色

- 🤖 **智能自然语言理解**: 使用DeepSeek API准确解析用户指令
- 📅 **完整日历操作**: 支持创建、查看、更新、删除日历事件
- 🍎 **Apple日历集成**: 通过CalDAV协议与Apple Calendar无缝集成
- 🌐 **Web界面**: 提供友好的Web界面进行交互
- 🇨🇳 **中英双语支持**: 完美支持中文和英文指令

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- Apple ID (用于日历访问)
- DeepSeek API密钥

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写您的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Apple Calendar CalDAV配置
CALDAV_SERVER_URL=https://caldav.icloud.com/
APPLE_CALENDAR_USERNAME=your_apple_id@icloud.com
APPLE_CALENDAR_PASSWORD=your_app_specific_password

# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key
```

#### 获取Apple日历密码

1. 访问 https://appleid.apple.com
2. 使用您的Apple ID登录
3. 进入"安全"部分
4. 为"CalDAV"生成应用专用密码

#### 获取DeepSeek API密钥

1. 访问 https://platform.deepseek.com/
2. 注册账号并获取API密钥

### 4. 运行应用

```bash
# 启动Web服务
python app.py
```

访问 http://localhost:5000 开始使用！

## 📋 功能特性

### 支持的操作

- **创建事件**: "创建明天下午3点和张三的会议"
- **查看日程**: "查看今天的日程"
- **更新事件**: "更新明天上午10点的会议时间"
- **删除事件**: "删除和张三的会议"
- **搜索事件**: "查找关于项目的会议"

### 支持的语言

- **中文**: "创建明天下午3点的会议"
- **英文**: "create a meeting tomorrow at 3pm"

### 时间解析

- 相对时间: "今天", "明天", "下周"
- 具体时间: "下午3点", "2:30pm"
- 时间范围: "从2点到4点"

## 🏗️ 项目结构

```
calendar_agent/
├── caldav_client.py          # CalDAV客户端
├── deepseek_parser.py        # DeepSeek自然语言解析
├── calendar_agent_deepseek.py # 主要代理逻辑
├── nlp_parser.py             # 基础NLP解析器
├── app.py                    # Flask Web应用
├── requirements.txt          # 依赖列表
├── .env.example              # 环境变量示例
└── templates/
    └── index.html            # Web界面
```

## 🔧 核心组件

### CalDAV客户端 (`caldav_client.py`)

- 连接Apple Calendar服务器
- 实现CRUD操作
- 处理iCalendar格式

### DeepSeek解析器 (`deepseek_parser.py`)

- 使用DeepSeek API解析自然语言
- 提取事件信息
- 智能时间推断

### 日历代理 (`calendar_agent_deepseek.py`)

- 协调各个组件
- 处理用户指令
- 生成响应

## 🧪 测试

### 测试NLP解析

```bash
python test_agent.py
```

### 测试DeepSeek解析

```bash
python deepseek_parser.py
```

## 📝 使用示例

### 中文指令

```
输入: 创建明天下午3点和张三的会议
响应: ✅ 已成功创建事件: 和张三的会议
      📅 时间: 2025-10-04 15:00 - 16:00
      📍 地点: 未指定
      📝 描述: 无

输入: 查看今天的日程
响应: 📅 您的日程安排:
      1. 团队会议
         时间: 14:00 - 15:00
         地点: 会议室A
         描述: 每周例会
```

### 英文指令

```
Input: create a meeting with John tomorrow at 3pm
Response: ✅ Successfully created event: Meeting with John
         📅 Time: 2025-10-04 15:00 - 16:00
         📍 Location: Not specified
         📝 Description: None

Input: show my schedule for today
Response: 📅 Your schedule:
          1. Team Meeting
             Time: 14:00 - 15:00
             Location: Conference Room A
             Description: Weekly meeting
```

## 🔄 开发计划

### 第一阶段 (已完成)
- [x] CalDAV客户端实现
- [x] 基础NLP解析
- [x] DeepSeek API集成
- [x] Web界面

### 第二阶段 (进行中)
- [ ] 冲突检测和智能建议
- [ ] 重复事件支持
- [ ] 多日历管理
- [ ] 提醒设置

### 第三阶段 (规划中)
- [ ] 微信集成
- [ ] iMessage集成
- [ ] 语音交互
- [ ] 机器学习优化

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供强大的自然语言理解API
- [caldav](https://github.com/python-caldav/caldav) - Python CalDAV客户端库
- [Apple](https://www.apple.com/) - CalDAV协议和日历服务