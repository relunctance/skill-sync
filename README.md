# skill-sync

> 同步 relunctance skills 到本地 Hermes/OpenClaw 工具链

将 `~/repos/` 下的 skill 仓库同步到各平台的 skills 目录，同时支持安装禁止瞎编规则到 SOUL.md。

## 安装

```bash
git clone https://github.com/relunctance/skill-sync.git ~/repos/skill-sync
```

## 使用方法

```bash
# 同步所有 skills
python3 ~/repos/skill-sync/scripts/sync-hermes-skills.py

# 同步指定 skill
python3 ~/repos/skill-sync/scripts/sync-hermes-skills.py target-skill honesty-skill

# 预览模式（不执行）
python3 ~/repos/skill-sync/scripts/sync-hermes-skills.py --dry-run

# 安装禁止瞎编规则到 SOUL.md
python3 ~/repos/skill-sync/scripts/sync-hermes-skills.py install-honesty
```

## 功能

| 命令 | 说明 |
|------|------|
| 无参数 | 同步所有 skills（按 SKILLS_TO_SYNC 列表） |
| `skill-name ...` | 仅同步指定的 skill |
| `--dry-run` | 预览将要执行的操作，不实际执行 |
| `install-honesty` | 将禁止瞎编规则写入当前平台的 SOUL.md |

## 同步的 skills

- base-skill
- capability-evolver-skill
- darwin-skill
- dir-skill
- find-skills
- git-standards-skill
- honesty-skill
- readme-skill
- role-build-skill
- skill-created
- SkillForge
- summarize-skill
- target-skill
- task-split-skill
- ubuntu-chinese-ime-skill
- ubuntu-chromium-setup-skill

## 路径说明

| 组件 | 路径 |
|------|------|
| repos 目录 | `~/repos/` |
| Hermes skills | `~/.hermes/skills/` |
| Hermes SOUL | `~/.hermes/profiles/<profile>/SOUL.md` |
| OpenClaw SOUL | `~/.openclaw/workspace/SOUL.md` |

> 注意：脚本内部会根据 WSL Hermes profile 环境自动检测实际路径。
