import { Routes, Route, Navigate } from 'react-router-dom'
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

function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/privacy" element={<PrivacyPolicy />} />

      {/* Admin */}
      <Route path="/*" element={
        <AdminLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/properties" replace />} />
            <Route path="/properties" element={<PropertyList />} />
            <Route path="/properties/new" element={<PropertyForm />} />
            <Route path="/properties/:id/edit" element={<PropertyForm />} />
            <Route path="/properties/:id" element={<PropertyDetail />} />
            <Route path="/agents" element={<AgentList />} />
            <Route path="/agents/new" element={<AgentForm />} />
            <Route path="/agents/:id/edit" element={<AgentForm />} />
            <Route path="/appointments" element={<AppointmentList />} />
            <Route path="/assistant" element={<AssistantChat />} />
            <Route path="/analytics" element={<AnalyticsDashboard />} />
            <Route path="/prompt" element={<PromptEditor />} />
          </Routes>
        </AdminLayout>
      } />
    </Routes>
  )
}

export default App
