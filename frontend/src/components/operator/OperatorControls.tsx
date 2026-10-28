type Props = {
  baseTime: string
  horizon: number
  topN: number
  onBaseTimeChange: (value: string) => void
  onHorizonChange: (value: number) => void
  onTopNChange: (value: number) => void
  onSubmit: () => void
}

export function OperatorControls({
  baseTime,
  horizon,
  topN,
  onBaseTimeChange,
  onHorizonChange,
  onTopNChange,
  onSubmit,
}: Props) {
  return (
    <section className="control-bar">
      <label className="control-field control-field-wide">
        <span>기준 시각</span>

        <input
          className="control-input"
          type="datetime-local"
          value={baseTime}
          onChange={(event) =>
            onBaseTimeChange(
              event.target.value,
            )
          }
        />
      </label>

      <label className="control-field">
        <span>예측 범위</span>

        <select
          value={horizon}
          onChange={(event) =>
            onHorizonChange(
              Number(event.target.value),
            )
          }
        >
          <option value={15}>15분</option>
          <option value={30}>30분</option>
          <option value={60}>60분</option>
        </select>
      </label>

      <label className="control-field">
        <span>Top N</span>

        <select
          value={topN}
          onChange={(event) =>
            onTopNChange(
              Number(event.target.value),
            )
          }
        >
          <option value={5}>5</option>
          <option value={10}>10</option>
          <option value={20}>20</option>
        </select>
      </label>

      <button
        className="primary-button"
        type="button"
        onClick={onSubmit}
      >
        조회
      </button>
    </section>
  )
}
