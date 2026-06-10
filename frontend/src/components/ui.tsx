import type { CSSProperties, ReactNode } from 'react'

// ── Card ────────────────────────────────────────────────────────────────────

export function Card({
  children,
  title,
  style,
}: {
  children: ReactNode
  title?: ReactNode
  style?: CSSProperties
}) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        borderRadius: 'var(--radius-lg)',
        border: '0.5px solid var(--border)',
        padding: 16,
        marginBottom: 12,
        ...style,
      }}
    >
      {title && (
        <div
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: 'var(--text)',
            marginBottom: 12,
          }}
        >
          {title}
        </div>
      )}
      {children}
    </div>
  )
}

// ── Metric card ─────────────────────────────────────────────────────────────

export function Metric({
  label,
  value,
  sub,
  valueColor,
  style,
}: {
  label: string
  value: ReactNode
  sub?: ReactNode
  valueColor?: string
  style?: CSSProperties
}) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 110,
        background: 'var(--surface)',
        borderRadius: 'var(--radius-md)',
        padding: '14px 16px',
        border: '0.5px solid var(--border)',
        ...style,
      }}
    >
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>
        {label}
      </div>
      <div
        style={{
          fontSize: 22,
          fontWeight: 500,
          color: valueColor ?? 'var(--text)',
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
          {sub}
        </div>
      )}
    </div>
  )
}

// ── Filter chip ─────────────────────────────────────────────────────────────

export function FilterChip({
  active,
  onClick,
  children,
}: {
  active?: boolean
  onClick?: () => void
  children: ReactNode
}) {
  return (
    <span
      onClick={onClick}
      style={{
        fontSize: 12,
        padding: '4px 10px',
        borderRadius: 'var(--radius-md)',
        border: active
          ? '0.5px solid var(--purple-border)'
          : '0.5px solid var(--border)',
        background: active ? 'var(--purple-light)' : 'var(--surface)',
        color: active ? 'var(--purple-dark)' : 'var(--text-secondary)',
        cursor: 'pointer',
        userSelect: 'none',
      }}
    >
      {children}
    </span>
  )
}

// ── Button ──────────────────────────────────────────────────────────────────

export function Button({
  variant = 'default',
  onClick,
  children,
  type = 'button',
  disabled,
  style,
}: {
  variant?: 'default' | 'primary'
  onClick?: () => void
  children: ReactNode
  type?: 'button' | 'submit'
  disabled?: boolean
  style?: CSSProperties
}) {
  const primary: CSSProperties = {
    background: 'var(--purple)',
    border: '0.5px solid var(--purple)',
    color: '#fff',
  }
  const def: CSSProperties = {
    background: 'var(--surface)',
    border: '0.5px solid var(--border-md)',
    color: 'var(--text)',
  }
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      style={{
        padding: '7px 14px',
        borderRadius: 'var(--radius-md)',
        fontSize: 13,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        whiteSpace: 'nowrap',
        ...(variant === 'primary' ? primary : def),
        ...style,
      }}
    >
      {children}
    </button>
  )
}

// ── Section header ──────────────────────────────────────────────────────────

export function SectionHeader({
  title,
  right,
}: {
  title: ReactNode
  right?: ReactNode
}) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
      }}
    >
      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>
        {title}
      </span>
      {right}
    </div>
  )
}

// ── Mini tag ────────────────────────────────────────────────────────────────

export function MiniTag({ children }: { children: ReactNode }) {
  return (
    <span
      style={{
        fontSize: 11,
        padding: '2px 8px',
        borderRadius: 4,
        background: 'var(--bg-secondary)',
        color: 'var(--text-secondary)',
      }}
    >
      {children}
    </span>
  )
}

// ── Two columns ─────────────────────────────────────────────────────────────

export function TwoCol({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.2fr) minmax(0, 1fr)',
        gap: 12,
      }}
      className="two-col-grid"
    >
      {children}
    </div>
  )
}

// ── Simple bar chart ────────────────────────────────────────────────────────

export function BarRow({
  label,
  value,
  pct,
  color = 'var(--purple)',
  labelMinWidth = 70,
}: {
  label: string
  value: ReactNode
  pct: number
  color?: string
  labelMinWidth?: number
}) {
  const safe = Math.max(0, Math.min(100, pct))
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span
        style={{
          fontSize: 12,
          color: 'var(--text-secondary)',
          minWidth: labelMinWidth,
          textAlign: 'right',
        }}
      >
        {label}
      </span>
      <div
        style={{
          flex: 1,
          height: 20,
          background: 'var(--bg-secondary)',
          borderRadius: 4,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            background: color,
            width: `${safe}%`,
            borderRadius: 4,
            display: 'flex',
            alignItems: 'center',
            paddingLeft: 8,
          }}
        >
          <span style={{ fontSize: 11, fontWeight: 500, color: '#fff' }}>{value}</span>
        </div>
      </div>
    </div>
  )
}

// ── Status chip ─────────────────────────────────────────────────────────────

export function StatusChip({
  variant,
  children,
}: {
  variant: 'ok' | 'warn' | 'error' | 'neutral'
  children: ReactNode
}) {
  const styles: Record<string, CSSProperties> = {
    ok: { background: 'var(--green-light)', color: 'var(--green-text)' },
    warn: { background: 'var(--amber-light)', color: 'var(--amber-text)' },
    error: { background: 'var(--coral-light)', color: 'var(--coral-text)' },
    neutral: { background: 'var(--bg-secondary)', color: 'var(--text-secondary)' },
  }
  return (
    <span
      style={{
        fontSize: 11,
        padding: '2px 7px',
        borderRadius: 4,
        fontWeight: 500,
        ...styles[variant],
      }}
    >
      {children}
    </span>
  )
}
