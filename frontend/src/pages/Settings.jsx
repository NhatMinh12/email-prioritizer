import { PreferencesForm } from '../components/PreferencesForm'
import { usePreferences } from '../hooks/usePreferences'

export default function Settings() {
  const { preferences, loading, saving, error, updatePreferences } =
    usePreferences()

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>

      <div className="bg-white rounded-lg shadow p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/4" />
            <div className="h-20 bg-gray-200 rounded" />
            <div className="h-4 bg-gray-200 rounded w-1/4" />
            <div className="h-20 bg-gray-200 rounded" />
          </div>
        ) : (
          preferences && (
            <PreferencesForm
              preferences={preferences}
              saving={saving}
              onSave={updatePreferences}
            />
          )
        )}
      </div>
    </div>
  )
}
