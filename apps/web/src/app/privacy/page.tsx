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
            Sign-in is handled by Supabase Auth. Google is the only provider enabled in this
            application. A successful Google sign-in creates a Supabase user id. That id is the
            application identity. A successful Google sign-in opens the application. Aqil does not
            merge accounts by comparing email addresses. Supabase Auth may still link identities
            when that project&apos;s own provider settings do so. There is no separate founder cookie.
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
              "Portfolio rows, when stored, belong to one Supabase user id. Another Google account cannot read them.",
              "Portfolio holdings are not stored by the authentication change. A separate portfolio migration, when applied, is designed so each row belongs to one user id.",
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
            Account data is used to decide whether this browser may open private screens. This
            branch does not store portfolio holdings, and it does not run portfolio analytics. When
            a later portfolio migration is applied, those rows are meant to stay tied to the
            Supabase user id. Research outputs do not change allocation targets in this application.
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
            API routes and the private screens (home, explore, calendar, learn, research and my
            wealth) are configured with Cache-Control: private, no-store, max-age=0. A production
            check on 18 October 2026 saw that header on the research and my wealth redirects. The
            login, privacy and terms pages are prerendered and were served with Cache-Control:
            s-maxage=31536000. They do not contain portfolio rows. This is not a retention period.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Security">
          <LegalParagraph>
            Traffic between your browser and the application is expected to use HTTPS in deployed
            environments. The repository defines row-level security for user settings and access
            grants. Those policies are enforced by the database, not by a header from the proxy.
            Wealth-table policies are not part of this branch. A policy file is not the same as a
            completed test run; the handover records which database tests actually passed.
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
