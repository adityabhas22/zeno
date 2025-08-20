import { useUser } from '@clerk/clerk-react'
import { useState, useEffect } from 'react'

interface User {
  id: string
  firstName: string | null
  lastName: string | null
  emailAddresses: Array<{ emailAddress: string }>
}

export default function Dashboard() {
  const { user, isLoaded } = useUser()
  const [briefing, setBriefing] = useState<string>('')
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isLoaded && user) {
      // Simulate fetching user data
      // Later we'll replace this with actual API calls
      setTimeout(() => {
        setBriefing("Good morning! Here's your day ahead...")
        setTasks([
          { id: 1, title: "Review morning emails", completed: false },
          { id: 2, title: "Daily planning session", completed: false },
          { id: 3, title: "Team standup meeting", completed: false }
        ])
        setLoading(false)
      }, 1000)
    }
  }, [isLoaded, user])

  if (!isLoaded || loading) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.firstName || 'there'}!
        </h1>
        <p className="text-gray-600">
          Here's what Zeno has prepared for you today.
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Today's Tasks</h3>
          <p className="text-3xl font-bold text-blue-600">{tasks.length}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Meetings</h3>
          <p className="text-3xl font-bold text-green-600">3</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Priority Items</h3>
          <p className="text-3xl font-bold text-red-600">2</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Morning Briefing */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Morning Briefing</h2>
          <div className="prose text-gray-600">
            <p>{briefing}</p>
            <button className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
              Get Full Briefing
            </button>
          </div>
        </div>

        {/* Today's Tasks */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Today's Tasks</h2>
          <div className="space-y-3">
            {tasks.map((task) => (
              <div key={task.id} className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  checked={task.completed}
                  onChange={() => {
                    setTasks(tasks.map(t => 
                      t.id === task.id ? { ...t, completed: !t.completed } : t
                    ))
                  }}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className={task.completed ? 'line-through text-gray-400' : 'text-gray-900'}>
                  {task.title}
                </span>
              </div>
            ))}
          </div>
          <button className="mt-4 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
            Add Task
          </button>
        </div>
      </div>

      {/* Zeno Chat Interface */}
      <div className="mt-8 bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Chat with Zeno</h2>
        <div className="border rounded-lg p-4 h-64 mb-4 bg-gray-50 overflow-y-auto">
          <div className="text-gray-500 text-center mt-20">
            Start a conversation with your AI assistant...
          </div>
        </div>
        <div className="flex space-x-2">
          <input
            type="text"
            placeholder="Ask Zeno anything..."
            className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md font-medium transition-colors">
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
