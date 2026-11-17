# FSD 质量检查清单（后端）

生成后端 FSD 后，逐项检查最终交付的 FSD 文件，确认产物质量。全部通过后方可交付。

---

## 核心检查（18 项）

- [ ] 1. YAML 结构化摘要已填写：name、type、**domain=backend**、branch、priority、project(id/repository)、repositories、summary(what/where/impact)、entry_points、dependencies(apis_provided/apis_consumed/storage/modules)、test_scope、is_new_feature
- [ ] 2. 仓库元数据一致：repositories 至少一项且 ID 唯一、仅一个 primary=true、project.repository/顶层 branch 分别与主仓 id/branch 一致；各仓分支与代码探索实际使用的分支一致
- [ ] 3. FSD 版本、生成时间、PRD 版本已在 YAML 摘要中填写
- [ ] 4. 所有代码入口路径均通过实际搜索确认（非猜测），精确到 `服务名:文件路径:行号`
- [ ] 5. 接口设计：字段类型、必需性、校验规则与代码实际定义一致
- [ ] 6. 接口幂等性、限流策略已明确说明
- [ ] 7. 表结构变更已列出（字段、索引、DDL 在线性、兼容性）
- [ ] 8. 缓存与消息变更已列出（key/topic、TTL、消息体格式、重试策略）
- [ ] 9. 核心逻辑伪代码包含：入参校验、前置条件、数据读写、事务边界
- [ ] 10. 每个新增/修改/删除功能点都有对应的验收标准，验收标准覆盖正常/异常/并发/幂等
- [ ] 11. Then 无"正常""正确""符合预期"等模糊措辞，明确写出数据状态/接口返回/事件输出
- [ ] 12. 数据验证路径：列出接口调用 + DB/Redis/MQ/日志的具体验证步骤
- [ ] 13. 接口测试映射已填写：接口清单 + 数据验证点 + Mock 策略
- [ ] 14. AI 自主决策的差异项（字段名/类型不一致）已在 3.6 注意事项中注明
- [ ] 15. 性能与容量评估已填写：QPS/RT 目标、资源影响（DB/缓存/MQ/外部依赖）、容量规划
- [ ] 16. 调用方影响清单已列出（哪些调用方需协同改造或通知）
- [ ] 17. FSD 中无"未确认"标记遗留
- [ ] 18. FSD 输出到 `docs/fsd/{需求简称}-fsd.md`；临时文件已清理；git 工作环境已恢复
