interface ProgressBarProps {
  value: number;
}

export function ProgressBar({ value }: ProgressBarProps) {
  return (
    <div className="progress" aria-label={`Progress ${value}%`}>
      <div className="progress__fill" style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} />
    </div>
  );
}

