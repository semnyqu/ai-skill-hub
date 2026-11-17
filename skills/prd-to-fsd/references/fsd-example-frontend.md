# FSD 填写范例：拍照回传 IN91 增值服务-电商平台件限制使用

此范例基于真实 PRD 生成，展示模板各章节的填写口径。所有代码路径、接口字段均从实际工程代码中确认。

```yaml
name: 拍照回传 IN91 增值服务-电商平台件限制使用
type: 已有功能迭代
branch: feature/in91-ecommerce-restrict
fsd_version: v1.0
generated_at: 2026-06-20 14:30
priority: 中
project:
  id: pickup
  repository: pickup-app
repositories:
  - id: pickup-app
    branch: feature/in91-ecommerce-restrict
    primary: true
  - id: pickup-app-android
    branch: feature/in91-ecommerce-restrict
prd_version: 2026-06-18 初版

summary:
  what: 增值服务推荐返回后，校验已选 IN91 子项是否在推荐允许范围内，不匹配时取消 IN91 勾选并提示
  where:
    - pickup-app:src/pickup/src/bizModules/.../AddServiceIN91.ts
    - pickup-app-android:src/pickup/src/bizModules/.../BatchCollectAddServiceAction.kt
    - pickup-app-android:src/pickup/src/bizModules/.../AddServicesActionNew.kt
  impact: 收件-散收任务详情页、收件-集收扫描页；不涉及后端接口变更，不影响非电商件流程

entry_points:
  - AddServiceIN91.handleRecommendResultPersonal
  - BatchCollectAddServiceAction.queryAddServiceChain
  - AddServicesActionNew.handleAddServiceQueryRespNew

dependencies:
  interfaces:
    - 查询可用增值服务(/recommendVas)
  modules:
    - pickup-vas 策略模板方法

test_scope:
  - unit
  - ui

is_new_feature: false
```

> 推导过程注释（帮助理解 FSD 各字段如何从代码中得出）：
> - `AddServiceIN91.handleRecommendResultPersonal`：搜索 `IN91` → 找到 `AddServiceIN91.ts` → 读取文件确认方法名
> - `attribute3`：搜索 `attribute3` → 在 `AddServiceBean` 中找到字段定义和注释
> - `requiredInformation` 结构：搜索 `requiredInformation` → 在接口响应解析代码中找到 JSON.parse 调用和后续的 childList 遍历逻辑
> - `recommendedType` 枚举值：搜索 `recommendedType` → 在常量定义文件中找到枚举注释

---

## 1. 需求背景

### 1.1 改造前 vs 改造后

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| 用户行为 | 下单或记忆带入 IN91 后，直接生效，不校验子项范围 | IN91 子项被校验，不匹配时自动取消勾选，散收弹窗提示/集收 Toast 提示 |
| 系统行为 | 不校验已选 IN91 子项是否在推荐返回的子项列表内 | 比对已选子项和推荐子项集合，不匹配时取消勾选、清空 attribute3、标记变更 |
| 业务结果 | 电商件可能带上电话号码子项，隐私合规风险 | 电商件不会带上被 SOP 禁用的子项，符合隐私合规 |

### 1.2 涉及业务子模块

收件 → 增值服务模块 → IN91 拍照回传服务（集收与散收共用校验逻辑，提示形式有差异）

### 1.3 交互设计稿截图

无

---

## 2. 开发范围

> 本模块采用标准策略模板方法。集收/散收/合并接口/独立请求等所有入口最终都汇入同一个策略类，**子项校验逻辑只改一处**；提示形式因集收/散收交互差异需分别接入。

| 业务模块 | 核心代码入口 | 文件路径 |
|---|---|---|
| `收件/增值服务/IN91 子项校验（共用）` | `AddServiceIN91.handleRecommendResultPersonal` | `src/pickup/src/bizModules/logicModulesWithPages/addService/biz/VasBiz/subLogic/AddServiceIN91.ts:123` |
| `收件/增值服务/校验未通过提示（差异化接入）` | 集收：`BatchCollectAddServiceAction.queryAddServiceChain`；散收：`AddServicesActionNew.handleAddServiceQueryRespNew` | 集收：`BatchCollectAddServiceAction.kt:89`；散收：`AddServicesActionNew.kt:156` |

### 2.1 架构说明

本模块采用标准策略模板方法（见 `docs/module-packages/pickup-vas/PACKAGE.md`），集收/散收/合并接口/独立请求等所有入口最终都汇入同一个策略类。子项校验逻辑只改一处，提示形式因集收/散收交互差异需分别接入。

