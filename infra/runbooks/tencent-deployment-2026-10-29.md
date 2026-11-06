# 腾讯云 IP 部署记录 · 2026-10-29

> 2026-11-04 已按用户要求新增独立首页805端口：<http://43.142.150.158:805/>。目录`/srv/feima-home-805/current`，独立Nginx站点`feima-home-805`。9个公网文件哈希及桌面/手机检查通过，原80端口首页哈希与业务服务保持正常。见[发布与撤销记录](../../docs/verification/standalone-homepage-805-deployment-2026-11-04.md)。

> 2026-11-03 20:03 已发布摄影配图 V3 首页。独立构建排除未发布的客服页导航改动；24 项单测、构建、公网 25 文件哈希及 ego 桌面／手机双主题检查通过，六个服务健康。备份 `/srv/yingzuo/backups/homepage-photo-v3-before-20261103-200343.tar.gz`。见[摄影 V3 首页发布与回滚记录](../../docs/verification/homepage-photo-v3-deployment-2026-11-03.md)。

> 2026-11-03 17:28 已发布最新光场创作首页，仅更新前端。24 项单测、生产构建、24 个公网文件哈希和 ego 桌面／手机检查通过，六个服务健康。备份 `/srv/yingzuo/backups/homepage-before-20261103-172816.tar.gz`。见[光场首页发布与回滚记录](../../docs/verification/homepage-lightfield-deployment-2026-11-03.md)。

> 2026-11-03 已发布当前工作区前端（动态首页、客服展示页、工作台及快速生成修复）和两个文案图片兼容后端文件。401 项单测、构建、公网 18 文件哈希与 ego 页面检查通过；六个服务健康。备份 `/srv/yingzuo/backups/web-before-20261103-114429.tar.gz`。入口仍为 <http://43.142.150.158/>，域名仍受备案限制。详见 [本次发布与回滚记录](../../docs/verification/web-deployment-2026-11-03.md)。

> 2026-10-31 已发布飞马登录注册双主题界面。当前可用入口 http://43.142.150.158/login ，域名仍受备案限制。备份与回滚见 [本次部署验证](../../docs/verification/auth-deployment-2026-10-31.md)。仅更新前端，未变更数据库及业务配置。

访问入口：http://feimadianshang.online/ ，登录入口：http://feimadianshang.online/login 。原 IP http://43.142.150.158/ 继续可用。
管理员账号 `admin`，继续使用本机原密码；未修改任何已有账号密码。

## 本次迁移范围

按用户最后确认的范围迁移 4 个账号、系统政策与价格参数、网站品牌配置、三个 Agent 的连接及模型配置、相应加密密钥。
保留每个账号当时的可用积分，并以有明确迁移说明的期初积分记录入账；历史冻结、消费和任务流水未迁移。积分对账通过。
没有上传用户素材和成果，没有迁移任务、作品、商品、文件、旧会话和生成历史。服务器素材目录为空，头像文件引用已清空。
本机数据库和素材未修改；快照期间暂停的本机后端服务已恢复。

沿用本机 `APP_MODE=mock`、`APP_TEST_ONLY=true` 及对应业务政策。三个 Agent 为实际 HTTP 服务，模型配置读取成功，但本次没有发起付费模型生成，不代表正式生产政策验收完成。

## 服务器布局

最新前端更新（2026-11-01）：已发布确认后的动态登录／注册页，静态目录沿用原路径，后端与数据未改动。三 agent 独立评审、24 项测试、构建、公网 13 个文件哈希及八种浏览器布局检查通过。备份为 `/srv/yingzuo/backups/auth-motion-before-20261101-201214.tar.gz`；入口为 <http://43.142.150.158/login>，域名仍受备案限制。详见[发布与回滚记录](../../docs/verification/auth-motion-deployment-2026-11-01.md)。

- 系统：Ubuntu 26.04；Python 3.12；MySQL 8.4；Redis；Nginx；FFmpeg；Noto CJK 字体。
- 发布代码：`/opt/yingzuo/releases/20261029/`，含 web、textAgent、imageAgent、videoAgent。
- 运行配置：`/srv/yingzuo/config/`，仅部署用户可读取，包含密码及加密密钥，不应公开或提交 Git。
- 新文件目录：`/srv/yingzuo/storage/web`、`/srv/yingzuo/storage/imageAgent`、`/srv/yingzuo/storage/videoAgent`。
- 账号配置导入快照：`/srv/yingzuo/backups/config-snapshot/`，不含素材、任务或作品历史。
- Nginx：`/etc/nginx/sites-available/yingzuo`。
- systemd：`yingzuo-api`、`yingzuo-worker`、`yingzuo-text`、`yingzuo-image`、`yingzuo-video-api`、`yingzuo-video-worker`，均已设置开机自启和失败重启。
- 公网监听：80；内部监听：web API 18000、文本 8000、图片 9000、视频 8015、MySQL 3306、Redis 6379，均绑定回环地址。

