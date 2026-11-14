export const WORK_FORMATS = { remote: 'Удалённо', hybrid: 'Гибрид', onsite: 'Офис' }
export const EMPLOYMENT = { full_time: 'Полная', part_time: 'Частичная', contract: 'Контракт', internship: 'Стажировка' }
export const SCHEDULES = { full_day: 'Полный день', flexible: 'Гибкий график', shift: 'Сменный', rotational: 'Вахта' }

export function formatSalary(v) {
  const { salary_min: min, salary_max: max, salary_currency: cur } = v
  if (!min && !max) return null
  const n = (x) => x.toLocaleString('ru-RU')
  const range = min && max ? `${n(min)}–${n(max)}` : min ? `от ${n(min)}` : `до ${n(max)}`
  return `${range} ${cur || ''}/мес`
}
