import Image from "next/image";
import type { Character } from "@/types/chat";
import { cn } from "@/lib/utils";

type BotAvatarProps = {
  character: Character;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizeClassNames = {
  sm: "size-9 text-xs",
  md: "size-11 text-sm",
  lg: "size-20 text-2xl",
};

const imageSizes = {
  sm: 36,
  md: 44,
  lg: 80,
};

export function BotAvatar({ character, className, size = "md" }: BotAvatarProps) {
  const classes = cn(
    "flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-zeta-line bg-zeta-panel font-semibold text-zeta-text",
    sizeClassNames[size],
    className,
  );

  if (character.avatarImageUrl) {
    return (
      <Image
        alt={`${character.name} profile`}
        className={cn(classes, "object-cover")}
        height={imageSizes[size]}
        src={character.avatarImageUrl}
        unoptimized
        width={imageSizes[size]}
      />
    );
  }

  return <div className={classes}>{character.avatar || character.name.slice(0, 1)}</div>;
}
