# FSD 后端范例：订单超时未支付自动取消

此范例展示后端模板各章节的填写口径。所有代码路径、接口字段、表结构均从实际工程代码中确认。

```yaml
name: 订单超时未支付自动取消
type: 已有功能迭代
domain: backend
branch: feature/order-timeout-cancel
fsd_version: v1.0
generated_at: 2026-06-20 16:00
priority: 中
project:
  id: order
  repository: order-service
repositories:
  - id: order-service
    branch: feature/order-timeout-cancel
    primary: true
  - id: inventory-service
    branch: feature/order-timeout-cancel
prd_version: 2026-06-18 初版

summary:
  what: 订单创建后 30 分钟未支付，自动取消订单并释放库存
  where:
    - order-service:src/main/java/.../OrderTimeoutTask.java
    - order-service:src/main/java/.../OrderService.java
    - inventory-service:src/main/java/.../InventoryService.java
  impact: order-service 新增定时任务、inventory-service 释放库存接口；下游通知中心需新增订单取消推送（已协同）

entry_points:
  - OrderTimeoutTask.scanAndCancel
  - OrderService.cancelByTimeout
  - InventoryService.releaseByOrder

dependencies:
  apis_provided:
    - POST /internal/inventory/release
  apis_consumed:
    - POST /notification/push
  storage:
    - mysql:t_order
    - mysql:t_inventory_lock
    - redis:order:timeout:set
    - mq:order.cancelled
  modules:
    - order-service.timeout
    - inventory-service.lock

test_scope:
  - unit
  - integration

is_new_feature: false
```

> 推导过程注释：
> - `OrderTimeoutTask.scanAndCancel`：搜索 `@Scheduled` + `order` → 找到定时任务类
> - `t_order` 表结构：从 `entity/OrderEntity.java` 反查
> - `order:timeout:set` Redis key：搜索 `RedisKey.ORDER_TIMEOUT` 常量定义

---

## 1. 需求背景

### 1.1 改造前 vs 改造后

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| 调用方行为 | 业务运营每日手动取消超时订单 | 系统自动取消，运营无需介入 |
| 系统行为 | 无超时机制；订单一直保持"待支付"状态占用库存 | 定时任务每分钟扫描，超过 30 分钟未支付的订单自动取消，并释放库存 |
| 数据/业务结果 | 库存被无效占用，影响商品可售卖性 | 库存及时释放，提升商品周转率；运营人力释放 |

### 1.2 涉及业务子模块

订单域 → order-service → 订单超时取消子模块（含 inventory-service 库存释放协同）

### 1.3 上下游调用关系

```text
定时任务（每分钟）─→ [order-service·OrderTimeoutTask] ─→ [order-service·OrderService.cancelByTimeout]
                                                          ├→ MySQL t_order（更新状态）
                                                          ├→ Redis order:timeout:set（移除）
                                                          ├→ inventory-service /internal/inventory/release
                                                          ├→ MQ order.cancelled（发布事件）
                                                          └→ notification-service /notification/push（通过 MQ 异步消费）
```

---

## 2. 开发范围

| 业务模块 | 核心代码入口 | 文件路径 | 服务边界 |
|---|---|---|---|
| `订单/超时取消/扫描` | `OrderTimeoutTask.scanAndCancel` | `order-service:src/main/java/com/xxx/order/task/OrderTimeoutTask.java:45` | 本服务内 |
| `订单/超时取消/执行` | `OrderService.cancelByTimeout` | `order-service:src/main/java/com/xxx/order/service/OrderService.java:312` | 本服务内 |
| `库存/释放/接口` | `InventoryController.release` | `inventory-service:src/main/java/com/xxx/inventory/controller/InventoryController.java:89` | 跨服务 |

### 2.1 架构说明

订单超时扫描采用 `XXL-Job` 定时任务调度，每分钟执行一次，按订单创建时间倒序扫描。单批次处理 100 条，避免长事务。库存释放通过 RPC 调用 inventory-service，失败时降级到 MQ 异步重试。

### 2.2 调用方影响

