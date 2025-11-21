
interface Props {
  stats: any
  apiKeys: any
}

export default function StatsPanel({ stats, apiKeys }: Props) {
  console.log('[StatsPanel] Rendering with stats:', stats)
  if (!stats) {
    console.log('[StatsPanel] No stats data, returning null')
    return null
  }

  const topCategories = Object.entries(stats.categories || {})
    .sort((a: any, b: any) => b[1].points - a[1].points)
    .slice(0, 3)

  return (
    <div className="bg-terminal-surface border border-terminal-border rounded p-6">
      <div className="mb-6 pb-2 border-b border-terminal-border">
        <h2 className="text-terminal-accent text-xl m-0">System Status</h2>
      </div>

      <div className="mb-8">
        <h3 className="text-terminal-accent text-base mb-4 font-semibold">API Keys</h3>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(100px,1fr))] gap-3">
          <div className={`flex items-center gap-2 px-4 py-3 rounded border text-sm ${
            apiKeys.OPENROUTER_API_KEY
              ? 'bg-green-950 border-terminal-accent text-terminal-accent'
              : 'bg-red-950 border-red-600 text-red-400'
          }`}>
            <span className="text-sm">{apiKeys.OPENROUTER_API_KEY ? 'OK' : 'Missing'}</span>
            <span className="text-sm">OpenRouter</span>
          </div>
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-terminal-accent text-base mb-4 font-semibold">Benchmark Statistics</h3>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(120px,1fr))] gap-4">
          <div className="bg-zinc-900 p-5 rounded border border-terminal-border hover:border-gray-600">
            <div className="text-xs text-gray-400 uppercase mb-1">Total Tests</div>
            <div className="text-3xl font-bold text-terminal-accent leading-none">{stats.total_tests}</div>
          </div>

          <div className="bg-zinc-900 p-5 rounded border border-terminal-border hover:border-gray-600">
            <div className="text-xs text-gray-400 uppercase mb-1">Total Points</div>
            <div className="text-3xl font-bold text-terminal-accent leading-none">{stats.total_points}</div>
          </div>

          <div className="bg-zinc-900 p-5 rounded border border-terminal-border hover:border-gray-600">
            <div className="text-xs text-gray-400 uppercase mb-1">Categories</div>
            <div className="text-3xl font-bold text-terminal-accent leading-none">{Object.keys(stats.categories || {}).length}</div>
          </div>

          <div className="bg-zinc-900 p-5 rounded border border-terminal-border hover:border-gray-600">
            <div className="text-xs text-gray-400 uppercase mb-1">Difficulty Levels</div>
            <div className="text-3xl font-bold text-terminal-accent leading-none">10</div>
          </div>
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-terminal-accent text-base mb-4 font-semibold">Top Categories (by points)</h3>
        <div className="flex flex-col gap-3">
          {topCategories.map(([name, data]: [string, any], index) => (
            <div key={name} className="flex items-center gap-4 p-4 bg-zinc-900 rounded border-l-3 border border-terminal-border hover:bg-zinc-800">
              <span className="w-8 h-8 flex items-center justify-center bg-terminal-border text-terminal-accent rounded font-bold text-sm">#{index + 1}</span>
              <div className="flex-1 flex flex-col gap-1">
                <span className="text-gray-300 font-medium">{name}</span>
                <span className="text-xs text-gray-500">
                  {data.count} tests • {data.points} points
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <h3 className="text-terminal-accent text-base mb-4 font-semibold">Level Distribution</h3>
        <div className="flex flex-col gap-2">
          {Object.entries(stats.levels || {})
            .sort((a, b) => {
              const levelA = parseInt(a[0].replace('level_', ''))
              const levelB = parseInt(b[0].replace('level_', ''))
              return levelA - levelB
            })
            .map(([level, data]: [string, any]) => {
              const levelNum = parseInt(level.replace('level_', ''))
              const percentage = (data.count / stats.total_tests) * 100
              return (
                <div key={level} className="grid grid-cols-[30px_1fr_40px] items-center gap-3">
                  <span className="text-sm text-gray-400 font-semibold">L{levelNum}</span>
                  <div className="h-5 bg-terminal-border rounded overflow-hidden">
                    <div
                      className="h-full bg-terminal-accent transition-all duration-700"
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <span className="text-sm text-terminal-accent font-semibold text-right">{data.count}</span>
                </div>
              )
            })}
        </div>
      </div>
    </div>
  )
}
