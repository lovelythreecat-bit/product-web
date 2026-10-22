import { productType } from './productTypes'
export const productLabels: Record<string, string> = {
  product_type: '商品类型', origin: '产地', price: '实际售价', promotion: '优惠信息', warranty: '售后保障',
  fabric: '面料成分', fit: '版型', season: '适用季节', care: '洗护方式', lining: '内里材质', sole_material: '鞋底材质',
  skin_type: '适用肤质', ingredients: '成分 / 配料', net_content: '净含量', shelf_life: '保质期', usage: '使用方法',
  flavor: '口味', allergens: '过敏原', storage_conditions: '储存条件', processor: '处理器', memory: '运行内存',
  storage: '存储容量', screen: '屏幕参数', battery: '电池与续航', connectivity: '连接方式', compatibility: '兼容设备',
  power: '额定功率', voltage: '额定电压', energy_rating: '能效等级', functions: '功能配置', sport: '适用运动',
  waterproof: '防水性能', age_range: '适用年龄', safety_standard: '安全标准', technical_specs: '其他规格',
  name: '商品名称', category: '商品品类', brand: '品牌', model: '型号 / SKU',
  material: '材质', color: '颜色', size: '尺寸', weight: '重量', capacity: '容量 / 净含量',
  package: '包装清单', sellingPoints: '历史核心卖点', audience: '适用人群', scene: '使用场景', notes: '补充说明',
  description: '商品卖点与说明',
}
export const productExamples: Record<string, string> = {
  name: '填写实际商品名称', category: '如：跑步鞋、保湿面霜、蓝牙耳机', brand: '填写实际品牌', model: '填写实际型号或货号',
  material: '填写实际材质', color: '填写可选颜色', size: '填写尺码或长 × 宽 × 高及单位', weight: '填写实际重量及单位',
  capacity: '填写实际容积及单位', package: '填写包装内物品和数量', sellingPoints: '填写已有依据的商品特点',
  description: '介绍商品用途、特色及适用条件', origin: '填写实际产地', price: '填写售价、币种及适用条件',
  promotion: '填写优惠内容、有效期与适用条件', warranty: '填写实际售后政策',
  fabric: '如：棉 95%、氨纶 5%', storage: '如：256 GB', memory: '如：8 GB', net_content: '如：500 g / 200 mL',
  audience: '填写实际适用人群', scene: '填写实际使用场景', notes: '其他需要在创作中保留的商品事实',
}
export const parameterLabels: Record<string, string> = {
  length: '文案长度', tone: '表达语气', purpose: '图片用途', ratio: '比例 / 尺寸', aspect_ratio: '画面比例', duration_seconds: '视频时长（秒）',
  style: '画面风格', count: '生成张数', duration: '时长', resolution: '分辨率', voice: '配音',
  captions: '字幕', subtitles: '字幕', music: '背景音乐', size: '图片尺寸',
  copy_type: '文案类型', platform: '目标平台', audience: '目标人群', max_chars: '最大字符数',
  extra_instructions: '额外协作要求', language: '文案语言', output_type: '图片用途', first_frame_file_id: '视频首帧',
}
export function fieldLabel(key: string, category: 'product' | 'parameter', index = 0) {
  return (category === 'product' ? productLabels : parameterLabels)[key] || `${category === 'product' ? '扩展资料' : '扩展设置'} ${index + 1}`
}
export function displayValue(value: unknown) {
  if (typeof value === 'boolean') return value ? '开启' : '关闭'
  if (value === null || value === undefined || value === '') return '未填写'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}
export function labeledEntries(values: Record<string, unknown> | undefined, category: 'product' | 'parameter') {
  return Object.entries(values || {}).filter(([, value]) => value !== '' && value !== null && value !== undefined)
    .filter(([key, value]) => category !== 'product' || key !== 'sellingPoints' || typeof value !== 'string' ||
      typeof values?.description !== 'string' || value.trim() !== values.description.trim())
    .map(([key, value], index) => ({ key, label: fieldLabel(key, category, index), value: category === 'product' && key === 'product_type' ? productType(value)?.label || displayValue(value) : displayValue(value) }))
}
export function parameterSummary(values: Record<string, unknown> | undefined) {
  return labeledEntries(values, 'parameter').map(item => `${item.label}：${item.value}`).join(' / ')
}
