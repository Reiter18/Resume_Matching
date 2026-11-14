export default function Placeholder({ title, week }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">Экран будет реализован на {week}-й неделе.</p>
    </section>
  )
}
