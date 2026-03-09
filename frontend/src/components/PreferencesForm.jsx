import { useState } from 'react'

export function PreferencesForm({ preferences, saving, onSave }) {
  const [senders, setSenders] = useState(
    (preferences?.important_senders || []).join(', ')
  )
  const [keywords, setKeywords] = useState(
    (preferences?.important_keywords || []).join(', ')
  )

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave({
      important_senders: senders
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      important_keywords: keywords
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label
          htmlFor="senders"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Important Senders
        </label>
        <textarea
          id="senders"
          rows={3}
          value={senders}
          onChange={(e) => setSenders(e.target.value)}
          placeholder="boss@company.com, cto@company.com"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Comma-separated email addresses that should always be high priority.
        </p>
      </div>

      <div>
        <label
          htmlFor="keywords"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Important Keywords
        </label>
        <textarea
          id="keywords"
          rows={3}
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="urgent, deadline, invoice"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Comma-separated keywords that indicate high-priority emails.
        </p>
      </div>

      <button
        type="submit"
        disabled={saving}
        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? 'Saving...' : 'Save Preferences'}
      </button>
    </form>
  )
}
