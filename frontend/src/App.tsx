import {
  SignedIn,
  SignedOut,
  SignInButton,
  SignUpButton,
  UserButton,
  useUser
} from '@clerk/clerk-react'
import './App.css'

function App() {
  const { user } = useUser()

  return (
    <div>
      <header style={{ display: 'flex', justifyContent: 'space-between', padding: '1rem' }}>
        <h1>Zeno AI Assistant</h1>
        
        <SignedOut>
          <div>
            <SignInButton />
            <SignUpButton />
          </div>
        </SignedOut>
        
        <SignedIn>
          <UserButton />
        </SignedIn>
      </header>

      <main style={{ padding: '2rem' }}>
        <SignedOut>
          <div>
            <h2>Welcome to Zeno</h2>
            <p>Please sign in to continue</p>
            <SignInButton />
          </div>
        </SignedOut>

        <SignedIn>
          <div>
            <h2>Welcome back, {user?.firstName}!</h2>
            <p>You are successfully authenticated with Clerk.</p>
            <p>User ID: {user?.id}</p>
          </div>
        </SignedIn>
      </main>
    </div>
  )
}

export default App
