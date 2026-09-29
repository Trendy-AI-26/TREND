'use client'

import { useBrandsContext } from '@/components/providers/brands-provider'

export function useBrands() {
  const {
    brands, loading, error, accents, industries, brandColors, taglines,
    refetchBrands, addBrand, updateBrand, removeBrand, setAccent,
  } = useBrandsContext()

  return {
    brands, loading, error, accents, industries, brandColors, taglines,
    refetch: refetchBrands, addBrand, updateBrand, removeBrand, setAccent,
  }
}