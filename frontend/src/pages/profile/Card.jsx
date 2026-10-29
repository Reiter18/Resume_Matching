export default function Card({ title, children, danger = false }) {
  return (
    <section className={`rounded-lg border bg-white p-5 ${danger ? 'border-red-200' : 'border-slate-200'}`}>
      <h2 className={`mb-3 font-semibold ${danger ? 'text-red-700' : ''}`}>{title}</h2>
      {children}
    </section>
  )
}

export const inputClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500'
export const buttonClass = 'rounded-md bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-60'
