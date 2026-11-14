import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './auth/ProtectedRoute.jsx'
import LoginPage from './pages/LoginPage.jsx'
import Placeholder from './pages/Placeholder.jsx'
import ProfilePage from './pages/ProfilePage.jsx'

export default function App() {
  return (
    <Routes>
      {/* публичные страницы без шапки приложения */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/s/:token" element={<Placeholder title="Публичная подборка" week={11} />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Placeholder title="Лента вакансий" week={5} />} />
          <Route path="vacancies/:id" element={<Placeholder title="Вакансия и разбор оценки" week={8} />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="preferences" element={<Placeholder title="Что вы ищете" week={6} />} />
          <Route path="notifications" element={<Placeholder title="Уведомления" week={10} />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
