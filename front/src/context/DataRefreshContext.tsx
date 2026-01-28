"use client"

import { createContext, useContext, useState, useCallback, type ReactNode } from "react"

interface DataRefreshContextType {
  refreshKey: number
  triggerRefresh: () => void
}

const DataRefreshContext = createContext<DataRefreshContextType | undefined>(undefined)

export function DataRefreshProvider({ children }: { children: ReactNode }) {
  const [refreshKey, setRefreshKey] = useState(0)

  const triggerRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1)
  }, [])

  return (
    <DataRefreshContext.Provider value={{ refreshKey, triggerRefresh }}>
      {children}
    </DataRefreshContext.Provider>
  )
}

export function useDataRefresh() {
  const context = useContext(DataRefreshContext)
  if (!context) {
    throw new Error("useDataRefresh must be used within DataRefreshProvider")
  }
  return context
}
