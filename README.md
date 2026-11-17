# ai-skill-hub

统一管理本地 AI Skills 的私有仓库。V1.0 采用 **Private Git + Copy 分发 + Global 管理**，由仓库维护源文件，工具目录接收部署副本。

## 当前范围

- 纳管需求开发流程实际用到的 Skills：通用工作流、需求工程、准入检查和效果领域能力。来源目录仅用于首次导入，仓库副本为后续唯一维护源。
- 仓库新增 `requirement-development`（需求开发入口）编排 Skill，用于定向查找模块知识库、对照代码并按需求成熟度路由后续 Skills。
- 目标运行环境：TDDC / OpenCode 全局 Skills 目录。
- 已纳入 `prd-to-fsd`、`fsd-readiness-check` 和 `effect`。
- 本地清单和校验命令不访问网络，不修改工具目录。

## 目录

```text
skills/                 Skill 源文件及附属资源
registry/skills.json    Skill、版本、分类和目标目录清单
scripts/skill_hub.py    本地只读 list / validate 命令
docs/architecture-v1.md 架构边界与操作约定
```

## 使用

```sh
python3 scripts/skill_hub.py list
python3 scripts/skill_hub.py validate
```

使用时以 **`需求开发`** 作为入口关键词，例如 `需求开发：请根据 docs/PRD.md 生成 FSD`。入口会先识别需求模块，检索相关知识库并核对代码，再根据需求是否模糊、是否已有 PRD、当前是否要实施或排障选择下一项 Skill。规则见 [入口 Skill](skills/requirement-development/SKILL.md)。

当前纳管 Skill 的源文件只在 `skills/` 下维护。分发到 `~/.agents/skills` 或 `~/.config/opencode/skills` 需由操作者手动执行；复制前先比较目标内容，发现差异时先人工处理，不要静默覆盖。仓库不执行安装、删除、自动同步、提交或拉取。
