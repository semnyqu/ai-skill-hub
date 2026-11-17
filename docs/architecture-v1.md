# 统一 Skill 架构 V1.0（本地实施）

## 已确认决策

| 维度 | 选择 |
| --- | --- |
| 仓库 | Private Git；本轮仅本地操作，不提交或拉取远端 |
| 分发 | Copy；部署副本与仓库源分离 |
| 管理范围 | Global |
| 首期适配 | TDDC / OpenCode |
| 纳管范围 | 需求开发入口涉及的 11 个 Skills |

## 职责边界

- `skills/` 是纳管 Skill 的唯一维护来源，完整保留每个目录内的 `SKILL.md`、references、scripts 等资源。
- `registry/skills.json` 记录版本、分类、来源、部署目标和暂缓来源。
- `scripts/skill_hub.py` 只提供本地清单与结构校验；不会改动目标目录。
- 目标工具负责发现和运行已复制的 Skill。

## 首期清单

`需求开发入口`、`brainstorming`、`prd-to-fsd`、`fsd-readiness-check`、`writing-plans`、`executing-plans`、`test-driven-development`、`systematic-debugging`、`verification-before-completion`、`using-superpowers`、`effect`。

版本 `1.0.0` 是本仓库首次纳管版本标记，不代表上游发布版本。之后按 Skill 独立升版并记录变更。

仓库另含 `requirement-development`（需求开发入口）编排 Skill。它先识别需求模块，定向检索项目知识库并对照代码证据，再将模糊需求路由到 brainstorming，将已有 PRD 路由到 prd-to-fsd 和 fsd-readiness-check，并按准入结果进入 writing-plans、实施、TDD、调试和交付验证。

## 手工分发约定

分发时逐个 Skill 比较仓库与目标目录。目标不存在时可由操作者复制；目标已存在且内容不同则停止该项并人工判断。不得在未经确认时覆盖目标文件。每次实际部署应记录版本、目标和时间，作为后续差异检查与回滚依据。

## 暂缓纳管

需求开发入口所需的 `prd-to-fsd`、`fsd-readiness-check` 已纳入；`effect` 作为独立领域 Skill 一并归档。

## 后续阶段

1. 逐项核对导入的 11 个 Skill 及其附属资源。
2. 定义部署快照格式及校验和。
3. 在安全策略确定后实现显式部署预览和回滚工具；部署写入必须明确指定目标，并拒绝静默覆盖。
4. 再评估 Codex、Claude Code、Cursor 等 Adapter。
