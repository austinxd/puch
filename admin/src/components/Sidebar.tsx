import { NavLink } from 'react-router-dom'

const links = [
  { to: '/properties', label: 'Propiedades', icon: '🏠' },
  { to: '/agents', label: 'Agentes', icon: '👤' },
  { to: '/appointments', label: 'Citas', icon: '📅' },
  { to: '/assistant', label: 'Asistente', icon: '💬' },
  { to: '/analytics', label: 'Análisis', icon: '📊' },
  { to: '/prompt', label: 'Prompt', icon: '🤖' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <h1 className="text-2xl font-bold tracking-tight">Brikia</h1>
        <p className="text-gray-400 text-sm mt-1">Panel de Administración</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <span>{link.icon}</span>
            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
