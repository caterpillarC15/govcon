type Decision = 'strong_pursue' | 'pursue' | 'maybe' | 'reject'

type Props = {
  score: number
  decision: Decision
  size?: number
}

const decisionColor: Record<Decision, string> = {
  strong_pursue: 'var(--color-decision-strong)',
  pursue: 'var(--color-decision-pursue)',
  maybe: 'var(--color-decision-maybe)',
  reject: 'var(--color-decision-reject)',
}

/**
 * 100-point fit-score gauge — half-arc tick meter, with the
 * §5.7 decision band encoded by tick color. Replaces the old
 * generic Gauge that displayed "%" suffixes.
 */
export default function FitScoreGauge({ score, decision, size = 200 }: Props) {
  const totalTicks = 40
  const activeTicks = Math.round((score / 100) * totalTicks)
  const cx = 100
  const cy = 100
  const rOuter = 82
  const rInner = rOuter - 10
  const color = decisionColor[decision]

  const ticks = Array.from({ length: totalTicks }, (_, i) => {
    const t = i / (totalTicks - 1)
    const angle = Math.PI + t * Math.PI
    const x1 = cx + rInner * Math.cos(angle)
    const y1 = cy + rInner * Math.sin(angle)
    const x2 = cx + rOuter * Math.cos(angle)
    const y2 = cy + rOuter * Math.sin(angle)
    const isActive = i < activeTicks
    return (
      <line
        key={i}
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={isActive ? color : '#e2e8f0'}
        strokeWidth={2.5}
        strokeLinecap="round"
      />
    )
  })

  return (
    <svg
      viewBox="0 0 200 120"
      role="img"
      aria-label={`Fit score ${score} out of 100`}
      style={{ width: size, maxWidth: '100%' }}
    >
      {ticks}
      <text
        x={100}
        y={96}
        textAnchor="middle"
        fontFamily="var(--font-sans)"
        fontSize={26}
        fontWeight={600}
        fill="var(--color-ink)"
      >
        {score}
      </text>
      <text
        x={100}
        y={114}
        textAnchor="middle"
        fontFamily="var(--font-sans)"
        fontSize={11}
        fill="var(--color-ink-subtle)"
      >
        of 100
      </text>
    </svg>
  )
}
