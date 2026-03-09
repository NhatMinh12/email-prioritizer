import { memo } from 'react'

const PRIORITY_STYLES = {
  high: 'bg-priority-high text-white',
  medium: 'bg-priority-medium text-white',
  low: 'bg-priority-low text-white',
}

const URGENCY_LABELS = {
  urgent: 'Urgent',
  time_sensitive: 'Time-sensitive',
  normal: 'Normal',
  low: 'Low',
}

export const PriorityBadge = memo(function PriorityBadge({ priority, urgency }) {
  const style = PRIORITY_STYLES[priority] || 'bg-gray-200 text-gray-700'

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${style}`}
      >
        {priority}
      </span>
      {urgency && urgency !== 'normal' && (
        <span className="text-xs text-gray-500">
          {URGENCY_LABELS[urgency] || urgency}
        </span>
      )}
    </div>
  )
})
