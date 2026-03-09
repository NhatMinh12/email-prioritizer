import { EmailList } from '../components/EmailList'
import { EmailToolbar } from '../components/EmailToolbar'
import { Pagination } from '../components/Pagination'
import { useEmails } from '../hooks/useEmails'

export default function Dashboard() {
  const {
    emails,
    total,
    page,
    pageSize,
    priorityFilter,
    loading,
    error,
    syncing,
    classifying,
    statusMessage,
    syncInbox,
    classifyEmails,
    submitFeedback,
    changePage,
    changeFilter,
    dismissStatus,
  } = useEmails()

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Email Dashboard</h2>

      {statusMessage && (
        <div className="mb-4 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <span className="text-sm text-blue-700">{statusMessage}</span>
          <button
            onClick={dismissStatus}
            className="text-blue-400 hover:text-blue-600 ml-4"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      )}

      <EmailToolbar
        priorityFilter={priorityFilter}
        onFilterChange={changeFilter}
        onSync={syncInbox}
        onClassify={classifyEmails}
        syncing={syncing}
        classifying={classifying}
      />

      <EmailList
        emails={emails}
        loading={loading}
        error={error}
        onFeedback={submitFeedback}
      />

      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={changePage}
      />
    </div>
  )
}
