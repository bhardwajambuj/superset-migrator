import { useState } from 'react'
import UploadStep from './components/UploadStep.jsx'
import MappingStep from './components/MappingStep.jsx'
import SummaryStep from './components/SummaryStep.jsx'

const STEPS = [
  { label: 'Upload', num: 1 },
  { label: 'Configure', num: 2 },
  { label: 'Download', num: 3 },
]

export default function App() {
  const [step, setStep] = useState(1)            // 1 | 2 | 3
  const [file, setFile] = useState(null)
  const [parseResult, setParseResult] = useState(null)
  const [summary, setSummary] = useState(null)

  function handleParsed(f, result) {
    setFile(f)
    setParseResult(result)
    setStep(2)
  }

  function handleTransformed(s) {
    setSummary(s)
    setStep(3)
  }

  function reset() {
    setStep(1)
    setFile(null)
    setParseResult(null)
    setSummary(null)
  }

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <div className="logo">⚡</div>
        <h1>Superset Dashboard Migrator</h1>
      </header>

      <main className="app-main">
        {/* Step indicator */}
        <nav className="steps">
          {STEPS.map((s, i) => {
            const status = step > s.num ? 'done' : step === s.num ? 'active' : ''
            return (
              <div key={s.num} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : 0 }}>
                <div className={`step-item ${status}`}>
                  <div className="step-dot">
                    {step > s.num ? '✓' : s.num}
                  </div>
                  {s.label}
                </div>
                {i < STEPS.length - 1 && <div className="step-connector" />}
              </div>
            )
          })}
        </nav>

        {/* Step content */}
        {step === 1 && <UploadStep onParsed={handleParsed} />}

        {step === 2 && (
          <MappingStep
            file={file}
            parseResult={parseResult}
            onTransformed={handleTransformed}
            onBack={() => setStep(1)}
          />
        )}

        {step === 3 && (
          <SummaryStep summary={summary} onReset={reset} />
        )}
      </main>
    </div>
  )
}
