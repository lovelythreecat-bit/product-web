from pathlib import Path
import shutil

root=Path(__file__).resolve().parent
old=root.parent/'homepage-art-direction-2026-11-03'
html=(old/'index.html').read_text(encoding='utf-8')
html=html.replace('创意配图 V2','摄影配图 V3').replace('查看全部 8 张素材','查看配图与放置位置')
html=html.replace('光学棱镜创意广告','纸艺布景广告').replace('精华瓶与面霜的水光美妆创作示例','精华瓶与压纹玻璃的美妆广告示例')
html=html.replace('我要卖一款影像手机，','我要卖一款手机，').replace('主打城市影像与金属质感','做一组新品广告')
html=html.replace('<span>你的想法</span>','<span>上传的商品原图</span>')
start=html.index('<section class="workspace wrap">')
end=html.index('<section class="delivery wrap"',start)
workspace=html[start:end].replace('digital/phone-source.png','digital/phone-campaign.png').replace('story/phone-lifestyle.png','digital/phone-detail.png').replace('影像手机白底商品示例','手机新品广告创作示例').replace('影像手机城市影像场景创作示例','手机工艺细节创作示例')
html=html[:start]+workspace+html[end:]
html=html.replace('href="assets.html"','href="overview.html"')
assert html.count('src="digital/phone-source.png"')==1
assert 'phone-lifestyle' not in html
(root/'index.html').write_text(html,encoding='utf-8')
shutil.copyfile(old/'style.css',root/'style.css')
motion=(old/'motion.js').read_text(encoding='utf-8').replace('我要卖一款影像手机，主打城市影像与金属质感','我要卖一款手机，做一组新品广告')
(root/'motion.js').write_text(motion,encoding='utf-8')
print('V3 independent preview built: source photo occurs once; no lifestyle asset.')
