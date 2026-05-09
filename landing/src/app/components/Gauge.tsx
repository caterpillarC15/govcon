type GaugeProps = {
  value: number
  color?: string
  showLabels?: boolean
  min?: string
  max?: string
}

export default function Gauge({
  value,
  color = '#ef4d23',
  showLabels = false,
  min,
  max,
}: GaugeProps) {
  const totalTicks = 40
  const activeTicks = Math.round((value / 100) * totalTicks)

  const cx = 100
  const cy = 100
  const rOuter = 80
  const rInner = rOuter - 10

  const ticks = Array.from({ length: totalTicks }, (_, i) => {
    // 180° arc starting at angle π (left, 9 o'clock) sweeping to 2π (right, 3 o'clock)
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
        stroke={isActive ? color : '#d4d4d8'}
        strokeWidth={2.5}
        strokeLinecap="round"
      />
    )
  })

  return (
    <div className="w-full flex flex-col items-center">
      <svg
        viewBox="0 0 200 120"
        className="w-full"
        style={{ maxWidth: 260 }}
      >
        {ticks}
        <text
          x={100}
          y={105}
          textAnchor="middle"
          fontSize={22}
          fontWeight={600}
          fill="#0b0f1a"
        >
          {value}%
        </text>
      </svg>
      {showLabels && (
        <div
          className="w-full flex justify-between text-neutral-500"
          style={{ fontSize: 11, maxWidth: 260 }}
        >
          <span>{min}</span>
          <span>{max}</span>
        </div>
      )}
    </div>
  )
}
