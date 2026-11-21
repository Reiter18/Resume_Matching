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

export const CRITERIA = {
  skills: 'Навыки', work_format: 'Формат работы', salary: 'Зарплата', location: 'Место',
  employment_type: 'Тип занятости', experience: 'Опыт', schedule: 'График', hours: 'Часы в неделю',
}  // prettier-ignore

export function vacancyFacts(v) {
  return [
    formatSalary(v),
    WORK_FORMATS[v.work_format],
    ...v.employment_types.map((t) => EMPLOYMENT[t] || t),
    SCHEDULES[v.schedule],
    v.hours_per_week && `${v.hours_per_week} ч/нед`,
    v.experience_years_min != null && `опыт от ${v.experience_years_min} лет`,
  ].filter(Boolean)
}
