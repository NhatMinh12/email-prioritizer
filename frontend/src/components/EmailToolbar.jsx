const PRIORITY_OPTIONS = [
  { value: '', label: 'All priorities' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

export function EmailToolbar({
  priorityFilter,
  onFilterChange,
  onSync,
  onClassify,
  syncing,
  classifying,
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <select
        value={priorityFilter}
        onChange={(e) => onFilterChange(e.target.value)}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {PRIORITY_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <div className="flex gap-2">
        <button
          onClick={onSync}
          disabled={syncing}
          className="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {syncing ? 'Syncing...' : 'Sync Inbox'}
        </button>
        <button
          onClick={onClassify}
          disabled={classifying}
          className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {classifying ? 'Classifying...' : 'Classify'}
        </button>
      </div>
    </div>
  )
}
