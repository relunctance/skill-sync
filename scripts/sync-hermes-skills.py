#!/usr/bin/env python3
"""
sync-hermes-skills — 同步 relunctance skills 到 hermes/skills/

用法：
  python3 sync-hermes-skills.py              # 同步所有 skills
  python3 sync-hermes-skills.py --dry-run   # 仅预览，不执行
  python3 sync-hermes-skills.py target-skill # 仅同步指定 skill
  python3 sync-hermes-skills.py install-honesty  # 安装 honesty 到 SOUL.md
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 跨平台路径策略：
# - WSL Hermes profile 下 Path.home() 指向 ~/.hermes/profiles/<profile>/home/
# - 直接用 Path.home() 让系统自动处理 WSL profile 情况
HOME_BASE = str(Path.home())

# relunctance 的 repos 统一放在 <home>/repos/
REPOS_DIR = Path(HOME_BASE) / "repos"
# hermes skills 统一放在 <home>/.hermes/skills/
# 在 Hermes profile 环境下，Path.home() 已经指向 profile home，所以直接用
HERMES_SKILLS = Path(HOME_BASE) / ".hermes" / "skills"

# relunctance 管理的 skill 仓库列表（从 repos 扫描）
SKILLS_TO_SYNC = [
    "base-skill",
    "capability-evolver-skill",
    "darwin-skill",
    "dir-skill",
    "find-skills",
    "git-standards-skill",
    "github-push-solver-skill",
    "honesty-skill",
    "network-proxy-guide-skill",
    "readme-skill",
    "role-build-skill",
    "skill-created",
    "skillforge",
    "summarize-skill",
    "target-skill",
    "task-split-skill",
    "ubuntu-chinese-ime-skill",
    "ubuntu-chromium-setup-skill",
]

# ─── SOUL.md 禁止瞎编核心规则 ────────────────────────────────────
# 安装 honesty-skill 时写入 SOUL.md，覆盖已有内容

SOUL_HONESTY_BLOCK = """# 禁止瞎编（honesty-skill 核心准则）

## 核心准则

- **不知道**：直接说「我不清楚」，绝不捏造角色/组织/工作流/路径/配置
- **不瞎编**：涉及身份/角色/组织/工作流时，必须先查证，不确定则说不知道
- **不臆测**：结论必须有依据，无依据不臆测，不打包票
- **标注前提**：不确定时主动标注前提、风险，不说「绝对/保证/100%」
- **编造禁止**：禁止编造事实/代码/参数/文档/出处/版本号/路径

## 自问清单（每次回答前）

在开口之前，问自己：
1. 我真的知道这个吗？
2. 我有没有查证过？
3. 如果我不确定，我是否说了「我不清楚，需要先确认」？

## 子 agent 委托约束

委托子 agent 时，必须在 context 中携带：
```
[强制约束] 禁止瞎编：不知道就说不知道，涉及未核实的信息必须标注前提。
```

---

