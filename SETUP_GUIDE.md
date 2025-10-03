# 🛠️ 详细配置指南

## 环境配置步骤

### 1. 创建环境配置文件

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env  # 或者使用其他编辑器
```

### 2. 配置Apple日历访问

#### 获取Apple应用专用密码

1. **访问Apple ID管理页面**
   - 打开 https://appleid.apple.com
   - 使用您的Apple ID登录

2. **进入安全设置**
   - 在左侧菜单点击"安全"
   - 找到"应用专用密码"部分

3. **生成专用密码**
   - 点击"生成应用专用密码"
   - 输入标签：`CalDAV日历助手`
   - 点击"创建"
   - **重要：立即复制生成的16位密码**（格式：xxxx-xxxx-xxxx-xxxx）

4. **配置环境变量**
   编辑 `.env` 文件：
   ```env
   # Apple Calendar配置
   CALDAV_SERVER_URL=https://caldav.icloud.com/
   APPLE_CALENDAR_USERNAME=您的Apple_ID@icloud.com
   APPLE_CALENDAR_PASSWORD=您生成的16位应用专用密码
   ```

**注意：**
- 使用完整的Apple ID邮箱地址
- 应用专用密码不是您的Apple ID密码
- 密码格式为：abcd-efgh-ijkl-mnop

### 3. 配置DeepSeek API

#### 获取DeepSeek API密钥

1. **访问DeepSeek平台**
   - 打开 https://platform.deepseek.com/
   - 注册账号并登录

2. **获取API密钥**
   - 进入API密钥管理页面
   - 点击"创建新的API密钥"
   - 复制生成的API密钥

3. **配置环境变量**
   编辑 `.env` 文件：
   ```env
   # DeepSeek API配置
   DEEPSEEK_API_KEY=您的DeepSeek_API密钥
   ```

### 4. 最终配置文件示例

您的 `.env` 文件应该类似这样：

```env
# Apple Calendar CalDAV Configuration
CALDAV_SERVER_URL=https://caldav.icloud.com/
APPLE_CALENDAR_USERNAME=your_real_email@icloud.com
APPLE_CALENDAR_PASSWORD=abcd-efgh-ijkl-mnop

# DeepSeek API Configuration
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. 激活虚拟环境并运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖（如果还没安装）
pip install -r requirements.txt

# 启动应用
python app.py
```

### 6. 访问应用

打开浏览器访问：
```
http://localhost:5000
```

## 🔍 验证配置

### 测试Apple日历连接

```bash
python -c "
from caldav_client import AppleCalendarClient
import os
from dotenv import load_dotenv
load_dotenv()

client = AppleCalendarClient(
    os.getenv('CALDAV_SERVER_URL'),
    os.getenv('APPLE_CALENDAR_USERNAME'),
    os.getenv('APPLE_CALENDAR_PASSWORD')
)
print('✅ Apple日历连接成功')
print('可用日历:', client.get_calendars())
"
```

### 测试DeepSeek API

```bash
python -c "
from deepseek_parser import DeepSeekCalendarParser
import os
from dotenv import load_dotenv
load_dotenv()

parser = DeepSeekCalendarParser()
result = parser.parse_command('测试连接')
print('✅ DeepSeek API连接成功')
print('解析结果:', result)
"
```

## ❗ 常见问题

### Apple日历连接失败
- 检查Apple ID和密码是否正确
- 确认使用了应用专用密码，不是Apple ID密码
- 检查网络连接

### DeepSeek API错误
- 检查API密钥是否正确
- 确认API密钥有足够的额度
- 检查网络连接

### 环境变量不生效
- 确认 `.env` 文件在项目根目录
- 确认文件名是 `.env` 不是 `.env.example`
- 重启应用使环境变量生效

## 🎯 快速测试

配置完成后，运行以下命令测试整个系统：

```bash
source venv/bin/activate
python app.py
```

然后在浏览器访问 `http://localhost:5000`，尝试输入：
- "查看今天的日程"
- "创建明天下午3点的测试会议"

如果看到响应，说明配置成功！