import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import {
  LegalDocument,
  LegalList,
  LegalParagraph,
  LegalSection,
} from "@/components/legal/legal-document";

export const metadata: Metadata = {
  title: "Privacy policy",
  description: "How Aqil handles account and portfolio information in this prototype.",
};

export default function PrivacyPage() {
  return (
    <AppShell title="Privacy policy">
      <LegalDocument title="Privacy policy" lastUpdated="18 October 2026">
        <LegalSection title="Scope">
          <LegalParagraph>
            This notice describes how the Aqil web application (a private investment-research
            prototype) handles information when you use the site. It reflects what is implemented in
            the codebase today, not a commercial privacy programme.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Authentication">
          <LegalParagraph>
            Sign-in is handled by Supabase Auth. The application is designed to use Google as the
            only supported sign-in provider. A dedicated sign-in flow may not yet be visible on
            every environment; until it is, access to some private features may rely on separate
            development-only controls rather than your Google account.
          </LegalParagraph>
          <LegalParagraph>
            When you sign in with Google, Supabase receives the profile information Google shares
            for that OAuth consent (typically including your email address and display name). Supabase
            assigns your account a user identifier used to link your data in the database.
          </LegalParagraph>
          <LegalParagraph>
            The application uses the Supabase SSR package to store session state in HTTP cookies on
            your device. We do not use browser local storage for portfolio or ledger data in the
            current implementation.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Information we store about you">
          <LegalList
            items={[
              "Account identity in Supabase Auth (linked to your Google sign-in when used).",
              "Optional user settings (for example locale and timezone) in the user_settings table, restricted to your user id.",
              "If you enter or import portfolio information while signed in: wealth profile metadata, positions (including identifiers such as ISIN or symbol where you provide them), strategic allocation targets, contribution plans and contribution events. These rows are stored in Supabase PostgreSQL and are scoped to your user id.",
            ]}
          />
          <LegalParagraph>
            Unpublished research datasets and worker pipelines are stored separately and are not
            exposed to the standard authenticated database role in our schema tests. The public site
            may show demonstration or empty states rather than your private portfolio when you are
            not authorised for a given feature.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="How we use this information">
          <LegalParagraph>
            We use account and portfolio data to operate the product for you: displaying your
            holdings and plan, running deterministic analytics you request in the interface, and
            enforcing per-user access in the application and database. We do not use positive
            research outputs to change your strategic allocation targets automatically.
          </LegalParagraph>
          <LegalParagraph>
            Engineering policy is to avoid writing access tokens, refresh tokens, cookies, OAuth
            codes or portfolio amounts to application logs. We have not published a separate
            logging or monitoring configuration for production.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Storage and hosting">
          <LegalParagraph>
            Data is stored in a Supabase-hosted PostgreSQL database configured for your deployment.
            The physical region and sub-processors depend on your Supabase project settings; this
            repository does not fix a production region.
          </LegalParagraph>
          <LegalParagraph>
            Pages that can show private wealth information are served with cache-control headers
            intended to prevent public caching (private, no-store on the My wealth route in the
            application configuration).
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Security">
          <LegalParagraph>
            Traffic between your browser and the application is expected to use HTTPS in deployed
            environments. Database access from the application uses Supabase credentials and row-level
            security policies on private tables so authenticated users can read and write only their
            own rows (verified in automated database tests for user settings and wealth tables).
          </LegalParagraph>
          <LegalParagraph>
            We have not published an independent security audit, backup restore drill or encryption
            attestation for this prototype. Platform security features are described by Supabase in
            their own documentation.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Sharing">
          <LegalParagraph>
            Google processes your sign-in when you use Google OAuth. Supabase processes authentication
            and database hosting. We have not published a full sub-processor list or data-processing
            agreement for this prototype.
          </LegalParagraph>
          <LegalParagraph>
            We do not describe any sale of portfolio data in the product design. Any future sharing
            would require an updated notice and, where required by law, your consent.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Details still being finalised">
          <LegalList
            items={[
              "Formal data retention periods and automated deletion workflows.",
              "Self-service export and account deletion.",
              "A published privacy contact and data protection officer arrangement.",
              "Cross-border transfer assessments (for example under Singapore PDPA) before commercial launch.",
            ]}
          />
          <LegalParagraph>
            Internal governance documents note that these items should be resolved before a
            multi-user or subscription offering; they are not implemented solely by this page.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Contact">
          <LegalParagraph>
            A dedicated privacy contact address is not yet published for this prototype. If you
            need to reach the operator, use the contact channel you were given for early access, or
            the address that will be listed here before any public launch.
          </LegalParagraph>
        </LegalSection>
      </LegalDocument>
    </AppShell>
  );
}
