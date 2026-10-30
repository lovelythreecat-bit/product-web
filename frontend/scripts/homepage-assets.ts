import { readFileSync } from 'node:fs'
import type { Plugin } from 'vite'

/** Only the two approved homepage illustrations are published from public/. */
export function homepageAssets(): Plugin {
  return {
    name: 'published-homepage-assets',
    apply: 'build',
    generateBundle() {
      for (const filename of ['commerce-hero-v3.png', 'commerce-categories-v3.png']) {
        this.emitFile({
          type: 'asset',
          fileName: `homepage/${filename}`,
          source: readFileSync(new URL(`../public/homepage/${filename}`, import.meta.url)),
        })
      }
    },
  }
}
