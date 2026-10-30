import { ref } from 'vue'
import { getSiteBrand } from '../../api/site'
import type { Schema } from '../../types/api'

export const brandName = ref('映作')
let revision = 0
export function applyBrand(brand: Schema<'SiteBrandView'>) {
  revision++
  brandName.value = brand.name
  document.title = `${brand.name} · 电商 AI 创作平台`
}
export async function refreshBrand() {
  const startedAt = revision
  const brand = await getSiteBrand()
  if (startedAt === revision) applyBrand(brand)
  return brand
}
