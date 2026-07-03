import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { HomePage } from '@/pages/home'
import { AuthLayout } from '@/components/auth/auth-layout'
import { ProtectedRoute } from '@/components/auth/protected-route'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import DashboardPage from '@/pages/dashboard/index'
import LoginPage from '@/pages/auth/login'
import RegisterPage from '@/pages/auth/register'
import ForgotPasswordPage from '@/pages/auth/forgot-password'
import ResetPasswordPage from '@/pages/auth/reset-password'
import VerifyEmailPage from '@/pages/auth/verify-email'
import ProfilePage from '@/pages/profile/index'
import StoragePage from '@/pages/storage/index'
import DocumentDetailsPage from '@/pages/documents/index'
import ChatPage from '@/pages/chat/index'
import KnowledgeBasePage from '@/pages/knowledge/index'
import KnowledgeBaseDetailPage from '@/pages/knowledge/detail'
import TasksPage from '@/pages/tasks/index'
import TaskDetailPage from '@/pages/tasks/detail'
import TaskCreatePage from '@/pages/tasks/create'
import SearchPage from '@/pages/search/index'
import AgentsPage from '@/pages/agents/index'
import AgentCreatePage from '@/pages/agents/new'
import AgentDetailPage from '@/pages/agents/detail'
import SettingsLayout from '@/pages/settings/index'
import AppearanceSettings from '@/pages/settings/AppearanceSettings'
import WorkspaceSettings from '@/pages/settings/WorkspaceSettings'
import AiProviders from '@/pages/settings/AiProviders'
import NotificationSettings from '@/pages/settings/NotificationSettings'
import SecuritySettings from '@/pages/settings/SecuritySettings'
import { useAuthStore } from '@/stores/auth'

export default function App() {
  const initialize = useAuthStore((s) => s.initialize)

  // Attempt silent token refresh on mount
  useEffect(() => {
    initialize()
  }, [initialize])

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<HomePage />} />

      {/* Auth routes (public, auth layout) */}
      <Route element={<AuthLayout />}>
        <Route path="auth/login" element={<LoginPage />} />
        <Route path="auth/register" element={<RegisterPage />} />
        <Route path="auth/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="auth/reset-password" element={<ResetPasswordPage />} />
        <Route path="auth/verify-email" element={<VerifyEmailPage />} />
        <Route path="auth/verify-email-notice" element={<VerifyEmailPage />} />
      </Route>

      {/* Protected routes (dashboard layout) */}
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="storage" element={<StoragePage />} />
          <Route path="storage/:fileId/documents" element={<DocumentDetailsPage />} />
          <Route path="knowledge" element={<KnowledgeBasePage />} />
          <Route path="knowledge/:kbId" element={<KnowledgeBaseDetailPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="tasks/new" element={<TaskCreatePage />} />
          <Route path="tasks/:taskId" element={<TaskDetailPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="agents/new" element={<AgentCreatePage />} />
          <Route path="agents/:agentId" element={<AgentDetailPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="settings" element={<SettingsLayout />}>
            <Route index element={<AppearanceSettings />} />
            <Route path="appearance" element={<AppearanceSettings />} />
            <Route path="workspace" element={<WorkspaceSettings />} />
            <Route path="providers" element={<AiProviders />} />
            <Route path="notifications" element={<NotificationSettings />} />
            <Route path="security" element={<SecuritySettings />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