| 调用方 | 影响类型 | 备注 |
|--------|----------|------|
| 前端/H5/小程序 | 需协同改造 | 订单详情页需展示"已超时自动取消"状态文案，已通知前端 |
| notification-service | 需协同 | 消费新的 `order.cancelled` 事件，已与对方对齐 |
| 数据中心 | 无影响 | 已通过现有订单状态变更事件订阅 |

---

## 3. 接口设计

### 3.1 接口变更概览

| 接口 | 变更类型 | 视角 | 说明 |
|------|----------|------|------|
| POST /internal/inventory/release | 新增接口 | 本服务消费 | 释放订单关联库存 |
| MQ topic `order.cancelled` | 新增字段 | 本服务发布 | 新增 `cancelReason: timeout` 字段 |

### 3.2 接口详情

#### 3.2.1 POST /internal/inventory/release

| 项目 | 内容 |
|---|---|
| 接口名称 | 释放订单关联库存 |
| 视角 | order-service 消费（inventory-service 提供） |
| 请求方式 | POST |
| 请求URL | `/internal/inventory/release` |
| 路由定义 | `inventory-service:InventoryController.java:89` |
| 业务入口方法 | `InventoryController.release` → `InventoryService.releaseByOrder` |

**请求结构：**

```jsonc
{
  "orderId": "string | 必需 | 长度 18 | 订单号",
  "reason": "string | 必需 | 枚举 [timeout, manual, refund] | 释放原因",
  "operatorId": "string | 可选 | 操作人 ID（自动任务为 system）"
}
```

**响应结构：**

```jsonc
{
  "code": "int | 0=成功，1001=订单不存在，1002=库存已释放，1003=系统异常",
  "msg": "string | 失败提示文案",
  "data": {
    "releasedSkus": "array | 释放的 SKU 列表，含 skuId 和数量"
  }
}
```

**字段校验规则**：

| 字段 | 校验 | 失败码 | 失败处理 |
|------|------|--------|----------|
| orderId | 长度 = 18 且只含数字 | 4001 | 返回参数错误 |
| reason | 必须在枚举内 | 4001 | 返回参数错误 |

**幂等性**：

| 项目 | 内容 |
|------|------|
| 是否幂等 | 是 |
| 幂等键 | `orderId + reason` |
| 实现方式 | `t_inventory_lock` 表 `release_status` 字段 + 唯一索引 `idx_order_release(order_id, release_status)` |
| 幂等窗口 | 永久（一旦释放不可重复） |

**限流策略**：

| 项目 | 内容 |
|------|------|
| 限流维度 | 接口级（内部接口，限定调用方为 order-service） |
| QPS 上限 | 500 |
| 超限处理 | 返回限流码 5001，order-service 端排队重试 |

### 3.3 数据层变更

#### 3.3.1 表结构变更

| 表名 | 变更类型 | 字段变更 | 索引变更 | 兼容性 |
|------|----------|----------|----------|--------|
| t_order | 新增字段 | `cancel_reason VARCHAR(32) DEFAULT NULL COMMENT '取消原因'` | 无 | 在线 DDL，向前兼容 |
| t_inventory_lock | 新增字段 | `release_status TINYINT DEFAULT 0 COMMENT '0:未释放 1:已释放'` | 新增 `idx_order_release(order_id, release_status)` | 在线 DDL，向前兼容 |

#### 3.3.2 数据迁移

无需迁移历史数据。改造前的旧订单不参与本次自动取消（按 `created_at >= 上线时间` 过滤）。

### 3.4 缓存与消息

| 类型 | 标识 | 变更 | 说明 |
|------|------|------|------|
| Redis 缓存 | `order:timeout:set` | 新增 | ZSet，score 为订单创建时间戳，member 为 orderId；订单创建时入集合，支付完成或取消时移除；TTL 1 小时（兜底清理） |
| MQ 消息 | `order.cancelled` | 修改 | 消息体新增 `cancelReason` 字段；生产方 order-service，消费方 notification-service、data-center；不需要重试（消费方自行保证幂等） |

### 3.5 核心逻辑