> 配套：若 IN91 策略类目前无法从 `AddServiceRecommendParam` 拿到推荐项的子项原始信息，需在调用方补参。

---

## 3. 接口文档

### 3.1 接口变更概览

| 接口 | 变更类型 | 说明 |
|------|----------|------|
| 查询可用增值服务 | 无变更 | 本次需求为纯客户端逻辑变更，仅使用现有字段 |

### 3.2 接口信息

#### 3.2.1 查询可用增值服务

| 项目 | 内容 |
|---|---|
| 接口名称 | 查询可用增值服务 |
| 请求方式 | POST |
| 请求URL | `/express/digitalPickupService/psds/recommendVas` |
| URL 常量 | `PAddServiceUrl.CALCULATE_QUERY_AVAILABLE_ADD_SERVICE_PICKUP` |
| 代码入口 | `RecommendVasBiz.queryAvailableAddServiceResult` |

**响应结构（涉及本需求的字段）：**

```jsonc
{
  // ---------- 通用字段 ----------
  "vasCode": "IN91",                    // 服务代码，枚举值
  "vasName": "拍照回传",                 // 服务名称
  "recommendedType": 2,                 // 服务推荐类型: 1=绑定不可取消, 2=可选服务, 5=默认绑定可取消, 6=默认可选不可取消
  "feeCode": "91",                      // 费用代码
  "freightBinding": 1,                  // 付款方式是否与主运费绑定: 0=否, 1=是
  "subItemType": 2,                     // 子项推荐类型: 1=子项不可修改, 2=子项可修改
  "stressRecommend": 0,                 // 是否重点推荐: 0=否, 1=是
  "useCoupon": "1",                     // 是否支持顺丰券支付: 0=否, 1=是
  "mutexVas": "IN149",                  // 互斥增值服务代码
  "currency": "CNY",                    // 币种
  "floorPrice": 2,                      // 最低价格

  // ---------- 本次需求校验的核心字段 ----------
  "requiredInformation": "{...}"        // JSON 字符串，结构见下方详解；
                                        // 在其 childList 中找到 value="13"（签回单拍照）的节点，
                                        // 取该节点的 childList 作为"推荐允许的 IN91 属性13子项列表"
                                        // 与小哥已选的 attribute3 做集合比对
}
```

**requiredInformation 反序列化后结构详解：**

```jsonc
{
  "name": "验收方式",                                    // 必填信息名称
  "writeType": "3",                                     // 填写方式: 1=文本, 2=单选, 3=多选, 4=数字
  "childList": [                                        // 一级 childList = IN91 的所有可选子项
    { "name": "身份证正面", "sort": 1, "value": "1" },
    { "name": "身份证反面", "sort": 2, "value": "2" },
    { "name": "NFC身份证验证", "sort": 9, "value": "9" },
    {
      "name": "签回单拍照",                               // 签回单拍照父节点（本次需求的关键入口）
      "sort": 13,
      "value": "13",
      "childList": [                                     // ★ 属性13子项列表（本次需求的校验依据）★
        { "name": "拍签名", "sort": 1, "value": "1" },
        { "name": "拍盖章", "sort": 2, "value": "2" },
        { "name": "登记身份证勾选", "sort": 4, "value": "4" },
        { "name": "签收日期", "sort": 8, "value": "8" }
        // 非电商件场景此处还会出现:
        // { "name": "电话号码", "sort": 9, "value": "9" }
      ],
      "comment": { "writeType": "1", "totalNum": "", "name": "总份数:" }
    }
  ]
}
```

**关键字段说明：**

| 路径 | 取值 | 含义 |
|---|---|---|
| `childList[].value` | `"1"\|"2"\|"9"\|"13"` | IN91 的一级子项标识。当 value="13" 时表示签回单拍照（本次需求的校验入口） |
| `childList[value=13].childList[].value` | `"1"\|"2"\|"4"\|"8"\|"9"` | 属性13子项的 value 值集合。**本次需求比对的目标数据源** |
| `childList[value=13].childList[value="9"]` | 电话号码（仅非电商件返回） | **电商平台件不会返回此节点**，即为本次需求触发的判定依据 |

### 3.3 客户端本地存储字段

小哥选择的 IN91 属性13子项存储在 `AddServiceBean.attribute3`（逗号分隔），对照关系：

