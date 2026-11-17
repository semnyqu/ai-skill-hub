# FSD Git 仓库元数据规范

FSD 顶部 YAML 使用“主仓兼容字段 + 多仓明细”结构：

```yaml
branch: release/V10.1.4
priority: 中
project:
  id: sfxg
  repository: esg-sasp-app-rn
repositories:
  - id: esg-sasp-app-rn
    branch: release/V10.1.4
    primary: true
  - id: esg-sasp-app-rn-android
    branch: release/V10.1.4
```

## 字段口径

| 字段 | 口径 |
|---|---|
| `branch` | 主仓目标分支，为兼容既有消费者保留 |
| `priority` | 需求优先级，使用 `高`、`中`、`低`；PRD 未给出时询问用户 |
| `project.id` | 业务项目 ID，不等同于仓库名；无法从用户输入或项目配置确认时必须询问 |
| `project.repository` | 主仓仓库 ID，必须等于唯一 `primary: true` 项的 `id` |
| `repositories[].id` | Git 远程仓库名，来自 `origin` URL 最后一个路径段并去掉 `.git` |
| `repositories[].branch` | 该仓库实际用于代码探索和开发的目标分支 |
| `repositories[].primary` | 仅主仓填写 `true`；整份 FSD 必须且只能有一个主仓 |

## 一致性约束

1. `repositories` 至少一项，仓库 ID 不得重复。
2. 必须且只能有一个 `primary: true`。
3. `project.repository == repositories[primary].id`。
4. `branch == repositories[primary].branch`。
5. 单仓库也必须填写 `repositories`，不能退回只写顶层 `branch`。
6. 多仓库文件路径在 `summary.where` 和开发范围中使用 `{repository_id}:{relative_path}`，避免同名路径混淆。

## 采集方式

在每个仓库根目录执行：

```bash
git remote get-url origin
git branch --show-current
git rev-parse --show-toplevel
```

如果用户指定的是尚未切换的目标分支，以经过确认并实际 checkout 的分支为准。没有 `origin`、处于 detached HEAD、项目 ID 不明或主仓不唯一时，必须暂停并询问，不能猜测。
