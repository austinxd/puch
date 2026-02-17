import { Routes, Route, Navigate } from 'react-router-dom'
import AdminLayout from './layouts/AdminLayout'
import PropertyList from './pages/Properties/PropertyList'
import PropertyForm from './pages/Properties/PropertyForm'
import PropertyDetail from './pages/Properties/PropertyDetail'
import AgentList from './pages/Agents/AgentList'
import AgentForm from './pages/Agents/AgentForm'
import AssistantChat from './pages/Assistant/AssistantChat'

function App() {
  return (
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
        <Route path="/assistant" element={<AssistantChat />} />
      </Routes>
    </AdminLayout>
  )
}

export default App
