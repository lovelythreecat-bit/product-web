---
id: "account-recharge"
title: "充值入口当前能做什么"
status: "draft"
implementation_status: "implemented"
applicable_routes: ["/recharge","/account"]
source_refs: [{"path":"frontend/src/features/account/RechargeInfoView.vue","line_start":11,"line_end":18},{"path":"docs/电商AI创作平台-首版需求终稿-2026-10-09.md","line_start":209,"line_end":224}]
deployment_status: "not_verified"
review_required: true
---

# 充值入口当前能做什么

> 草稿，仅依据当前本地代码或设计资料；未经人工审核，不进入正式知识库，也不代表生产已上线。

## 用户可能怎么问
- 可以微信充值吗？
- 点充值为什么积分没增加？

## 简洁回答
“充值积分”打开说明页，显示“在线充值暂未开放”。不会创建订单、调用支付或增加积分。首版使用注册赠送与管理员发放，具体额度以实际账户和适用配置为准。

## 常见异常及处理
不要向未知收款码付款。未来支付方式、比例、档位、退款规则待支付阶段确认，不能承诺上线日期或退款。
