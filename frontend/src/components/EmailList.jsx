import { EmailCard } from './EmailCard'

export function EmailList({ emails, loading, error, onFeedback }) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white border border-gray-200 rounded-lg p-4 animate-pulse"
          >
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-3/4" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
        {error}
      </div>
    )
  }

  if (emails.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-8 text-center text-gray-500">
        No emails found. Try syncing your inbox.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {emails.map((email) => (
        <EmailCard key={email.id} email={email} onFeedback={onFeedback} />
      ))}
    </div>
  )
}