```
attribute3 = "1,2,8"     → 已选: 拍签名(1) + 拍盖章(2) + 签收日期(8)
attribute3 = "1,2,8,9"   → 已选: 拍签名(1) + 拍盖章(2) + 签收日期(8) + 电话号码(9)
attribute3 = ""          → 未选择子项，不触发校验
```

### 3.4 核心逻辑

```
1. 前置条件判断：
   - IN91 未勾选 或 attribute3 为空 → 跳过校验，不触发任何处理
   - 推荐结果中未返回 IN91 → 走原有"未推荐"分支，不触发本次校验

2. 数据提取：
   - 已选子项集合 = attribute3.split(",")  → 例如 ["1","2","8","9"]
   - 推荐子项集合 = childList[value="13"].childList[].value  → 例如 ["1","2","8"]

3. 集合比对：
   - 已选集合 ⊆ 推荐集合 → 校验通过，不做任何处理，沿用原有流程
   - 已选集合 ⊈ 推荐集合 → 校验未通过：
     a. 取消 IN91 勾选
     b. 清空 attribute3
     c. 标记 bean.in91SubItemChanged = true
     d. 由集收/散收按各自交互形式提示小哥

4. 校验顺序：在 recommendedType 自动勾选逻辑之前执行
```

### 3.5 注意事项

- 接口字段本身**无新增/修改/废弃**。本需求为纯客户端逻辑变更。
- `requiredInformation` 解析失败（非合法 JSON）时跳过校验，不阻塞原有流程。
- 该校验落在 IN91 策略类钩子内，集收/散收等所有入口天然共用一份代码。
- **性能影响**：无新增接口调用，本地集合比对 O(n) 复杂度 n≤10，内存无变化。
- **兼容性**：向后全兼容（非电商件流程完全不变），接口无变更，无需升级 APP 版本。

---

## 4. 需求功能点

| 功能点 ID | 变更类型 | 触发/前置条件 | 功能描述 | 输出/交互 | 边界/特殊处理 |
|---|---|---|---|---|---|
| FP-001 | 修改 | 增值服务推荐接口返回后，进入 IN91 推荐结果处理；下单或记忆已带入 IN91（即 IN91 当前处于勾选态、且存在已选属性13子项） | 比对"小哥已选的 IN91 属性13子项（attribute3 逗号分隔值）"与"本次推荐接口返回的 IN91 requiredInformation.childList 中 value=13（签回单拍照）节点下的子项 value 集合"。① 已选子项全部在推荐列表内 → 不做任何处理；② 存在任一已选子项不在推荐列表内 → 取消 IN91 勾选，清空 attribute3，标记 in91SubItemChanged=true，由集收/散收按各自交互形式提示小哥 | 校验通过：无可感知变化。校验未通过：增值服务列表中 IN91 变为未勾选，组合服务摘要同步刷新，费用同步刷新，并按 FP-002/FP-003 给出对应提示 | 1) 只在"IN91 当前已勾选且 attribute3 非空"时执行；推荐结果未返回 IN91、或下单/记忆未带 IN91 时均不触发；2) 比对粒度为 value=13 节点下的直接 childList value；3) 校验顺序在 recommendedType 自动勾选逻辑之前；4) 该校验落在 IN91 策略类钩子内，集收/散收公用一份代码。**上线保障**：灰度 5% 3 天；回滚方案为代码回滚；监控埋点为 IN91 校验未通过埋点（区分散收/集收）；回归范围为收件散收下单、集收扫描、非电商件 IN91 |
| FP-002 | 新增 | 散收场景下 IN91 校验未通过（bean.in91SubItemChanged === true） | 经由 deleteAvsDialog 弹窗提示小哥（复用现有弹窗机制）；弹窗显示 IN91 被取消，提供"确认"按钮 | 点击确认后弹窗关闭，回到增值服务列表，可自行重新进入 IN91 选择允许的子项 | 弹窗复用增值服务现有 deleteAvsDialog 能力；同一票同一次推荐返回最多触发一次 |
| FP-003 | 新增 | 集收（批量收件）场景下 IN91 校验未通过（bean.in91SubItemChanged === true） | 用顶部 Toast 轻提示，内容："记忆的增值服务发生变化，已经取消，请和客户确认"；不打断批量扫描流；不走 deleteAvsDialog 弹窗 | Toast 自动消失，不需要小哥操作；IN91 已被取消勾选，小哥需要时可手动重新进入选择 | 1) 集收为连续扫描场景，不能用模态弹窗阻断；2) 同一批扫描内同一票最多触发一次 Toast |

---

## 5. 验收标准

