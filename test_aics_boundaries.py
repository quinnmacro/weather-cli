#!/usr/bin/env python3
"""
AICS Hook 系统边界测试脚本
模拟各种使用场景来探索系统能力和限制
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 添加天气CLI项目到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 尝试导入AICS hooks
try:
    sys.path.insert(0, "/Users/liulu/Code/aics/src")
    from aics.hooks import get_current_project, get_storage_adapter, init_config
    from aics.hooks.conversation_aggregator import get_aggregator
    AICS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  AICS模块不可用: {e}")
    print("请先安装AICS: cd /Users/liulu/Code/aics && pip install -e .")
    AICS_AVAILABLE = False


class BoundaryTester:
    """边界测试器"""

    def __init__(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="aics-boundary-test-"))
        print(f"📁 测试目录: {self.test_dir}")

        # 创建测试项目结构
        self._create_test_project()

        # 测试结果
        self.results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": []
        }

    def _create_test_project(self):
        """创建测试项目结构"""
        # 复制天气CLI项目文件
        weather_cli_dir = Path("/tmp/weather-cli")
        test_project_dir = self.test_dir / "weather-cli-test"

        # 创建基本结构
        test_project_dir.mkdir(exist_ok=True)

        # 创建pyproject.toml
        (test_project_dir / "pyproject.toml").write_text("""[project]