"""

# ─── 工具函数 ───────────────────────────────────────────────────

def get_git_head(repo_path: Path) -> str:
    """获取 git commit short hash"""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "?"
    except Exception:
        return "?"


def get_remote(repo_path: Path) -> str:
    """获取 git remote URL"""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def sync_skill(skill_name: str, dry_run: bool = False) -> dict:
    """同步单个 skill，返回结果"""
    repo_dir = REPOS_DIR / skill_name
    hermes_dir = HERMES_SKILLS / skill_name

    result = {
        "name": skill_name,
        "status": "ok",
        "action": "unchanged",
        "repo_commit": "?",
        "hermes_commit": "?",
        "message": "",
    }

    if not repo_dir.exists():
        result["status"] = "skip"
        result["message"] = "repos 不存在"
        return result

    # 检查 git 状态
    result["repo_commit"] = get_git_head(repo_dir)
    result["remote"] = get_remote(repo_dir)

    if not result["remote"] or "github.com/relunctance" not in result["remote"]:
        result["status"] = "skip"
        result["message"] = "非 relunctance 仓库"
        return result

    # 如果 hermes 目录不存在，创建它
    if not hermes_dir.exists():
        if dry_run:
            result["action"] = "create (dry-run)"
            result["status"] = "pending"
        else:
            shutil.copytree(repo_dir, hermes_dir)
            result["action"] = "create"
            result["hermes_commit"] = get_git_head(hermes_dir)
            result["message"] = "新建"
    else:
        # 比较版本
        result["hermes_commit"] = get_git_head(hermes_dir)

        if result["repo_commit"] == result["hermes_commit"]:
            result["action"] = "unchanged"
        else:
            if dry_run:
                result["action"] = f"update {result['hermes_commit']}→{result['repo_commit']} (dry-run)"
                result["status"] = "pending"
            else:
                # 删除后重新复制（保留 .git 历史）
                shutil.rmtree(hermes_dir)
                shutil.copytree(repo_dir, hermes_dir)
                result["action"] = f"update {result['hermes_commit']}→{result['repo_commit']}"
                result["hermes_commit"] = result["repo_commit"]
                result["message"] = "已同步"

    return result


def get_openclaw_workspace_soul() -> Path | None:
    """
    从当前工作目录推断 OpenClaw workspace SOUL.md 路径。

    逻辑：
    - cwd 在 ~/.openclaw/workspace-{name}/ 下 → 返回该目录的 SOUL.md
    - cwd 在 ~/.openclaw/workspace-{name}/ 子目录下 → 向上查找 SOUL.md
    - 不在 openclaw 目录下 → 返回 None

    注意：WSL 下 Path.home() 可能指向 ~/.hermes/profiles/xxx/home/，
    因此 openclaw_base 用绝对路径 /home/gql/.openclaw/ 而非 Path.home()。
    """
    import os as _os

    cwd = Path.cwd()
    # WSL Hermes profile 环境下，HOME_BASE 是 /home/<user>
    openclaw_base = Path(HOME_BASE) / ".openclaw"

    # 向上遍历目录，查找 SOUL.md
    current = cwd.resolve()
    for parent in [current] + list(current.parents):
        # 检查这个目录下是否有 SOUL.md
        soul_path = parent / "SOUL.md"
        if soul_path.exists() and soul_path.is_file():
            return soul_path
        # 如果已经到 /home 或更上，停止
        if parent == Path("/home") or str(parent).startswith("/mnt"):
            break

    return None


def install_honesty(dry_run: bool = False) -> dict:
    """
    将禁止瞎编规则写入 SOUL.md。
    
    - Hermes: ~/.hermes/profiles/baijie/SOUL.md
    - OpenClaw: 从 cwd 推断 workspace 路径
    
    覆盖已有内容（用户确认）。
    """
    result = {
        "platform": "unknown",
        "soul_path": None,
        "action": "none",
        "message": "",
    }
    
    # 检测平台：优先检测 cwd 是否在 openclaw workspace 下
    import os as _os
    openclaw_soul = get_openclaw_workspace_soul()
    hermes_soul = Path(HOME_BASE).parent / "SOUL.md"

    # 优先用 cwd 检测到的（如果在 openclaw workspace 下）
    if openclaw_soul:
        result["platform"] = "openclaw"
        result["soul_path"] = str(openclaw_soul)
    elif hermes_soul.exists():
        result["platform"] = "hermes"
        result["soul_path"] = str(hermes_soul)
    
    if result["platform"] == "unknown":
        result["message"] = "无法检测平台（Hermes / OpenClaw），请确认工作目录"
        return result
    
    soul_path = Path(result["soul_path"])
    
    if dry_run:
        result["action"] = "would overwrite SOUL.md"
        result["message"] = f"[dry-run] {result['platform']}: {soul_path}\n\n内容预览：\n{SOUL_HONESTY_BLOCK}"
        return result
    
    # 写入（覆盖）
    try:
        with open(soul_path, "w", encoding="utf-8") as f:
            f.write(SOUL_HONESTY_BLOCK)
        result["action"] = "overwritten"
        result["message"] = f"✅ {result['platform']} SOUL.md 已写入禁止瞎编规则\n   路径: {soul_path}"
    except Exception as e:
        result["message"] = f"❌ 写入失败: {e}"
        result["action"] = "error"
    
    return result


# ─── 主入口 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="sync-hermes-skills: 同步 relunctance skills + 安装 honesty 到 SOUL.md"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    parser.add_argument("skills", nargs="*", default=[], help="指定要同步的 skill（默认全部）")
    args = parser.parse_args()

    # 检测是否是 install-honesty 命令
    if args.skills and args.skills[0] == "install-honesty":
        r = install_honesty(dry_run=args.dry_run)
        print(f"📦 install-honesty ({'dry-run' if args.dry_run else 'live'})")
        print(f"   平台: {r['platform']}")
        print(f"   路径: {r['soul_path']}")
        print(f"   动作: {r['action']}")
        print(f"   消息: {r['message']}")
        return

    skills = args.skills if args.skills else SKILLS_TO_SYNC

    print(f"{'🔍 [dry-run] ' if args.dry_run else '📦 '}{'同步' if not args.dry_run else '预览'} {len(skills)} 个 skills...")
    print()

    results = []
    for skill in skills:
        r = sync_skill(skill, dry_run=args.dry_run)
        results.append(r)

    # 输出结果表格
    print(f"{'action':<45} {'repo':<8} {'hermes':<8}  skill")
    print("-" * 80)

    changed = 0
    for r in results:
        action = r["action"]
        if r["status"] == "skip":
            continue
        if r["action"] != "unchanged":
            changed += 1
            print(f"✅ {action:<43} {r['repo_commit']:<8} {r['hermes_commit']:<8}  {r['name']}")
        else:
            print(f"   {action:<45} {r['repo_commit']:<8} {r['hermes_commit']:<8}  {r['name']}")

    print()
    if args.dry_run:
        if changed > 0:
            print(f"🔍 共 {changed} 个 skill 需要更新（dry-run，未执行）")
        else:
            print("✅ 所有 skills 已同步，无需更新")
    else:
        print(f"✅ 同步完成，{changed} 个 skill 已更新")


if __name__ == "__main__":
    main()