```text
1. 定时任务触发（每分钟）：
   - XXL-Job 调度 OrderTimeoutTask.scanAndCancel()

2. 扫描超时订单：
   - 从 Redis order:timeout:set 中取出 score < (now - 30min) 的 orderId 列表
   - 单批次最多取 100 条
   - 如果 Redis 不可用，降级查 MySQL（按 status=PENDING_PAY AND created_at < now-30min，limit 100）

3. 遍历处理每个 orderId：
   a. 开启事务：
      - 锁定订单（SELECT ... FOR UPDATE）
      - 二次校验状态（必须为 PENDING_PAY）
      - 更新 t_order 状态为 CANCELLED，cancel_reason = 'timeout'
   b. 提交事务

   c. 调用 inventory-service /internal/inventory/release：
      - 失败时记录到失败队列，发送到 MQ retry topic 异步重试

   d. 移除 Redis order:timeout:set 中的 orderId

   e. 发布 MQ 事件 order.cancelled，含 cancelReason: timeout

4. 任务结束：记录扫描数量、成功数量、失败数量到监控
```

### 3.6 注意事项

- **接口兼容性**：MQ `order.cancelled` 新增 `cancelReason` 字段，消费方按缺省值 `null` 兼容；已通知现有消费方
- **向后兼容**：`t_order.cancel_reason` 默认 NULL，旧订单不受影响
- **异常处理**：inventory 释放失败 → MQ 异步重试 3 次 → 仍失败则记录到 `t_order_cancel_fail` 表，由人工介入
- **性能影响**：新增定时任务每分钟 1 次，单批次 100 条，预计每分钟 QPS < 200；DB 单次扫描走 `idx_status_created(status, created_at)` 索引，走索引覆盖
- **事务边界**：订单状态变更 + cancel_reason 写入在一个事务内；库存释放在事务外（最终一致性 + MQ 重试保证）
- **代码与 PRD 差异**：PRD 称字段为 `cancelReasonCode`，代码实际为 `cancel_reason`，以代码为准

---

## 4. 需求功能点

| 功能点 ID | 变更类型 | 触发/前置条件 | 功能描述 | 输出/数据变更/事件 | 边界/并发/异常 |
|---|---|---|---|---|---|
| FP-001 | 新增 | XXL-Job 调度 OrderTimeoutTask 每分钟触发 | 扫描超时订单：从 Redis order:timeout:set 取 score < now-30min 的 orderId（最多 100 条）；Redis 不可用时降级查 MySQL | 返回待处理订单列表 | 单批次 ≤ 100；Redis 降级 MySQL 查询时走 `idx_status_created` 索引避免全表扫；**上线保障**：灰度 1 个分片 1 天观察后全量；监控指标：扫描数/成功数/失败数；告警：单批次失败率 > 5% |
| FP-002 | 新增 | 扫描到超时订单 | 遍历每条订单执行取消：开启事务 → 锁订单 → 二次校验状态 → 更新状态为 CANCELLED + cancel_reason='timeout' → 提交事务 | t_order 状态从 PENDING_PAY 变为 CANCELLED，cancel_reason 写入 'timeout' | 二次校验防并发（订单可能已被用户主动支付或取消）；事务超时 3s；DB 死锁重试 3 次 |
| FP-003 | 新增 | 订单状态成功更新为 CANCELLED | 调用 inventory-service `/internal/inventory/release` 释放库存；失败时发送到 MQ 重试 topic | inventory-service 释放对应 SKU 库存；成功后 t_inventory_lock.release_status = 1 | RPC 超时 1s，失败重试 3 次（指数退避）；仍失败则发 MQ；幂等键 orderId + reason 防重复释放 |
| FP-004 | 新增 | 订单取消完成（无论库存是否释放成功） | 发布 MQ 事件 order.cancelled，消息体含 orderId/cancelReason='timeout'/cancelTime；移除 Redis order:timeout:set 中对应 orderId | MQ topic order.cancelled 消息发出；Redis 集合中 orderId 被移除 | MQ 发送失败不影响主流程，记录失败日志；下游消费方自行保证幂等 |
| FP-005 | 修改 | 用户主动支付完成或取消订单 | 在原有支付完成/取消逻辑后，新增从 Redis order:timeout:set 移除 orderId 的操作 | Redis 集合中 orderId 被移除，避免被超时任务误处理 | 移除失败不影响主流程，超时任务会通过二次校验状态兜底 |