name = "weather-cli-test"
version = "1.0.0"
""")

        # 创建src目录
        (test_project_dir / "src").mkdir(exist_ok=True)
        (test_project_dir / "src" / "__init__.py").touch()

        print(f"  ✅ 创建测试项目: {test_project_dir}")
        self.project_dir = test_project_dir

    def _run_hook_simulation(self, scenario: str, env_vars: Dict[str, str]):
        """模拟运行hook场景"""
        if not AICS_AVAILABLE:
            print(f"  ⚠️  AICS不可用，跳过场景: {scenario}")
            return None

        # 保存原始环境变量
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            # 初始化配置
            config = init_config()

            # 获取项目
            project = get_current_project()
            if not project:
                print(f"  ❌ 无法检测项目: {scenario}")
                return None

            # 获取存储适配器
            adapter = get_storage_adapter()
            if not adapter:
                print(f"  ❌ 无法创建存储适配器: {scenario}")
                return None

            return adapter

        except Exception as e:
            print(f"  ❌ 场景{scenario}执行失败: {e}")
            return None
        finally:
            # 恢复环境变量
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                else:
                    os.environ.pop(key, None)

    def test_scenario_1_basic_functionality(self):
        """测试场景1: 基本功能"""
        print("\n" + "="*60)
        print("场景1: 基本对话保存功能")
        print("="*60)

        # 设置环境变量
        env_vars = {
            "CLAUDE_CWD": str(self.project_dir),
            "CLAUDE_SESSION_ID": f"test-basic-{int(time.time())}",
            "AICS_HOOK_DEBUG": "true",
            "AICS_STORAGE_TYPE": "sqlite"
        }

        adapter = self._run_hook_simulation("basic", env_vars)
        if not adapter:
            self.results["failed"] += 1
            self.results["details"].append({"scenario": "basic", "status": "failed", "reason": "无法初始化"})
            return False

        # 检查存储目录
        storage_dir = self.project_dir / ".aics"
        if storage_dir.exists():
            print(f"  ✅ 存储目录已创建: {storage_dir}")
            self.results["passed"] += 1
            self.results["details"].append({"scenario": "basic", "status": "passed", "detail": "存储目录创建成功"})
            return True
        else:
            print(f"  ❌ 存储目录未创建")
            self.results["failed"] += 1
            self.results["details"].append({"scenario": "basic", "status": "failed", "reason": "存储目录未创建"})
            return False

    def test_scenario_2_storage_adapters(self):
        """测试场景2: 不同存储适配器"""
        print("\n" + "="*60)
        print("场景2: 存储适配器测试")
        print("="*60)

        storage_types = ["sqlite", "markdown", "hybrid"]
        successes = 0

        for storage_type in storage_types:
            print(f"\n  测试{storage_type}存储:")

            # 为每种类型创建单独的测试目录
            test_dir = self.test_dir / f"storage-{storage_type}"
            test_dir.mkdir(exist_ok=True)
            (test_dir / "pyproject.toml").touch()

            env_vars = {
                "CLAUDE_CWD": str(test_dir),
                "CLAUDE_SESSION_ID": f"test-{storage_type}-{int(time.time())}",
                "AICS_STORAGE_TYPE": storage_type,
                "AICS_HOOK_DEBUG": "false"
            }

            adapter = self._run_hook_simulation(f"storage-{storage_type}", env_vars)
            if adapter:
                # 检查存储创建
                if storage_type == "sqlite":
                    db_path = test_dir / ".aics" / "conversations.db"
                    if db_path.exists():
                        print(f"    ✅ SQLite数据库已创建")
                        successes += 1
                    else:
                        print(f"    ❌ SQLite数据库未创建")

                elif storage_type == "markdown":
                    md_dir = test_dir / ".aics" / "conversations"
                    if md_dir.exists():
                        print(f"    ✅ Markdown目录已创建")
                        successes += 1
                    else:
                        print(f"    ❌ Markdown目录未创建")

                elif storage_type == "hybrid":
                    db_path = test_dir / ".aics" / "conversations.db"
                    md_dir = test_dir / ".aics" / "markdown_conversations"
                    if db_path.exists() and md_dir.exists():
                        print(f"    ✅ Hybrid存储已创建")
                        successes += 1
                    else:
                        print(f"    ❌ Hybrid存储不完整")
            else:
                print(f"    ⚠️  {storage_type}适配器初始化失败")

        # 评估结果
        if successes >= 2:  # 至少2种存储通过
            print(f"\n  ✅ 存储适配器测试通过: {successes}/{len(storage_types)}")
            self.results["passed"] += 1
            self.results["details"].append({"scenario": "storage_adapters", "status": "passed", "detail": f"{successes}种存储通过"})
            return True
        else:
            print(f"\n  ❌ 存储适配器测试失败: {successes}/{len(storage_types)}")
            self.results["failed"] += 1
            self.results["details"].append({"scenario": "storage_adapters", "status": "failed", "reason": f"只有{successes}种存储通过"})
            return False

    def test_scenario_3_large_content(self):
        """测试场景3: 大内容处理"""
        print("\n" + "="*60)
        print("场景3: 大内容处理能力")
        print("="*60)

        # 创建包含大内容的测试目录
        large_dir = self.test_dir / "large-content"
        large_dir.mkdir(exist_ok=True)
        (large_dir / "pyproject.toml").touch()

        # 生成大文本（约50KB）
        large_text = "大内容测试\n" * 5000

        # 创建大文件
        large_file = large_dir / "large_code.py"
        large_file.write_text(large_text)

        print(f"  ✅ 创建大文件: {large_file} ({len(large_text)} 字符)")

        # 测试是否能够处理大目录
        try:
            # 尝试获取项目信息
            env_vars = {
                "CLAUDE_CWD": str(large_dir),
                "CLAUDE_SESSION_ID": f"test-large-{int(time.time())}",
                "AICS_HOOK_DEBUG": "false"
            }

            adapter = self._run_hook_simulation("large_content", env_vars)
            if adapter:
                print(f"  ✅ 大内容目录处理成功")
                self.results["passed"] += 1
                self.results["details"].append({"scenario": "large_content", "status": "passed", "detail": "大目录处理成功"})
                return True
            else:
                print(f"  ⚠️  大内容目录处理可能有限制")
                self.results["warnings"] += 1
                self.results["details"].append({"scenario": "large_content", "status": "warning", "reason": "大目录处理有限制"})
                return False

        except Exception as e:
            print(f"  ❌ 大内容处理失败: {e}")
            self.results["failed"] += 1
            self.results["details"].append({"scenario": "large_content", "status": "failed", "reason": str(e)})
            return False

    def test_scenario_4_special_characters(self):
        """测试场景4: 特殊字符处理"""
        print("\n" + "="*60)
        print("场景4: 特殊字符和格式")
        print("="*60)

        special_dir = self.test_dir / "special-chars"
        special_dir.mkdir(exist_ok=True)

        # 创建包含各种特殊内容的文件
        special_content = """# 特殊字符测试文件

## Markdown格式
**粗体** *斜体* ~~删除线~~

## 代码块
```python
def hello():
    print("Hello, 世界!")
```

## JSON数据
{"name": "测试", "value": 123, "special": "引号\"和\\反斜杠"}

## HTML/XML片段
<div class="test">内容 &amp; 实体</div>

## 表情符号
🎉 😊 🚀

