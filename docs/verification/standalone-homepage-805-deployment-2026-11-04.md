# 独立首页 805 端口发布

用户明确要求发布到服务器805端口。2026-11-04已完成，入口：<http://43.142.150.158:805/>。

## 部署

- 来源：`standalone/feima-home-v4/`，包含最新宽屏、固定导航、双向滚动渐变、平滑轮播及真实业务跳转。
- 版本：`20261104-232556`（北京时间）。发布9个静态文件，未上传服务器连接资料或本地报告。
- 目录：`/srv/feima-home-805/releases/20261104-232556`。
- 当前版本链接：`/srv/feima-home-805/current`。
- Nginx配置：`/etc/nginx/sites-available/feima-home-805`，通过同名sites-enabled链接启用；监听`0.0.0.0:805`。
- 原805端口空闲、无同名站点，属于首次发布，无旧版本需覆盖。新配置先nginx -t再平滑reload，未重启业务服务。
- 业务链接继续指向原80端口站点，本站不代理API或处理登录、付款。

## 验证

- SSH严格使用本机已记录的主机密钥，连接密码只从用户指定文件读取，未写入发布文件。
- 服务器与公网全部9个文件SHA256均与本地一致；公网805可直接访问，无需修改防火墙或云安全组。
- 原80首页发布前后SHA256相同：`159ebff14ee5830edc2c267e51d1f445091a539e10a87c4fad5771f452082f1f`。
- Nginx和六个业务服务均active。
- ego浏览器1440/390px：无横向溢出、无破图、无捕获到的页面错误、无dialog。导航滚动后top=0；手动轮播切换正常；免费试用实点到`http://43.142.150.158/register`。
- 已查看公网桌面/手机截图；发布内容与此前本地动效验证一致。

原始证据：`.agent-runs/homepage-v4-deploy805-20261104/`下manifest.json、preflight.txt、publish-result.txt、public-verification.json、browser-verification.json及截图。

## 撤销本次独立站点

需要停用805站点时执行以下命令，仅移除该站点的启用链接，版本目录保留：

```sh
sudo unlink /etc/nginx/sites-enabled/feima-home-805
sudo nginx -t && sudo systemctl reload nginx
```

恢复：重新建立`sites-enabled/feima-home-805`到`sites-available/feima-home-805`的符号链接，配置检查后reload。
