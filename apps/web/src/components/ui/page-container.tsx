import type { ReactNode } from "react";

type PageContainerProps = {
  children: ReactNode;
  className?: string;
};

export function PageContainer({ children, className }: PageContainerProps) {
  const classes = ["aq-page-container", className].filter(Boolean).join(" ");
  return <div className={classes}>{children}</div>;
}
