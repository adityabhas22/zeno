import { useAuth } from '@clerk/clerk-react'
import { useState } from 'react'

interface ApiResponse {
  success: boolean
  data?: any
  error?: string
}

export default function TestBackend() {
  const { getToken } = useAuth()
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<ApiResponse | null>(null)
  const [endpoint, setEndpoint] = useState('/user/test-auth')

  const testApi = async (endpoint: string) => {
    setLoading(true)
    setResponse(null)
    
    try {
      // Get the JWT token from Clerk
      const token = await getToken()
      
      if (!token) {
        throw new Error('No auth token available')
      }

      console.log('Making API call with token:', token.substring(0, 20) + '...')
      
      // Make authenticated API call
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      console.log('Response status:', response.status)
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data = await response.json()
      console.log('Response data:', data)
      
      setResponse({ success: true, data })
    } catch (error: any) {
      console.error('API call failed:', error)
      setResponse({ 
        success: false, 
        error: error.message || 'Unknown error occurred' 
      })
    } finally {
      setLoading(false)
    }
  }

  const endpoints = [
    { path: '/user/test-auth', label: 'Test Auth' },
    { path: '/user/me', label: 'Get Profile' },
    { path: '/user/tasks', label: 'Get Tasks' },
    { path: '/user/briefings', label: 'Get Briefings' },
    { path: '/user/sessions', label: 'Get Sessions' }
  ]

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <label>
          Select endpoint to test:
          <select 
            value={endpoint} 
            onChange={(e) => setEndpoint(e.target.value)}
            style={{ marginLeft: '0.5rem', padding: '0.25rem' }}
          >
            {endpoints.map((ep) => (
              <option key={ep.path} value={ep.path}>
                {ep.label} ({ep.path})
              </option>
            ))}
          </select>
        </label>
      </div>

      <button 
        onClick={() => testApi(endpoint)}
        disabled={loading}
        style={{
          padding: '0.5rem 1rem',
          backgroundColor: loading ? '#ccc' : '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer'
        }}
      >
        {loading ? 'Testing...' : 'Test API Call'}
      </button>

      {response && (
        <div style={{ 
          marginTop: '1rem', 
          padding: '1rem', 
          backgroundColor: response.success ? '#d4edda' : '#f8d7da',
          border: `1px solid ${response.success ? '#c3e6cb' : '#f5c6cb'}`,
          borderRadius: '4px'
        }}>
          <h4 style={{ margin: '0 0 0.5rem 0' }}>
            {response.success ? '✅ Success' : '❌ Error'}
          </h4>
          
          {response.success ? (
            <pre style={{ 
              backgroundColor: '#f8f9fa', 
              padding: '0.5rem', 
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '0.9rem'
            }}>
              {JSON.stringify(response.data, null, 2)}
            </pre>
          ) : (
            <p style={{ margin: 0, color: '#721c24' }}>
              {response.error}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
