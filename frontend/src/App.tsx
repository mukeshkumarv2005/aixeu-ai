import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { HomePage } from '@/pages/home'
import { AuthLayout } from '@/components/auth/auth-layout'
import { ProtectedRoute } from '@/components/auth/protected-route'
import LoginPage from '@/pages/auth/login'
import RegisterPage from '@/pages/auth/register'
import ForgotPasswordPage from '@/pages/auth/forgot-password'
import ResetPasswordPage from '@/pages/auth/reset-password'
import VerifyEmailPage from '@/pages/auth/verify-email'
import ProfilePage from '@/pages/profile/index'
import StoragePage from '@/pages/storage/index'
import ChatPage from '@/pages/chat/index'
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

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="profile" element={<ProfilePage />} />
        <Route path="storage" element={<StoragePage />} />
        <Route path="chat" element={<ChatPage />} />
      </Route>
    </Routes>
  )
}
