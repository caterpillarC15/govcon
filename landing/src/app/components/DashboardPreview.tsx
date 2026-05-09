import { ChevronDown, TrendingDown, TrendingUp, X } from 'lucide-react'
import Gauge from './Gauge'

function TogglePill({
  options,
  activeIndex,
}: {
  options: [string, string]
  activeIndex: 0 | 1
}) {
  return (
    <div className="bg-neutral-100 rounded-full p-1 flex">
      {options.map((opt, i) => {
        const active = i === activeIndex
        return (
          <button
            key={opt}
            type="button"
            className={
              'flex-1 rounded-full px-3 py-1.5 transition-colors ' +
              (active
                ? 'bg-white shadow-sm text-neutral-900'
                : 'text-neutral-500 hover:text-neutral-700')
            }
            style={{ fontSize: 12 }}
          >
            {opt}
          </button>
        )
      })}
    </div>
  )
}

function ClicksCard() {
  return (
    <div className="bg-white rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between" style={{ fontSize: 13 }}>
        <span style={{ color: '#ef4d23' }}>Clicks</span>
        <span className="text-neutral-500">This Month</span>
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span
            className="text-neutral-900"
            style={{ fontSize: 28, fontWeight: 600, lineHeight: 1 }}
          >
            6,896
          </span>
          <span
            className="inline-flex items-center gap-1 bg-red-50 text-red-600 rounded-full px-2 py-0.5"
            style={{ fontSize: 11 }}
          >
            <TrendingDown size={12} strokeWidth={2} />
            -3,382 (33%)
          </span>
        </div>
        <span className="text-neutral-500" style={{ fontSize: 11 }}>
          Compared to yesterday
        </span>
      </div>

      <div className="flex flex-col items-center">
        <span className="text-neutral-700" style={{ fontSize: 12 }}>
          Month Target achieved
        </span>
        <Gauge value={92} color="#ef4d23" showLabels min="389K" max="425K" />
      </div>

      <TogglePill options={['Impressions', 'Clicks']} activeIndex={0} />
    </div>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label
      className="text-neutral-700"
      style={{ fontSize: 12 }}
    >
      {children}
    </label>
  )
}

function DropdownButton({ value }: { value: string }) {
  return (
    <button
      type="button"
      className="w-full flex items-center justify-between border border-neutral-200 rounded-lg px-3 py-2 text-neutral-900 bg-white hover:bg-neutral-50"
      style={{ fontSize: 13 }}
    >
      <span>{value}</span>
      <ChevronDown size={14} strokeWidth={2} className="text-neutral-500" />
    </button>
  )
}

function HashInput({ defaultValue }: { defaultValue: string }) {
  return (
    <div
      className="flex items-center border border-neutral-200 rounded-lg px-3 py-2 bg-white focus-within:ring-2 focus-within:ring-neutral-200"
      style={{ fontSize: 13 }}
    >
      <span className="text-neutral-400 mr-2">#</span>
      <input
        defaultValue={defaultValue}
        className="flex-1 outline-none bg-transparent text-neutral-900"
      />
    </div>
  )
}

function FormCard() {
  return (
    <div className="bg-white rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <FieldLabel>Show figures for</FieldLabel>
        <DropdownButton value="This month" />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel>Compare period by</FieldLabel>
        <DropdownButton value="Month-to-date (MTD)" />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel>Ste targets (This month)</FieldLabel>
        <HashInput defaultValue="10" />
      </div>

      <div className="flex flex-col gap-1.5">
        <FieldLabel>Ste targets (This year)</FieldLabel>
        <HashInput defaultValue="100" />
      </div>

      <div className="flex items-center gap-4 pt-1">
        <button
          type="button"
          className="text-white rounded-lg px-5 py-2"
          style={{ backgroundColor: '#ef4d23', fontSize: 13 }}
        >
          Save
        </button>
        <button
          type="button"
          className="underline text-neutral-700"
          style={{ fontSize: 13 }}
        >
          Cancel
        </button>
        <button
          type="button"
          aria-label="Close"
          className="ml-auto w-8 h-8 inline-flex items-center justify-center rounded-full text-neutral-500 hover:bg-neutral-100"
        >
          <X size={16} strokeWidth={2} />
        </button>
      </div>
    </div>
  )
}

function VideoStartsCard() {
  return (
    <div className="bg-white rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between" style={{ fontSize: 13 }}>
        <span style={{ color: '#ef4d23' }}>Video Starts</span>
        <span className="text-neutral-500">today</span>
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span
            className="text-neutral-900"
            style={{ fontSize: 28, fontWeight: 600, lineHeight: 1 }}
          >
            0
          </span>
          <span
            className="inline-flex items-center gap-1 bg-neutral-100 text-neutral-600 rounded-full px-2 py-0.5"
            style={{ fontSize: 11 }}
          >
            <TrendingUp size={12} strokeWidth={2} />0
          </span>
        </div>
        <span className="text-neutral-500" style={{ fontSize: 11 }}>
          Compared to yesterday
        </span>
      </div>

      <div className="flex flex-col items-center">
        <Gauge value={68} color="#9ca3af" />
      </div>

      <TogglePill options={['Video Clicks', 'Video Starts']} activeIndex={0} />
    </div>
  )
}

export default function DashboardPreview() {
  return (
    <div className="px-3 sm:px-4">
      <div
        className="rounded-3xl p-4 sm:p-6 w-full max-w-[880px] mx-auto"
        style={{ backgroundColor: '#f5f2ee' }}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <ClicksCard />
          <FormCard />
          <VideoStartsCard />
        </div>
      </div>
    </div>
  )
}
