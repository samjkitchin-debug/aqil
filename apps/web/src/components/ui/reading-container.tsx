import type { ReactNode } from "react";

type ReadingContainerProps = {
  children: ReactNode;
  className?: string;
};

export function ReadingContainer({ children, className }: ReadingContainerProps) {
  const classes = ["aq-reading-container", className].filter(Boolean).join(" ");
  return <div className={classes}>{children}</div>;
}
