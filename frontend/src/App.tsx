import { useState } from 'react'

import UserApp from './App.jsx'
import { OperatorPage } from './pages/OperatorPage'

type View = 'user' | 'operator'

function App() {
  const [view, setView] =
    useState<View>('user')

  return (
    <>
      <nav
        className="app-view-tabs"
        aria-label="화면 선택"
      >
        <button
          type="button"
          className={
            view === 'user'
              ? 'active'
              : undefined
          }
          aria-pressed={
            view === 'user'
          }
          onClick={() =>
            setView('user')
          }
        >
          이용자
        </button>
        <button
          type="button"
          className={
            view === 'operator'
              ? 'active'
              : undefined
          }
          aria-pressed={
            view === 'operator'
          }
          onClick={() =>
            setView('operator')
          }
        >
          운영자
        </button>
      </nav>

      {view === 'user'
        ? <UserApp />
        : <OperatorPage />}
    </>
  )
}

export default App
