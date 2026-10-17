import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import {
  LegalDocument,
  LegalList,
  LegalParagraph,
  LegalSection,
} from "@/components/legal/legal-document";

export const metadata: Metadata = {
  title: "Terms of service",
  description: "Terms for using the Aqil private investment-research prototype.",
};

export default function TermsPage() {
  return (
    <AppShell title="Terms of service">
      <LegalDocument title="Terms of service" lastUpdated="18 October 2026">
        <LegalSection title="Agreement">
          <LegalParagraph>
            By using the Aqil website and application, you agree to these terms. If you do not agree,
            do not use the service. Aqil is currently operated as a private prototype for
            investment research and personal portfolio tooling, not as a commercial financial
            service open to the general public unless explicitly invited.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Not financial advice">
          <LegalParagraph>
            Aqil is not a regulated financial adviser, broker, portfolio manager or insurance
            intermediary. Nothing on the site is personal financial advice, a recommendation to buy
            or sell any instrument, or an offer to provide regulated services in Singapore or any
            other jurisdiction.
          </LegalParagraph>
          <LegalParagraph>
            Research views, scenarios, macro indicators and portfolio analytics are informational
            and educational tools. You remain solely responsible for your own decisions, tax
            position and compliance with applicable law. Obtain qualified professional advice before
            acting on financial matters.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Prototype limitations">
          <LegalList
            items={[
              "Features, data sources and access controls may change without notice during development.",
              "Demonstration or synthetic data may be shown when live data or your account is unavailable.",
              "The service does not execute trades, hold client money or connect to a brokerage for order placement in the current implementation.",
              "Availability is not guaranteed; maintenance, source outages or auth issues may interrupt access.",
            ]}
          />
        </LegalSection>

        <LegalSection title="Your responsibilities">
          <LegalParagraph>
            You must provide accurate information you choose to enter (for example portfolio
            positions and contributions). You must keep your sign-in credentials secure and not
            misuse the service, attempt to access another user&apos;s data, or probe systems without
            permission.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Intellectual property and research integrity">
          <LegalParagraph>
            Site content, research methods and software are owned by the operator or licensors.
            Published research is intended to distinguish facts, model outputs and interpretation; it
            does not guarantee future results. Do not rely on the platform as a sole source for
            investment decisions.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Disclaimer of warranties">
          <LegalParagraph>
            The service is provided &quot;as is&quot; and &quot;as available&quot; to the extent
            permitted by law. We do not warrant uninterrupted operation, accuracy of third-party
            data, or fitness for a particular purpose.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Limitation of liability">
          <LegalParagraph>
            To the fullest extent permitted by law, the operator is not liable for indirect,
            incidental or consequential losses, or for trading or investment losses arising from use
            of the service. Nothing in these terms excludes liability that cannot be excluded under
            applicable law.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Details still being finalised">
          <LegalList
            items={[
              "Governing law and dispute resolution jurisdiction.",
              "Formal consumer terms, cooling-off rights and payment terms if subscriptions launch.",
              "Published operator legal entity name and registered address.",
            ]}
          />
        </LegalSection>

        <LegalSection title="Changes">
          <LegalParagraph>
            We may update these terms as the product matures. The &quot;Last updated&quot; date at the
            top of this page will change when material updates are published. Continued use after
            changes constitutes acceptance of the revised terms.
          </LegalParagraph>
        </LegalSection>

        <LegalSection title="Contact">
          <LegalParagraph>
            A general support or legal contact address is not yet published for this prototype. Use
            the early-access channel provided to you, or the contact details that will be listed here
            before a public launch.
          </LegalParagraph>
        </LegalSection>
      </LegalDocument>
    </AppShell>
  );
}