## HTTP 兼容改动

按用户要求先用 IP:80，未配置 HTTPS。Nginx 仅在该 HTTP 入口去除 session/csrf_token 的 Secure 标记，保留 HttpOnly、SameSite、Origin 与 CSRF 校验。未来切换 HTTPS 时移除配置中的两条 `proxy_cookie_flags ... nosecure`，并将 `APP_AUTH_ORIGINS` 更新为实际 HTTPS 来源。
前端新增 `src/compat/randomUUID.ts`，使用 `crypto.getRandomValues` 补齐 HTTP 下缺失的 UUID v4 方法，支持注册、任务幂等与积分操作。原生 randomUUID 存在时保持原实现。
videoAgent 的 `video_agent/media.py` 新增 Linux Noto CJK 字体默认路径，同时保留 Windows 字体目录；支持 `VIDEO_AGENT_FONT_DIR` 覆盖。

## 验证

- 四个数据库的 Alembic 迁移版本均已核对至当前代码 head。
- web 和三个 Agent 的 ready 均为 HTTP 200；六个应用服务运行正常。
- HTTP 登录、会话保持、错误 Origin 拒绝、CSRF 校验及退出通过；一次性验证账号和会话已在脚本 finally 中删除。
- 三类模型配置的后台读取接口均为 HTTP 200，验证了服务接线与加密配置可读。
- 4 个账号积分账本对账无差异。
- 前端 UUID 专项测试 3/3 通过，类型检查和生产构建通过。
- ego 浏览器确认公网首页、登录页、ready 接口与 HTTP UUID 兼容正常。
- Linux 下使用临时合成素材完成 30 帧中文字幕视频合成，测试文件自动清理，未调用付费模型。

## 运维命令

```sh
sudo systemctl status yingzuo-api yingzuo-worker yingzuo-text yingzuo-image yingzuo-video-api yingzuo-video-worker
sudo journalctl -u yingzuo-api -n 100 --no-pager
curl http://127.0.0.1:18000/api/v1/health/ready
sudo nginx -t
```

配置有变更时重启对应服务。仅服务器已有配置发生变化时，不要重新执行创建数据库或导入快照步骤。

## 域名绑定更新（2026-10-29）

用户最终要求仅使用 HTTP，暂不启用 HTTPS。

- `feimadianshang.online` 的 A 记录已指向 `43.142.150.158`。
- Nginx 80 端口同时接收域名和原 IP；已撤销 HTTPS 跳转及 443 监听。
- `APP_AUTH_ORIGINS` 精确允许 `http://feimadianshang.online` 和 `http://43.142.150.158`。
- HTTP 入口继续保留此前 Cookie 兼容配置；域名下登录、会话、CSRF 和退出已验证通过。
- ego 浏览器实测 HTTP 域名登录页可访问，ready 接口返回 200。
- 已签发的证书未用于当前站点；`certbot.timer` 已停用。未新增腾讯云 443 入站规则。
- 原配置备份位于 `/srv/yingzuo/backups/domain-20261029/`。

## 80 端口界面更新（2026-10-30）

- 按用户要求发布当前本地飞马蓝色浅色／深色前端；数据库、账号、业务配置和后端服务未改动。远端品牌模块四个文件的 SHA256 与本地一致，无需重复部署后端。
- 发布目录仍为 `/opt/yingzuo/releases/20261029/web/frontend/dist`。先复制资源，再原子替换 `index.html`，保留旧哈希资源供已打开的页面使用。
- 旧版本备份：`/srv/yingzuo/backups/feima-ui-before-20261030-112811.tar.gz`；新包展开目录：`/opt/yingzuo/releases/feima-ui-20261030-112811`。回滚时解包到独立临时目录，先复制资源，最后原子替换入口文件。
- `npm run build` 通过；品牌、主题、首页、HTTP UUID 回归共 3 个文件、16 项测试通过。初次测试因沙箱临时文件重命名权限失败，正常权限重跑通过。
- IP 入口 `http://43.142.150.158/` 的全部 11 个发布文件与本地构建 SHA256 一致；ready 为 true，六个应用服务 active，Nginx 配置检查通过。
- ego 浏览器验证 IP 首页 6 处图片全部加载、浅色／深色切换正常、无横向溢出。沿用既有登录态访问登录路由，正常进入并加载快速生成工作台；未触发新任务或积分操作，未测试重新登录。用户原深色主题已恢复。
- **公网域名当前受备案限制**：本机外部访问 `http://feimadianshang.online/` 被跳转至腾讯云 `dnspod.qcloud.com/static/webblock.html`，显示“您的网站未完成备案”。服务器内部访问域名正常，不能据此认定公网域名可用。当前可使用上述 IP:80 入口；域名需完成腾讯云备案后再验证。