---

## 5. 验收标准

| 用例 ID | 场景 | Given | When | Then | 数据验证路径 |
|---|---|---|---|---|---|
| AC-001 | 正常超时自动取消 | 订单 O001 创建于 31 分钟前，状态为 PENDING_PAY，Redis 集合中存在 | OrderTimeoutTask 触发执行 | 订单状态变为 CANCELLED，cancel_reason='timeout'；库存被释放；MQ 事件发出；Redis 集合中移除 | 调用 触发任务 OrderTimeoutTask → DB 表 t_order 行 id=O001 字段 status 值为 CANCELLED → DB 表 t_order 行 id=O001 字段 cancel_reason 值为 timeout → DB 表 t_inventory_lock 行 order_id=O001 字段 release_status 值为 1 → MQ topic order.cancelled 消息体包含 orderId=O001,cancelReason=timeout → Redis key order:timeout:set 不包含 O001 |
| AC-002 | 未超时不取消 | 订单 O002 创建于 10 分钟前，状态为 PENDING_PAY | OrderTimeoutTask 触发执行 | 订单状态保持 PENDING_PAY，不做任何变更 | 调用 触发任务 OrderTimeoutTask → DB 表 t_order 行 id=O002 字段 status 值为 PENDING_PAY → Redis key order:timeout:set 包含 O002 |
| AC-003 | 并发处理：用户在任务执行瞬间完成支付 | 订单 O003 即将超时，用户在任务取走 orderId 后、更新前完成支付，状态已变为 PAID | OrderTimeoutTask 继续处理 O003 | 二次校验状态发现非 PENDING_PAY，跳过处理，不误改状态 | 调用 触发任务 OrderTimeoutTask → DB 表 t_order 行 id=O003 字段 status 值为 PAID → DB 表 t_inventory_lock 行 order_id=O003 字段 release_status 值为 0（未释放） |
| AC-004 | 库存释放失败重试 | 订单 O004 超时取消成功，但 inventory-service 调用返回 500 | OrderTimeoutTask 执行库存释放 | 重试 3 次仍失败，发送到 MQ retry topic | 调用 触发任务 OrderTimeoutTask → Mock 外部接口 POST /internal/inventory/release 返回 500 → DB 表 t_order 行 id=O004 字段 status 值为 CANCELLED（已取消） → 调用次数：外部接口 POST /internal/inventory/release 被调用 3 次 → MQ topic inventory.release.retry 消息体包含 orderId=O004 |
| AC-005 | 幂等性：库存释放接口重复调用 | inventory-service 已收到 O005 的释放请求并处理成功 | 网络重试导致同样的请求再次到达 | 第二次调用直接返回成功（基于唯一索引），不重复释放 | 调用 POST /internal/inventory/release 参数 orderId=O005,reason=timeout → 接口返回 code=0 → 调用 POST /internal/inventory/release 参数 orderId=O005,reason=timeout（再次） → 接口返回 code=1002 msg="库存已释放" → DB 表 t_inventory_lock 行 order_id=O005 行数为 1 |
| AC-006 | Redis 故障降级 | Redis 不可用 | OrderTimeoutTask 触发执行 | 降级查 MySQL 获取超时订单，正常处理 | Mock Redis 返回错误 → 调用 触发任务 OrderTimeoutTask → 日志包含 "Redis 降级 MySQL 查询" → DB 表 t_order 超时订单状态正常更新 |
| AC-007 | 性能：单批次 100 条订单处理耗时 | 准备 100 条超时订单 | OrderTimeoutTask 触发执行 | 单批次耗时 < 10 秒 | 调用 触发任务 OrderTimeoutTask → 日志包含 "扫描耗时" 且耗时 < 10000ms |

### 5.1 数据验证路径编写规范

格式 `[调用接口/事件] → 验证{数据状态/日志/消息}`，AI 测试引擎可解析为集成测试。

