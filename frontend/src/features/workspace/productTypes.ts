export const productTypes = [
  { value: 'clothing', label: '服饰内衣', fields: ['fabric', 'size', 'color', 'fit', 'season', 'care', 'package'] },
  { value: 'shoes_bags', label: '鞋靴箱包', fields: ['material', 'size', 'color', 'lining', 'sole_material', 'weight', 'package'] },
  { value: 'beauty', label: '美妆个护', fields: ['skin_type', 'ingredients', 'net_content', 'shelf_life', 'usage', 'package'] },
  { value: 'food', label: '食品饮料', fields: ['flavor', 'net_content', 'ingredients', 'allergens', 'shelf_life', 'storage_conditions', 'package'] },
  { value: 'digital', label: '数码电子', fields: ['processor', 'memory', 'storage', 'screen', 'battery', 'connectivity', 'compatibility', 'package'] },
  { value: 'home', label: '家居日用', fields: ['material', 'color', 'size', 'weight', 'capacity', 'package'] },
  { value: 'appliances', label: '家用电器', fields: ['power', 'voltage', 'energy_rating', 'size', 'weight', 'functions', 'package'] },
  { value: 'sports', label: '运动户外', fields: ['sport', 'material', 'size', 'weight', 'waterproof', 'package'] },
  { value: 'baby', label: '母婴玩具', fields: ['age_range', 'material', 'safety_standard', 'size', 'weight', 'package'] },
  { value: 'other', label: '其他商品', fields: ['material', 'color', 'size', 'weight', 'technical_specs', 'package'] },
]
export function productType(value: unknown) { return productTypes.find(type => type.value === value) }
export function productFormGroups(value: unknown) {
  return [
    { title: '基本信息', fields: ['name', 'product_type', 'category', 'brand', 'origin'] },
    { title: '规格参数', fields: productType(value)?.fields || ['material', 'color', 'size', 'weight', 'capacity', 'package'] },
    { title: '卖点与使用场景', fields: ['description', 'audience', 'scene', 'price', 'promotion', 'warranty', 'notes'] },
  ]
}
export const longProductFields = ['description', 'sellingPoints', 'notes', 'technical_specs', 'functions', 'usage']

/** Normalize a new editable version; persisted snapshots stay intact. */
export function editableProduct(values: Record<string, unknown>, requiredFields: string[] = []) {
  const product = { ...values }
  if (!requiredFields.includes('model')) delete product.model
  const description = typeof product.description === 'string' ? product.description.trim() : ''
  const points = typeof product.sellingPoints === 'string' ? product.sellingPoints.trim() : ''
  if (points && (!description || description === points)) {
    if (requiredFields.includes('sellingPoints') && !requiredFields.includes('description')) delete product.description
    else { product.description = description || points; delete product.sellingPoints }
  }
  return product
}
