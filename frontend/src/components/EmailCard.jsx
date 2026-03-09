import { memo, useState } from 'react'
import { PriorityBadge } from './PriorityBadge'

export const EmailCard = memo(function EmailCard({ email, onFeedback }) {
  const [expanded, setExpanded] = useState(false)
  const { classification } = email

  const formattedDate = new Date(email.received_at).toLocaleDateString(
    undefined,
    { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
  )

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900 truncate">
              {email.sender}
            </span>
            {email.has_attachments && (
              <svg
                className="w-4 h-4 text-gray-400 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                />
              </svg>
            )}
            {email.thread_length > 1 && (
              <span className="text-xs text-gray-400 flex-shrink-0">
                ({email.thread_length})
              </span>
            )}
          </div>
          <h3 className="text-sm text-gray-800 font-medium truncate">
            {email.subject}
          </h3>
          {email.body_preview && (
            <p className="text-xs text-gray-500 mt-1 truncate">
              {email.body_preview}
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <span className="text-xs text-gray-400">{formattedDate}</span>
          {classification && (
            <PriorityBadge
              priority={classification.priority}
              urgency={classification.urgency}
            />
          )}
        </div>
      </div>

      {expanded && classification && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-sm text-gray-600 mb-2">{classification.reason}</p>

          {classification.needs_response && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 mb-2">
              Needs response
            </span>
          )}

          {classification.action_items?.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-500 mb-1">
                Action items:
              </p>
              <ul className="list-disc list-inside text-xs text-gray-600 space-y-0.5">
                {classification.action_items.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {onFeedback && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs text-gray-500">Was this accurate?</span>
              {['correct', 'incorrect'].map((type) => (
                <button
                  key={type}
                  onClick={(e) => {
                    e.stopPropagation()
                    onFeedback(email.id, type)
                  }}
                  disabled={classification.feedback === type}
                  className={`text-xs px-2 py-1 rounded border transition-colors ${
                    classification.feedback === type
                      ? 'bg-gray-100 text-gray-500 border-gray-200'
                      : 'border-gray-300 hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  {type === 'correct' ? 'Yes' : 'No'}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {expanded && !classification && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-400 italic">Not yet classified</p>
        </div>
      )}
    </div>
  )
})