| 用例 ID | 场景 | Given | When | Then | UI 操作路径 |
|---|---|---|---|---|---|
| AC-001 | 非电商件-散收-下单带 IN91 | 散收单票订单的下单信息包含 IN91，已选属性13子项含电话号码 | 进入散收任务详情，推荐接口返回的 IN91 属性13子项列表包含电话号码 | IN91 保持勾选，电话号码完整保留，不弹窗 | [任务详情页] → 等待增值服务加载完成 → 截图 → 元素"拍照回传"状态为"勾选" → 点击"拍照回传" → 页面显示"电话号码" |
| AC-002 | 非电商件-集收-记忆带 IN91 | 集收小哥前一票记忆了含电话号码的 IN91，扫描下一票（非电商件） | 推荐接口返回的 IN91 属性13子项列表包含电话号码 | IN91 保持勾选，记忆完整带入，不出现 Toast | [集收扫描页] → 扫描非电商件运单 → 等待增值服务加载完成 → 截图 → 页面不显示"记忆的增值服务发生变化" |
| AC-003 | 电商件-散收-下单带 IN91 | 散收单票订单属于电商平台件，下单 IN91 已选属性13子项含电话号码 | 推荐接口返回的 IN91 属性13子项列表不包含电话号码 | 弹出模态弹窗"拍照回传的子项有变更，请重新选择"；点击确认后 IN91 变为未勾选；组合服务摘要同步刷新；总费用扣除 IN91 费用 | [任务详情页] → 等待增值服务加载完成 → 弹窗显示"拍照回传的子项有变更，请重新选择" → 点击"确认" → 弹窗关闭 → 元素"拍照回传"状态为"未勾选" → 截图 |
| AC-004 | 电商件-集收-记忆带 IN91 | 集收小哥前一票记忆了含电话号码的 IN91，扫描下一票（电商件） | 推荐接口返回的 IN91 属性13子项列表不包含电话号码 | 顶部 Toast 显示"记忆的增值服务发生变化，已经取消，请和客户确认"，不打断扫描流；IN91 变为未勾选；组合服务摘要、费用同步刷新 | [集收扫描页] → 扫描电商件运单 → 等待增值服务加载完成 → Toast显示"记忆的增值服务发生变化，已经取消，请和客户确认" → 等待3000ms → Toast消失 → 页面不显示弹窗 → 截图 |
| AC-005 | 电商件-全部子项不在推荐内 | 已选的所有 IN91 属性13子项在本次推荐结果中都不存在 | 触发增值服务推荐处理 | 散收：同 AC-003 弹窗；集收：同 AC-004 Toast | 同 AC-003（散收）/ AC-004（集收） |
| AC-006 | 推荐结果未返回 IN91 | 下单/记忆带入 IN91，但推荐结果中无 IN91 项 | 触发增值服务推荐处理 | 走原有"未推荐"分支，不触发本次新增的属性13子项校验 | [任务详情页] → 等待增值服务加载完成 → 截图 → 页面不显示"拍照回传的子项有变更" |
| AC-007 | 下单/记忆未带 IN91 | 下单与记忆均未包含 IN91 | 触发增值服务推荐处理 | 不触发属性13子项校验，无任何新增提示 | [任务详情页] → 等待增值服务加载完成 → 截图 → 页面不显示"拍照回传的子项有变更" → 页面不显示"记忆的增值服务发生变化" |
| AC-008 | 校验逻辑一致性回归 | 同一个电商件订单 | 分别走散收和集收链路 | 两条链路下 IN91 均被取消勾选；散收弹窗、集收 Toast | 散收：[任务详情页] → 弹窗显示"拍照回传的子项有变更，请重新选择" → 点击"确认" → 元素"拍照回传"状态为"未勾选"。集收：[集收扫描页] → 扫描同一电商件运单 → Toast显示"记忆的增值服务发生变化，已经取消，请和客户确认" → 元素"拍照回传"状态为"未勾选" |
| AC-009 | 集收同一票不重复提示 | 集收场景下，同一票触发了校验未通过 | 该票增值服务推荐返回处理完成 | Toast 只出现一次；后续扫下一票时是新 Toast，不与上一票残留 | [集收扫描页] → 扫描电商件运单 → Toast显示"记忆的增值服务发生变化，已经取消，请和客户确认" → 等待3000ms → Toast消失 → 截图 → 页面不显示"记忆的增值服务发生变化" |

> 低质量 PRD 处理范例见 `references/low-quality-prd-handling.md`（前后端通用）。
