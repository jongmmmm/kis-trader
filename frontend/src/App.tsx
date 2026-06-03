import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import ErrorBoundary from './components/common/ErrorBoundary'
import ProtectedRoute from './components/common/ProtectedRoute'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './components/auth/LoginPage'
import SignupPage from './components/auth/SignupPage'
import RegisterFingerprintPage from './components/auth/RegisterFingerprintPage'
import DashboardPage from './components/dashboard/DashboardPage'
import StrategiesPage from './components/strategies/StrategiesPage'
import OrdersPage from './components/orders/OrdersPage'
import SettingsPage from './components/settings/SettingsPage'
import ChatPage from './components/chat/ChatPage'
import EsgPage from './components/esg/EsgPage'

export default function App() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/register-fingerprint" element={<RegisterFingerprintPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/strategies" element={<StrategiesPage />} />
              <Route path="/orders" element={<OrdersPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/esg" element={<EsgPage />} />
            </Route>
          </Route>
        </Routes>
      </ErrorBoundary>
    </AuthProvider>
  )
}
