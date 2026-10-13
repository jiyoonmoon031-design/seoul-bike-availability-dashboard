type Props = {
  source?: string
}

export function SourceBadge({ source }: Props) {
  if (source !== 'baseline_fallback') {
    return null
  }

  return (
    <div className="fallback-badge">
      Baseline fallback 사용 중
    </div>
  )
}
