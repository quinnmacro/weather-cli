# AICS Hook 自动启用指南

## 🎯 目标
实现"一个项目一旦有了`.claude`目录，就自动启用AICS对话保存系统"

## ✅ 已完成的功能

### 1. 智能自动启用
AICS Hook现在可以自动检测项目目录：
- **有`.claude`目录** → 自动启用AICS
- **无`.claude`目录** → 自动禁用AICS
- **环境变量优先** → `AICS_HOOK_ENABLED=true/false` 覆盖自动检测

### 2. 调试输出
设置 `AICS_HOOK_DEBUG=true` 可以看到检测日志：
```
[AICS Hook] 2026-04-12 12:37:12 - 检测到.claude目录，自动启用: /path/to/project/.claude
[AICS Hook] 2026-04-12 12:37:12 - 未检测到.claude目录，禁用: /path/to/project
```

## 🚀 快速设置

### 步骤1: 安装AICS包
```bash
cd ~/Code/aics
pip install -e .
```

### 步骤2: 启用全局Hook配置
```bash
# 如果还没有hooks.json，从示例复制
cp ~/.claude/hooks-aics.json ~/.claude/hooks.json

# 或者直接创建
cat > ~/.claude/hooks.json << 'EOF'
{
  "description": "AICS Conversation Persistence Hooks",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"${CLAUDE_CWD}\" && python -m aics.hooks.session_start",
            "timeout": 30
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "cd \"${CLAUDE_CWD}\" && python -m aics.hooks.user_message \"${USER_PROMPT}\"",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "cd \"${CLAUDE_CWD}\" && python -m aics.hooks.ai_response",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "cd \"${CLAUDE_CWD}\" && python -m aics.hooks.session_end",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
EOF
```

### 步骤3: 在项目中启用AICS
```bash
# 进入你的项目目录
cd /path/to/your/project

# 创建.claude目录（空目录即可）
mkdir .claude

# 可选：添加项目特定配置
echo '{"storage_type": "markdown"}' > .claude/aics-config.json
```

### 步骤4: 开始使用
```bash
# 在项目目录中启动Claude Code
# 所有对话将自动保存到 .aics/ 目录
```

## 📁 目录结构示例

```
my-project/
├── .claude/          # 启用AICS的标志目录
├── .aics/            # AICS自动创建的存储目录
│   ├── conversations.db    # SQLite数据库
│   └── buffer/            # 临时缓冲区
├── src/              # 项目源代码
├── README.md         # 项目文档
└── pyproject.toml    # Python项目配置
```

## ⚙️ 配置选项

### 环境变量（优先级最高）
```bash
# 强制启用/禁用（覆盖自动检测）
export AICS_HOOK_ENABLED=true

# 调试模式
export AICS_HOOK_DEBUG=true

# 存储类型：sqlite, markdown, hybrid, auto
export AICS_STORAGE_TYPE=markdown

# 自动保存
export AICS_AUTO_SAVE=true

# 项目检测
export AICS_PROJECT_DETECTION=true
```

### 项目级配置（未来计划）
在 `.claude/aics-config.json` 中：
```json
{
  "storage_type": "markdown",
  "auto_save": true,
  "debug": false
}
```

## 🔧 验证设置

### 方法1: 手动测试
```bash
# 在项目目录中运行
cd /path/to/your/project
mkdir -p .claude

# 设置环境变量
export CLAUDE_CWD=$(pwd)
export CLAUDE_SESSION_ID=test-session
export AICS_HOOK_DEBUG=true

# 测试session_start hook
python -m aics.hooks.session_start

# 应该看到类似输出：
# [AICS Hook] ... - 检测到.claude目录，自动启用: ...
# [AICS Hook] ... - 会话开始: test-session
```

### 方法2: 使用测试脚本
```bash
cd /tmp/weather-cli
python test_aics_boundaries.py
```

## 🎪 使用场景

### 场景1: 新项目快速启用
```bash
# 1. 创建新项目
mkdir my-new-project
cd my-new-project

# 2. 启用AICS
mkdir .claude

# 3. 开始开发对话
# 所有对话自动保存
```

