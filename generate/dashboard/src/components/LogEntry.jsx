export default function LogEntry({ event }) {
  const colors = {
    pipeline_start: 'text-sky-400/80',
    pipeline_complete: 'text-emerald-400/80',
    pipeline_error: 'text-red-400/80',
    stage_start: 'text-sky-300/80',
    stage_complete: 'text-emerald-300/80',
    stage_error: 'text-red-300/80',
    validation: 'text-violet-400/80',
    warning: 'text-amber-400/80',
    progress: 'text-zinc-600',
  }

  if (event.event === 'progress') return null

  const isWarning = event.event === 'warning'
  const hasErrors = isWarning && event.data?.errors?.length > 0

  return (
    <div className="text-xs py-1 border-b border-zinc-800/50">
      <span className="text-zinc-600">{new Date(event.timestamp).toLocaleTimeString()}</span>
      <span className={`ml-2 ${colors[event.event] || 'text-zinc-300'}`}>{event.event}</span>
      {event.data?.stage && <span className="ml-2 text-zinc-500">[{event.data.stage}]</span>}
      {event.data?.status && <span className="ml-2 text-zinc-400">{event.data.status}</span>}
      {isWarning && event.data?.message && (
        <div className="mt-1 ml-4 text-amber-400/60">{event.data.message}</div>
      )}
      {hasErrors && (
        <div className="mt-1 ml-4 space-y-0.5">
          {event.data.errors.map((err, i) => (
            <div key={i} className="text-amber-400/50 font-mono truncate">{err}</div>
          ))}
        </div>
      )}
    </div>
  )
}
