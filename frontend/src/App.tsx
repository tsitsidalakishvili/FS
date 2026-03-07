import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { EventDetailPage } from './pages/EventDetailPage'
import { EventsPage } from './pages/EventsPage'
import { PeopleCreatePage } from './pages/PeopleCreatePage'
import { PeopleDetailPage } from './pages/PeopleDetailPage'
import { PeopleListPage } from './pages/PeopleListPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { PublicEventRegistrationPage } from './pages/PublicEventRegistrationPage'
import { TasksPage } from './pages/TasksPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/people" replace />} />
      <Route element={<AppLayout />}>
        <Route path="/app/people" element={<PeopleListPage />} />
        <Route path="/app/people/new" element={<PeopleCreatePage />} />
        <Route path="/app/people/:personId" element={<PeopleDetailPage />} />
        <Route path="/app/tasks" element={<TasksPage />} />
        <Route path="/app/events" element={<EventsPage />} />
        <Route path="/app/events/:eventId" element={<EventDetailPage />} />
      </Route>
      <Route path="/public/event-registration" element={<PublicEventRegistrationPage />} />
      <Route
        path="/public/questionnaire"
        element={<PlaceholderPage title="Questionnaire route preserved" />}
      />
      <Route path="/public/survey" element={<PlaceholderPage title="Survey route preserved" />} />
      <Route path="*" element={<Navigate to="/app/people" replace />} />
    </Routes>
  )
}

export default App
