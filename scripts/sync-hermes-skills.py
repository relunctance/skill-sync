#!/usr/bin/env python3
"""
sync-hermes-skills — 同步 relunctance skills 到 hermes/skills/

用法：
  python3 sync-hermes-skills.py          # 同步所有 skills
  python3 sync-hermes-skills.py --dry-run # 仅预览，不执行
  python3 sync-hermes-skills.py target-skill  # 仅同步指定 skill
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERMES_SKILLS = Path.home() / ".hermes" / "skills"
REPOS_DIR = Path.home() / "repos"

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
    "ubuntu-chinese-ime-skill",
    "ubuntu-chromium-setup-skill",
]


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


def main():
    parser = argparse.ArgumentParser(description="同步 relunctance skills 到 hermes/skills/")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    parser.add_argument("skills", nargs="*", default=[], help="指定要同步的 skill（默认全部）")
    args = parser.parse_args()

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
