import { useCallback, useEffect, useState } from 'react'
import apiClient from '../api/client'

export function usePreferences() {
  const [preferences, setPreferences] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const fetchPreferences = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await apiClient.get('/api/preferences')
      setPreferences(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load preferences')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPreferences()
  }, [fetchPreferences])

  const updatePreferences = useCallback(async (updates) => {
    setSaving(true)
    setError(null)
    try {
      const res = await apiClient.put('/api/preferences', updates)
      setPreferences(res.data)
      return true
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save preferences')
      return false
    } finally {
      setSaving(false)
    }
  }, [])

  return { preferences, loading, saving, error, updatePreferences }
}
