# 贡献指南

感谢您对AI Calendar Agent项目的关注！我们欢迎各种形式的贡献。

## 🚀 如何贡献

### 报告问题
- 使用GitHub Issues报告bug或提出功能建议
- 在报告前请先搜索是否已有类似问题
- 提供详细的复现步骤和环境信息

### 提交代码
1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 开发环境设置

1. 克隆仓库
```bash
git clone https://github.com/your-username/Calendar-Agent.git
cd Calendar-Agent
```

2. 设置虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入您的配置
```

### 代码规范

- 遵循PEP 8代码风格
- 使用有意义的变量名和函数名
- 添加必要的注释和文档
- 确保代码通过基本测试

### 测试

在提交代码前，请运行以下测试：

```bash
# 测试NLP解析
python test_agent.py

# 检查环境配置
python check_env.py

# 测试DeepSeek解析
python deepseek_parser.py
```

## 📋 开发计划

### 第一阶段 (已完成)
- [x] CalDAV客户端实现
- [x] DeepSeek API集成
- [x] Web界面开发

### 第二阶段 (进行中)
- [ ] 冲突检测和智能建议
- [ ] 重复事件支持
- [ ] 多日历管理

### 第三阶段 (规划中)
- [ ] 微信集成
- [ ] iMessage集成
- [ ] 语音交互

## 🤝 行为准则

我们致力于营造一个开放、友好的社区环境。请遵守以下行为准则：

- 尊重他人观点和经验
- 建设性批评，避免人身攻击
- 帮助新成员融入社区
- 保持专业和礼貌

## 📄 许可证

通过贡献代码，您同意您的贡献将遵循项目的MIT许可证。

感谢您的贡献！🎉