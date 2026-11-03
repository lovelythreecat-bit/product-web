# 登录注册页部署验证 · 2026-10-31

用户明确要求将已确认并完成的正式登录注册页部署到既有服务器。本次仅发布前端构建，数据库、账号、积分、用户素材、运行配置与六个后端服务均未修改或重启。

## 发布

- IP 入口：`http://43.142.150.158/login`、`http://43.142.150.158/register`。
- Nginx 静态根：`/opt/yingzuo/releases/20261029/web/frontend/dist`。
- 本地重新执行 vue-tsc 与 Vite build，均通过；保留既有大 chunk 警告。
- 包 SHA256：`216d252519d524247ac72c8a4462566c9e672285021bd9d2267daeb1f448f65e`，上传后服务器再次核对通过。
- 旧版备份：`/srv/yingzuo/backups/auth-ui-before-20261031-002513.tar.gz`，已校验压缩包可读取。
- 独立展开目录：`/opt/yingzuo/releases/auth-ui-20261031-002513`。
- 先复制静态资源，保留历史哈希文件；最后原子替换 index.html。服务器内后置检查失败时脚本自动恢复旧入口。
- 原入口 SHA256：`317ac29b25a9726b19721b0b1c828ba1c06dc0c87c1cb81bf163935f535ce4f2`。
- 新入口 SHA256：`19dd85b1ea7f6aaeb2497fad808cf4409607bd789b8aa914d2cbb802f14b2892`。

## 验证

- Nginx 配置检查通过，ready 返回 true（database/storage 均 true），六个应用服务均 active。
- 公网下载全部 13 个构建文件，与本地 SHA256 逐个一致；ready 为 HTTP 200。
- Ego 浏览器实测正式 IP 入口，未注入测试接口：1440×960、390×844 下登录／注册、浅色／深色共 8 组均无横向溢出；Logo 及对应主题商品图加载成功。表单字段数量为 2／3。
- 后台品牌名“飞马工作台”正常展示，原浅色主题在检查后恢复。未提交真实登录、注册或生成请求，不代表认证写入全链路验收。
- 截图与 JSON 见同名目录 `auth-deployment-2026-10-31/`。Ego TaskSpace 已关闭，未升级浏览器。

## 域名现状

公网 `http://feimadianshang.online/login` 仍被重定向至 `https://dnspod.qcloud.com/static/webblock.html?d=feimadianshang.online`，提示“您的网站未完成备案”。这是既有备案限制，不是本次发布导致。当前使用 IP 入口；未修改 DNS、HTTPS 或备案设置。

## 回滚

旧哈希资源完整保留；可将上述展开目录内 `previous-index.html` 复制到 dist 下临时入口，再原子替换 `index.html`。完整恢复则将备份解压到独立临时目录、先恢复资源、最后原子替换入口。回滚后检查入口哈希及 ready；无需迁移数据库或重启业务服务。