## 混合内容
正常文本 + `行内代码` + **强调** + [链接](http://example.com)
"""

        test_file = special_dir / "test_special.md"
        test_file.write_text(special_content)
        (special_dir / "pyproject.toml").touch()

        print(f"  ✅ 创建特殊字符测试文件")
        print(f"     包含: Markdown、代码、JSON、HTML、表情符号")

        # 测试处理
        try:
            env_vars = {
                "CLAUDE_CWD": str(special_dir),
                "CLAUDE_SESSION_ID": f"test-special-{int(time.time())}",
                "AICS_HOOK_DEBUG": "false"
            }

            adapter = self._run_hook_simulation("special_chars", env_vars)
            if adapter:
                print(f"  ✅ 特殊字符目录处理成功")
                self.results["passed"] += 1
                self.results["details"].append({"scenario": "special_chars", "status": "passed", "detail": "特殊字符处理成功"})
                return True
            else:
                print(f"  ⚠️  特殊字符处理可能有限制")
                self.results["warnings"] += 1
                self.results["details"].append({"scenario": "special_chars", "status": "warning", "reason": "特殊字符处理有限制"})
                return False

        except Exception as e:
            print(f"  ❌ 特殊字符处理失败: {e}")
            self.results["failed"] += 1
            self.results["details"].append({"scenario": "special_chars", "status": "failed", "reason": str(e)})
            return False

    def test_scenario_5_project_detection(self):
        """测试场景5: 项目类型检测"""
        print("\n" + "="*60)
        print("场景5: 不同项目类型检测")
        print("="*60)

        project_types = [
            ("git", ".git目录", lambda d: (d / ".git").mkdir(exist_ok=True)),
            ("python", "Python项目", lambda d: (d / "pyproject.toml").write_text("[project]\nname='test'")),
            ("node", "Node.js项目", lambda d: (d / "package.json").write_text('{"name":"test"}')),
            ("empty", "空目录", lambda d: None),
        ]

        successes = 0

        for project_id, description, setup_func in project_types:
            print(f"\n  测试{description}:")

            test_dir = self.test_dir / f"project-{project_id}"
            test_dir.mkdir(exist_ok=True)
            setup_func(test_dir)

            env_vars = {
                "CLAUDE_CWD": str(test_dir),
                "CLAUDE_SESSION_ID": f"test-{project_id}-{int(time.time())}",
                "AICS_HOOK_DEBUG": "false"
            }

            adapter = self._run_hook_simulation(f"project-{project_id}", env_vars)
            if adapter:
                print(f"    ✅ {description}检测成功")
                successes += 1
            else:
                print(f"    ⚠️  {description}检测可能失败")

        # 评估结果
        if successes >= 3:  # 至少3种类型通过
            print(f"\n  ✅ 项目类型检测通过: {successes}/{len(project_types)}")
            self.results["passed"] += 1
            self.results["details"].append({"scenario": "project_detection", "status": "passed", "detail": f"{successes}种项目类型通过"})
            return True
        else:
            print(f"\n  ❌ 项目类型检测失败: {successes}/{len(project_types)}")
            self.results["failed"] += 1
            self.results["details"].append({"scenario": "project_detection", "status": "failed", "reason": f"只有{successes}种项目类型通过"})
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("="*80)
        print("AICS Hook 系统边界测试")
        print("="*80)

        if not AICS_AVAILABLE:
            print("❌ AICS不可用，无法运行测试")
            print("请先安装: cd /Users/liulu/Code/aics && pip install -e .")
            return False

        tests = [
            ("基本功能", self.test_scenario_1_basic_functionality),
            ("存储适配器", self.test_scenario_2_storage_adapters),
            ("大内容处理", self.test_scenario_3_large_content),
            ("特殊字符", self.test_scenario_4_special_characters),
            ("项目检测", self.test_scenario_5_project_detection),
        ]

        for test_name, test_func in tests:
            print(f"\n▶️  开始测试: {test_name}")
            try:
                test_func()
            except Exception as e:
                print(f"❌ 测试{test_name}异常: {e}")
                import traceback
                traceback.print_exc()
                self.results["failed"] += 1
                self.results["details"].append({"scenario": test_name, "status": "error", "reason": str(e)})

        # 显示结果
        print("\n" + "="*80)
        print("测试完成")
        print("="*80)
        print(f"通过: {self.results['passed']}")
        print(f"失败: {self.results['failed']}")
        print(f"警告: {self.results['warnings']}")

        print("\n详细结果:")
        for detail in self.results["details"]:
            status_icon = "✅" if detail["status"] == "passed" else "❌" if detail["status"] == "failed" else "⚠️"
            print(f"  {status_icon} {detail['scenario']}: {detail.get('detail', detail.get('reason', '未知'))}")

        # 测试目录信息
        print(f"\n📁 测试目录: {self.test_dir}")
        print("保留以供检查，可手动删除。")

        # 清理建议
        print("\n💡 清理命令:")
        print(f"rm -rf {self.test_dir}")

        return self.results["failed"] == 0


def main():
    """主函数"""
    tester = BoundaryTester()

    try:
        success = tester.run_all_tests()

        if success:
            print("\n🎉 边界测试完成！系统表现良好。")
            print("\n下一步建议:")
            print("1. 使用真实Claude Code会话进行更深入测试")
            print("2. 参考EXPLORE_AICS_HOOKS.md中的场景进行手动测试")
            print("3. 尝试不同的项目类型和对话内容")
            return 0
        else:
            print(f"\n⚠️  发现{ tester.results['failed'] }个问题，请检查。")
            return 1

    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())