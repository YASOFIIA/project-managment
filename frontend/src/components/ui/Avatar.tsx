import { getAvatarColor } from '../../utils/getAvatarColor';

interface Props {
  name: string;
  size?: number;
  ring?: boolean;
}

// Colored circle with initials
export function Avatar({ name, size = 32, ring }: Props) {
  return (
    <span
      title={name}
      aria-label={name}
      className={`inline-flex shrink-0 select-none items-center justify-center rounded-full font-semibold text-white ${
        ring ? 'ring-2 ring-white' : ''
      }`}
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * 0.4),
        backgroundColor: getAvatarColor(name),
      }}
    >
      {name.slice(0, 2).toUpperCase()}
    </span>
  );
}

export function AvatarStack({ names, max = 4, size = 26 }: { names: string[]; max?: number; size?: number }) {
  const shown = names.slice(0, max);
  const rest = names.length - shown.length;
  return (
    <div className="flex items-center -space-x-2">
      {shown.map((n) => (
        <Avatar key={n} name={n} size={size} ring />
      ))}
      {rest > 0 && (
        <span
          className="inline-flex items-center justify-center rounded-full bg-black/10 text-[11px] font-medium text-ink-soft ring-2 ring-white"
          style={{ width: size, height: size }}
        >
          +{rest}
        </span>
      )}
    </div>
  );
}
