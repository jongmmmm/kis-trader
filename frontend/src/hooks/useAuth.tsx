import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { apiLogin, apiLogout, apiMe } from '../api/auth'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (username: string, password: string, remember: boolean) => Promise<{ success: boolean; msg?: string }>
  logout: () => Promise<void>
  setUser: (user: User | null) => void
}

const AuthContext = createContext<AuthContextType>(null!)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiMe()
      .then(d => { if (d.authenticated) setUser(d.user) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username: string, password: string, remember: boolean) => {
    try {
      const d = await apiLogin(username, password, remember)
      if (d.success) setUser(d.user)
      return d
    } catch (e: unknown) {
      return { success: false, msg: (e as Error).message }
    }
  }, [])

  const logout = useCallback(async () => {
    await apiLogout().catch(() => {})
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
