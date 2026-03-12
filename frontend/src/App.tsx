import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from './layout/AppShell'
import { CrmPage } from './pages/CrmPage'
import { DeliberationPage } from './pages/DeliberationPage'
import { DueDiligencePage } from './pages/DueDiligencePage'
import { HomePage } from './pages/HomePage'

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route element={<HomePage />} path="/" />
          <Route element={<CrmPage />} path="/crm" />
          <Route element={<DeliberationPage />} path="/deliberation" />
          <Route element={<DueDiligencePage />} path="/due-diligence" />
          <Route element={<Navigate replace to="/" />} path="*" />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}

export default App