```
动作类型：
  调用 POST/GET/PUT/DELETE {URL} 参数 {...}
  触发任务 {taskName}
  触发事件 {topic} 消息 {...}
  等待 {毫秒}ms
  Mock 外部接口 {URL} 返回 {...}
  Mock {Redis/MySQL/MQ} 返回错误

断言关键字：
  接口返回 code={值} msg="文案"
  接口返回 data.{字段} = {值}
  DB 表 {表名} 行 {主键=X} 字段 {字段名} 值为 {值}
  DB 表 {表名} 行 {条件} 行数为 {N}
  Redis key {key} 值为 {值} / 不存在 / 包含 {member}
  Redis key {key} 不包含 {member}
  MQ topic {topic} 消息体包含 {字段=值}
  日志包含 "{文案}"
  调用次数：外部接口 {URL} 被调用 {N} 次
```

---

## 6. 接口测试映射

### 6.1 接口清单

| 接口 | 测试层级 | 测试入口 | 备注 |
|------|----------|----------|------|
| OrderTimeoutTask.scanAndCancel | 单元测试 + 集成测试 | `OrderTimeoutTaskTest` | Mock DB/Redis/RPC |
| POST /internal/inventory/release | 单元测试 + 集成测试 + 契约测试 | `InventoryControllerTest` + `InventoryReleaseContractTest` | 提供方契约测试 |
| MQ order.cancelled | 集成测试 | `OrderCancelEventTest` | 验证消息体格式 |

### 6.2 数据验证点清单

| 验证点 ID | 验证内容 | 数据源 | 预期结果 | 备注 |
|-----------|----------|--------|----------|------|
| DV-001 | 订单状态变更 | MySQL t_order.status | CANCELLED | 主验证点 |
| DV-002 | 取消原因写入 | MySQL t_order.cancel_reason | timeout | 区分人工/超时取消 |
| DV-003 | 库存释放状态 | MySQL t_inventory_lock.release_status | 1 | 验证库存联动 |
| DV-004 | MQ 事件发布 | MQ order.cancelled | 消息体含 cancelReason=timeout | 验证下游通知 |
| DV-005 | Redis 集合清理 | Redis order:timeout:set | 不含已处理订单 | 防重复扫描 |

### 6.3 Mock 与桩

| 外部依赖 | Mock 方式 | Mock 数据 | 备注 |
|----------|-----------|-----------|------|
| inventory-service | WireMock | `{"code":0,"data":{"releasedSkus":[...]}}` | 正常+失败+超时三种场景 |
| Redis | Embedded Redis | 实际数据写入测试实例 | 集成测试用 |
| XXL-Job | 手动触发 | 调用 `task.execute()` 模拟调度 | 单元测试用 |

---

## 7. 性能与容量评估

### 7.1 QPS 与 RT

| 指标 | 改造前 | 改造后 | 目标 |
|------|--------|--------|------|
| 入口 QPS | N/A | 每分钟 1 次任务 * 100 单 = 1.67 QPS | 任务级，无 SLA |
| 库存释放 RPC RT | N/A | 平均 50ms，P99 200ms | < 1s（含 3 次重试） |
| 单批次耗时 | N/A | 平均 5s，P99 10s | < 30s（任务间隔 1 分钟） |

### 7.2 资源影响

| 资源 | 影响 | 评估 |
|------|------|------|
| MySQL t_order | 新增定时扫描查询 + 单条更新 | 走 `idx_status_created` 索引，无全表扫；写入 100 单/分钟，无压力 |
| MySQL t_inventory_lock | 新增 release_status 写入 | 唯一索引保证幂等，无新增 IO 压力 |
| Redis | 新增 order:timeout:set ZSet | 预估 100 万订单 = 50MB 内存，可接受 |
| inventory-service | 新增 RPC 调用 | 100 QPS/分钟峰值，inventory-service 现有容量充足 |
| MQ order.cancelled | 新增消息流量 | 100 消息/分钟，可忽略 |

### 7.3 容量规划

- **峰值场景**：大促期间订单量 10 倍，预估每分钟 1000 单待处理
- **容量评估**：单批次提升到 500 条；任务执行频率不变；MQ 重试 topic 容量预估增加 10 倍
- **降级方案**：超时任务执行耗时 > 30s 时跳过本轮，下轮执行；连续 3 轮跳过则告警人工介入

---

> 低质量 PRD 处理范例见 `references/low-quality-prd-handling.md`（前后端通用）。
