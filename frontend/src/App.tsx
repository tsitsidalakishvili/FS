import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { AdminPage } from './pages/AdminPage'
import { DashboardPage } from './pages/DashboardPage'
import { DataPage } from './pages/DataPage'
import { DeliberationPage } from './pages/DeliberationPage'
import { DueDiligencePage } from './pages/DueDiligencePage'
import { EventDetailPage } from './pages/EventDetailPage'
import { EventsPage } from './pages/EventsPage'
import { MapPage } from './pages/MapPage'
import { OutreachPage } from './pages/OutreachPage'
import { PeopleCreatePage } from './pages/PeopleCreatePage'
import { PeopleDetailPage } from './pages/PeopleDetailPage'
import { PeopleListPage } from './pages/PeopleListPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { PublicEventRegistrationPage } from './pages/PublicEventRegistrationPage'
import { TasksPage } from './pages/TasksPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
      <Route element={<AppLayout />}>
        <Route path="/app/dashboard" element={<DashboardPage />} />
        <Route path="/app/people" element={<PeopleListPage />} />
        <Route path="/app/people/new" element={<PeopleCreatePage />} />
        <Route path="/app/people/:personId" element={<PeopleDetailPage />} />
        <Route path="/app/tasks" element={<TasksPage />} />
        <Route path="/app/outreach" element={<OutreachPage />} />
        <Route path="/app/map" element={<MapPage />} />
        <Route path="/app/events" element={<EventsPage />} />
        <Route path="/app/events/:eventId" element={<EventDetailPage />} />
        <Route path="/app/due-diligence" element={<DueDiligencePage />} />
        <Route path="/app/data" element={<DataPage />} />
        <Route path="/app/admin" element={<AdminPage />} />
        <Route path="/app/deliberation" element={<DeliberationPage />} />
      </Route>
      <Route path="/public/event-registration" element={<PublicEventRegistrationPage />} />
      <Route
        path="/public/questionnaire"
        element={<PlaceholderPage title="Questionnaire route preserved" />}
      />
      <Route path="/public/survey" element={<PlaceholderPage title="Survey route preserved" />} />
      <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
    </Routes>
  )
}

export default App
