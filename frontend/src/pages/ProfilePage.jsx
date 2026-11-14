import { useAuth } from '../auth/AuthContext.jsx'
import Card from './profile/Card.jsx'
import DeleteAccount from './profile/DeleteAccount.jsx'
import NameForm from './profile/NameForm.jsx'
import PasswordForm from './profile/PasswordForm.jsx'
import ResumeCard from './profile/ResumeCard.jsx'

export default function ProfilePage() {
  const { user } = useAuth()
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Профиль и резюме</h1>
      <Card title="Аккаунт">
        <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
          <dt className="text-slate-500">Email</dt>
          <dd>{user.email}</dd>
          <dt className="text-slate-500">Регистрация</dt>
          <dd>{new Date(user.created_at).toLocaleDateString('ru-RU')}</dd>
        </dl>
        <NameForm key={user.full_name ?? ''} />
      </Card>
      <Card title="Резюме">
        <ResumeCard />
      </Card>
      <Card title="Смена пароля">
        <PasswordForm />
      </Card>
      <Card title="Удаление аккаунта" danger>
        <DeleteAccount />
      </Card>
    </div>
  )
}
