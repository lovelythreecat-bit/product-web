from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
source = root.parent / 'homepage-bold-2026-11-03'
html = (source / 'index.html').read_text(encoding='utf-8')
html = html.replace('光场创作概念', '创意配图 V2 · 评审稿')
html = html.replace('</head>', '<link rel="stylesheet" href="image-fit.css"></head>')
html = html.replace('assets/logo.png', '../homepage-bold-2026-11-03/assets/logo.png').replace('assets/lingling.png', '../homepage-bold-2026-11-03/assets/lingling.png')
mapping = {
    'shoe-20261103.webp': 'categories/shoe-campaign.png',
    'beauty-20261103.webp': 'categories/beauty-campaign.png',
    'audio-20261103.webp': 'categories/audio-campaign.png',
    'tumbler-20261103.webp': 'digital/phone-source.png',
    'commute-20261103.webp': 'story/phone-lifestyle.png',
    'creator-20261103.webp': 'story/phone-creator.png',
}
for old, new in mapping.items():
    html = html.replace('assets/' + old, new)
html = html.replace('保温杯', '影像手机').replace('主打上班通勤', '主打城市影像与金属质感').replace('浅蓝色通勤', '冰蓝钛金属').replace('办公通勤海报', '城市影像广告').replace('通勤场景', '城市影像场景')
html = html.replace('<img class="result-a" src="digital/phone-source.png" alt="同款影像手机白底主图"', '<img class="result-a" src="digital/phone-campaign.png" alt="同款手机光学棱镜创意广告"')
html = html.replace('<img class="result-b" src="story/phone-lifestyle.png" alt="同款影像手机城市影像广告"', '<img class="result-b" src="digital/phone-detail.png" alt="同款手机镜头与金属工艺创意海报"')
oldhero = '<figure class="product-plane" data-product="0" data-slot="0"><img src="categories/shoe-campaign.png" alt="蓝白跑鞋商品主图创作示例"'
newhero = '<figure class="product-plane" data-product="0" data-slot="0"><img src="digital/phone-campaign.png" alt="冰蓝钛金属手机光学棱镜创意广告示例"'
assert oldhero in html
html = html.replace(oldhero, newhero).replace('<span>文生图 · 鞋服</span>', '<span>文生图 · 手机</span>').replace('aria-pressed="true">鞋服</button>', 'aria-pressed="true">手机</button>').replace('aria-pressed="false">数码</button>', 'aria-pressed="false">音频</button>')
html = html.replace('<span>光场创作 · 高保真动效提案</span>', '<a href="assets.html">创意配图 V2 · 查看全部 8 张素材</a>')
(root / 'index.html').write_text(html, encoding='utf-8')
shutil.copyfile(source / 'style.css', root / 'style.css')
motion = (source / 'motion.js').read_text(encoding='utf-8').replace('保温杯', '影像手机').replace('主打上班通勤', '主打城市影像与金属质感')
(root / 'motion.js').write_text(motion, encoding='utf-8')
print('Built isolated homepage review; no production files changed.')
