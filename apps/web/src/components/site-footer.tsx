import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer" aria-label="Site footer">
      <div className="site-footer-inner">
        <p className="site-footer-note">
          Aqil is a private investment-research prototype. It is not a regulated financial adviser.
        </p>
        <nav className="site-footer-links" aria-label="Legal">
          <Link className="site-footer-link" href="/privacy">
            Privacy policy
          </Link>
          <Link className="site-footer-link" href="/tos">
            Terms of service
          </Link>
        </nav>
      </div>
    </footer>
  );
}