### 场景2: 现有项目添加AICS
```bash
# 1. 进入现有项目
cd existing-project

# 2. 添加.claude目录
mkdir .claude

# 3. 继续开发
# 从现在开始的对话都会被保存
```

### 场景3: 临时禁用AICS
```bash
# 方法1: 删除.claude目录
rm -rf .claude

# 方法2: 使用环境变量（优先级更高）
export AICS_HOOK_ENABLED=false
```

### 场景4: 不同项目不同配置
```bash
# 项目A: 使用Markdown存储
cd project-a
mkdir .claude
export AICS_STORAGE_TYPE=markdown

# 项目B: 使用SQLite存储
cd ../project-b
mkdir .claude
export AICS_STORAGE_TYPE=sqlite
```

## 🐛 故障排除

### 问题1: AICS没有启用
**检查步骤:**
1. 确认有 `.claude` 目录
2. 检查环境变量 `AICS_HOOK_ENABLED` 是否设置为 `false`
3. 查看调试输出: `export AICS_HOOK_DEBUG=true`

### 问题2: 对话没有保存
**检查步骤:**
1. 确认 `~/.claude/hooks.json` 存在且正确
2. 检查 `.aics/` 目录是否创建
3. 查看hook日志: `export AICS_HOOK_DEBUG=true`

### 问题3: 存储类型不匹配
**解决方案:**
```bash
# 清理旧存储
rm -rf .aics/

# 设置新存储类型
export AICS_STORAGE_TYPE=markdown

# 重新开始会话
```

## 📈 高级用法

### 1. 批量启用多个项目
```bash
# 为所有Git项目启用AICS
find ~/Code -name ".git" -type d | while read gitdir; do
    project_dir=$(dirname "$gitdir")
    mkdir -p "$project_dir/.claude"
    echo "Enabled AICS for $project_dir"
done
```

### 2. 项目特定配置脚本
```bash
# 在.claude目录中创建setup.sh
cat > .claude/setup.sh << 'EOF'
#!/bin/bash
# 项目特定的AICS配置
export AICS_STORAGE_TYPE=hybrid
export AICS_HOOK_DEBUG=false
EOF
```

### 3. 监控AICS状态
```bash
# 查看当前项目的AICS状态
python -c "
import os
from pathlib import Path

cwd = os.environ.get('CLAUDE_CWD', '.')
has_claude = (Path(cwd) / '.claude').exists()
enabled = os.environ.get('AICS_HOOK_ENABLED')

print(f'项目: {cwd}')
print(f'有.claude目录: {has_claude}')
print(f'AICS_HOOK_ENABLED: {enabled}')
print(f'AICS状态: {'启用' if (enabled == 'true' or (enabled is None and has_claude)) else '禁用'}')
"
```

## 🔮 未来增强计划

### 1. 项目级配置文件
```json
// .claude/aics.json
{
  "enabled": true,
  "storage": {
    "type": "hybrid",
    "sqlite_path": ".aics/conversations.db",
    "markdown_dir": ".aics/conversations"
  },
  "features": {
    "auto_tagging": true,
    "semantic_search": false,
    "sync_enabled": true
  }
}
```

### 2. 智能项目检测
- Git仓库自动启用
- Python/Node.js项目自动启用
- 配置文件白名单/黑名单

### 3. 一键安装脚本
```bash
# 安装AICS并配置全局hooks
curl -s https://aics.example.com/install.sh | bash
```

## 🎉 现在就开始吧！

### 最简单的启用方式:
```bash
# 1. 确保AICS已安装
cd ~/Code/aics && pip install -e .

# 2. 确保全局hooks配置
cp ~/.claude/hooks-aics.json ~/.claude/hooks.json

# 3. 在任何项目中创建.claude目录
cd /path/to/your/project
mkdir .claude

# 4. 开始使用Claude Code！
# 对话将自动保存到 .aics/ 目录
```

### 验证是否工作:
1. 在项目中启动Claude Code
2. 进行一些对话
3. 检查是否生成 `.aics/` 目录
4. 查看保存的对话

**恭喜！你现在拥有了智能的、项目感知的对话持久化系统！** 🚀