import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './auth/ProtectedRoute.jsx'
import FeedPage from './pages/FeedPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import Placeholder from './pages/Placeholder.jsx'
import PreferencesPage from './pages/PreferencesPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import VacancyPage from './pages/VacancyPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/s/:token" element={<Placeholder title="Публичная подборка" week={11} />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<FeedPage />} />
          <Route path="vacancies/:id" element={<VacancyPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="preferences" element={<PreferencesPage />} />
          <Route path="notifications" element={<Placeholder title="Уведомления" week={10} />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
