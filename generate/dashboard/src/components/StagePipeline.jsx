import { formatBytes, formatDuration, formatTokens } from '../utils/format'

export default function StagePipeline({ stages, progress, validation, onRun, disabled }) {
  const stageOrder = ['fetch', 'extract', 'assemble', 'validate']
  const stageNames = {
    fetch: 'Fetch & Sanitize',
    extract: 'Deterministic Extract',
    assemble: 'LLM Assembly',
    validate: 'Validation',
  }

  const getStageProgress = (key) => {
    if (key === 'validate') {
      if (!validation) return 0
      if (validation.is_valid !== undefined) return 100
      if (validation.status?.includes('complete')) return 100
      if (validation.status?.includes('progress')) {
        return validation.total > 0 ? (validation.current / validation.total) * 100 : 50
      }
      if (validation.status?.includes('start')) return 10
      return 0
    }
    const stage = stages[key]
    if (stage.status === 'complete') return 100
    if (stage.status === 'error') return 100
    if (stage.status === 'running' && progress[key]?.total > 0) {
      return (progress[key].current / progress[key].total) * 100
    }
    if (stage.status === 'running') return 50
    return 0
  }

  const getValidationStatus = () => {
    if (!validation) return 'pending'
    if (validation.is_valid !== undefined) return validation.is_valid ? 'complete' : 'warning'
    if (validation.status?.includes('complete')) return 'complete'
    if (validation.status) return 'running'
    return 'pending'
  }

  return (
    <div className="mb-6">
      <div className="flex items-stretch h-48">
        {stageOrder.map((key, index) => {
          const isValidateStage = key === 'validate'
          const stage = isValidateStage ? null : stages[key]
          const stageProgress = getStageProgress(key)
          const validationStatus = isValidateStage ? getValidationStatus() : null

          const isRunning = isValidateStage ? validationStatus === 'running' : stage.status === 'running'
          const isComplete = isValidateStage ? (validationStatus === 'complete' || validationStatus === 'warning') : stage.status === 'complete'
          const isError = isValidateStage ? false : stage.status === 'error'
          const isWarning = isValidateStage && validationStatus === 'warning'
          const showProgress = isValidateStage
            ? (isRunning && validation?.total > 0)
            : (isRunning && progress[key]?.total > 0)

          const strict = validation?.strict_validation || validation?.strict_check

          return (
            <div
              key={key}
              className={`stage-arrow relative flex-1 transition-all duration-300 ${
                isRunning ? 'stage-running' : ''
              }`}
              style={{ marginLeft: index === 0 ? 0 : '-12px' }}
            >
              <div className="absolute inset-0 bg-zinc-800 stage-arrow-inner border-r border-zinc-700/50" />

              <div className={`absolute inset-0 stage-arrow-inner overflow-hidden ${
                isError ? 'bg-red-900/80' : ''
              } ${isWarning ? 'bg-amber-900/40' : ''}`}>
                <div
                  className={`absolute inset-0 stage-fill ${
                    isComplete && !isWarning ? 'stage-fill-complete' : isWarning ? 'stage-fill-warning' : 'stage-fill-animated'
                  } ${isRunning ? 'stage-shimmer' : ''}`}
                  style={{
                    clipPath: `inset(0 ${100 - stageProgress}% 0 0)`,
                    transition: 'clip-path 0.4s ease-out',
                  }}
                />
              </div>

              <div
                className="absolute inset-0 flex flex-col z-10 py-2 overflow-hidden"
                style={{
                  paddingLeft: index === 0 ? '16px' : '28px',
                  paddingRight: index === 3 ? '16px' : '28px'
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 stage-text">
                    <span className="text-xs text-zinc-300 font-jetbrains">{index + 1}</span>
                    <span className="text-sm font-semibold font-jetbrains text-white whitespace-nowrap">
                      {stageNames[key]}
                    </span>
                  </div>
                  {!isValidateStage && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onRun(key); }}
                      disabled={disabled}
                      className={`stage-button px-2 py-1 text-xs font-jetbrains font-medium rounded transition ${
                        disabled
                          ? 'opacity-50 cursor-not-allowed text-zinc-400'
                          : 'text-white cursor-pointer'
                      }`}
                    >
                      {isRunning ? '...' : 'Run'}
                    </button>
                  )}
                </div>

                {isValidateStage ? (
                  <ValidationStageContent
                    validation={validation}
                    showProgress={showProgress}
                    stageProgress={stageProgress}
                    strict={strict}
                  />
                ) : showProgress ? (
                  <ProgressContent progress={progress[key]} stageProgress={stageProgress} />
                ) : (
                  <StageMetrics stage={stage} stageKey={key} />
                )}

                {isError && stage.error && (
                  <div className="text-xs text-red-200 mt-1 whitespace-nowrap overflow-hidden text-ellipsis stage-text font-jetbrains">{stage.error}</div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ValidationStageContent({ validation, showProgress, stageProgress, strict }) {
  if (showProgress) {
    return (
      <div className="flex-1 flex flex-col justify-start font-jetbrains stage-text text-xs overflow-y-auto">
        <div className="text-white mb-1 whitespace-nowrap">{validation?.message || 'Validating...'}</div>
        <div className="h-1 bg-black/40 rounded-full overflow-hidden mb-1">
          <div className="h-full bg-white transition-all" style={{ width: `${stageProgress}%` }} />
        </div>
        <div className="text-zinc-400">{validation?.current}/{validation?.total}</div>
      </div>
    )
  }

  if (validation?.is_valid !== undefined) {
    return (
      <div className="flex-1 flex flex-col justify-start font-jetbrains stage-text text-xs overflow-y-auto">
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 whitespace-nowrap">
          <div className="text-zinc-400">Status</div>
          <div className={validation.is_valid ? 'text-emerald-400' : 'text-amber-400'}>
            {validation.recommendation || (validation.is_valid ? 'PASS' : 'REVIEW')}
          </div>
          {strict && (
            <>
              <div className="text-zinc-400">Strict</div>
              <div className={strict.failed === 0 ? 'text-emerald-400' : 'text-amber-400'}>
                {strict.passed}/{strict.passed + strict.failed} pass
              </div>
            </>
          )}
          {validation.patterns_found !== undefined && (
            <>
              <div className="text-zinc-400">Patterns</div>
              <div className="text-white">{validation.patterns_found}/{validation.patterns_total}</div>
            </>
          )}
          {validation.token_count > 0 && (
            <>
              <div className="text-zinc-400">Tokens</div>
              <div className="text-white">{formatTokens(validation.token_count)}</div>
            </>
          )}
        </div>
        {strict?.errors?.length > 0 && (
          <div className="mt-1 text-amber-400/70 space-y-0.5">
            {strict.errors.slice(0, 2).map((err, i) => (
              <div key={i} className="whitespace-nowrap overflow-hidden text-ellipsis">
                [{err.source}:{err.line}] {err.error}
              </div>
            ))}
            {strict.errors.length > 2 && (
              <div className="text-zinc-500">+{strict.errors.length - 2} more</div>
            )}
          </div>
        )}
      </div>
    )
  }

  return null
}

function ProgressContent({ progress, stageProgress }) {
  return (
    <div className="flex-1 flex flex-col justify-center font-jetbrains stage-text">
      <div className="text-xs text-white mb-1 whitespace-nowrap overflow-hidden text-ellipsis">
        {progress.message || 'Processing...'}
      </div>
      <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
        <div
          className="h-full bg-white transition-all duration-200"
          style={{ width: `${stageProgress}%` }}
        />
      </div>
      <div className="text-xs text-white mt-1">
        {progress.current} / {progress.total}
      </div>
    </div>
  )
}

function StageMetrics({ stage, stageKey }) {
  return (
    <div className="flex-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs content-center font-jetbrains stage-text whitespace-nowrap">
      <div className="text-zinc-300">Input</div>
      <div className="text-white">{stage.input_size > 0 ? formatBytes(stage.input_size) : '-'}</div>
      <div className="text-zinc-300">Output</div>
      <div className="text-white">{stage.output_size > 0 ? formatBytes(stage.output_size) : '-'}</div>
      <div className="text-zinc-300">Ratio</div>
      <div className={stage.compression_ratio < 0.5 && stage.compression_ratio > 0 ? 'text-green-300' : 'text-white'}>
        {stage.input_size > 0 ? `${(stage.compression_ratio * 100).toFixed(0)}%` : '-'}
      </div>
      <div className="text-zinc-300">Duration</div>
      <div className="text-white">{formatDuration(stage.duration)}</div>
      {stageKey === 'extract' && stage.extra?.signatures > 0 && (
        <>
          <div className="text-zinc-300">Signatures</div>
          <div className="text-white">{stage.extra.signatures}</div>
        </>
      )}
      {stageKey !== 'extract' && (
        <>
          <div className="text-zinc-300">Files</div>
          <div className="text-white">{stage.file_count || stage.files?.length || 0}</div>
        </>
      )}
    </div>
  )
}
