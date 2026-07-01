/** Quick action buttons — common tasks one click away. */

import { useNavigate } from 'react-router-dom'
import { MessageSquare, Upload, Brain, User } from 'lucide-react'

export function QuickActions() {
  const navigate = useNavigate()

  const actions = [
    {
      label: 'New Chat',
      description: 'Start a conversation',
      icon: MessageSquare,
      color: 'bg-primary-500 hover:bg-primary-600',
      onClick: () => navigate('/chat'),
    },
    {
      label: 'Upload File',
      description: 'Add a document',
      icon: Upload,
      color: 'bg-accent-500 hover:bg-accent-600',
      onClick: () => navigate('/storage'),
    },
    {
      label: 'Knowledge Base',
      description: 'Semantic search & RAG',
      icon: Brain,
      color: 'bg-indigo-500 hover:bg-indigo-600',
      onClick: () => navigate('/knowledge'),
    },
    {
      label: 'Edit Profile',
      description: 'Update your account',
      icon: User,
      color: 'bg-surface-500 hover:bg-surface-600',
      onClick: () => navigate('/profile'),
    },
  ]

  return (
    <div className="rounded-xl border border-surface-200 bg-white dark:border-surface-800 dark:bg-surface-950">
      <div className="border-b border-surface-200 px-4 py-3 dark:border-surface-800">
        <h3 className="text-sm font-semibold text-surface-900 dark:text-white">
          Quick Actions
        </h3>
      </div>
      <div className="grid grid-cols-1 gap-1 p-3 sm:grid-cols-2 lg:grid-cols-4">
        {actions.map(({ label, description, icon: Icon, color, onClick }) => (
          <button
            key={label}
            onClick={onClick}
            className="flex flex-col items-center gap-2 rounded-xl p-4 text-white transition-colors"
          >
            <div className={`rounded-lg p-2.5 ${color}`}>
              <Icon size={20} />
            </div>
            <span className="text-sm font-medium text-surface-900 dark:text-white">
              {label}
            </span>
            <span className="text-xs text-surface-500">{description}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
