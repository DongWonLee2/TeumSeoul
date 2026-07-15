import { CATEGORIES } from '../data/places.js'

export function getCategoryMeta(contentTypeId) {
  const category = CATEGORIES.find((item) => item.id === contentTypeId) ?? CATEGORIES[0]

  return {
    ...category,
    bg: `oklch(94% 0.035 ${category.hue})`,
    stripe: `oklch(90% 0.045 ${category.hue})`,
    fg: `oklch(38% 0.14 ${category.hue})`,
    dot: `oklch(66% 0.19 ${category.hue})`,
  }
}
