import { ReadingContainer } from "@/components/ui/reading-container";

type LegalDocumentProps = {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
};

export function LegalDocument({ title, lastUpdated, children }: LegalDocumentProps) {
  return (
    <ReadingContainer>
      <article className="legal-document" aria-labelledby="legal-title">
        <header className="legal-document-header">
          <h1 id="legal-title" className="legal-document-title">
            {title}
          </h1>
          <p className="legal-document-meta">Last updated: {lastUpdated}</p>
        </header>
        <div className="legal-document-body">{children}</div>
      </article>
    </ReadingContainer>
  );
}

type LegalSectionProps = {
  title: string;
  children: React.ReactNode;
};

export function LegalSection({ title, children }: LegalSectionProps) {
  const id = title.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  return (
    <section className="legal-section" aria-labelledby={id}>
      <h2 id={id} className="legal-section-title">
        {title}
      </h2>
      {children}
    </section>
  );
}

export function LegalParagraph({ children }: { children: React.ReactNode }) {
  return <p className="legal-paragraph">{children}</p>;
}

export function LegalList({ items }: { items: string[] }) {
  return (
    <ul className="legal-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}
