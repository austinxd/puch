import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AdminLayout from './layouts/AdminLayout'
import PropertyList from './pages/Properties/PropertyList'
import PropertyForm from './pages/Properties/PropertyForm'
import PropertyDetail from './pages/Properties/PropertyDetail'
import AgentList from './pages/Agents/AgentList'
import AgentForm from './pages/Agents/AgentForm'
import AppointmentList from './pages/Appointments/AppointmentList'
import AssistantChat from './pages/Assistant/AssistantChat'
import AnalyticsDashboard from './pages/Analytics/AnalyticsDashboard'
import PromptEditor from './pages/Prompt/PromptEditor'
import PrivacyPolicy from './pages/Legal/PrivacyPolicy'
import Login from './pages/Login/Login'
import MyProfile from './pages/Profile/MyProfile'

function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />

        {/* Protected */}
        <Route path="/*" element={
          <ProtectedRoute>
            <AdminLayout>
              <Routes>
                <Route path="/" element={<Navigate to="/properties" replace />} />
                <Route path="/properties" element={<PropertyList />} />
                <Route path="/properties/new" element={<PropertyForm />} />
                <Route path="/properties/:id/edit" element={<PropertyForm />} />
                <Route path="/properties/:id" element={<PropertyDetail />} />
                <Route path="/appointments" element={<AppointmentList />} />
                <Route path="/assistant" element={<AssistantChat />} />
                <Route path="/profile" element={<MyProfile />} />

                {/* Admin only */}
                <Route path="/agents" element={
                  <ProtectedRoute adminOnly><AgentList /></ProtectedRoute>
                } />
                <Route path="/agents/new" element={
                  <ProtectedRoute adminOnly><AgentForm /></ProtectedRoute>
                } />
                <Route path="/agents/:id/edit" element={
                  <ProtectedRoute adminOnly><AgentForm /></ProtectedRoute>
                } />
                <Route path="/analytics" element={
                  <ProtectedRoute adminOnly><AnalyticsDashboard /></ProtectedRoute>
                } />
                <Route path="/prompt" element={
                  <ProtectedRoute adminOnly><PromptEditor /></ProtectedRoute>
                } />
              </Routes>
            </AdminLayout>
          </ProtectedRoute>
        } />
      </Routes>
    </AuthProvider>
  )
}

export default App
