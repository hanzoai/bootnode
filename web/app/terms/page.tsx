import Link from "next/link"
import type { Metadata } from "next"
import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import { Badge } from "@/components/ui/badge"
import { FileText } from "lucide-react"
import { getBrand } from "@/lib/brand"

const brand = getBrand()

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    `${brand.name} Terms of Service. The terms and conditions governing your use of the ${brand.name} platform.`,
}

export default function TermsPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      {/* Hero */}
      <section className="border-b bg-gradient-to-b from-background to-muted/20">
        <div className="container py-16 md:py-20">
          <div className="mx-auto max-w-3xl">
            <Badge variant="secondary" className="mb-4">
              <FileText className="mr-1 h-3 w-3" />
              Legal
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Terms of Service
            </h1>
            <p className="mt-4 text-muted-foreground">
              Effective date: January 1, 2026
            </p>
          </div>
        </div>
      </section>

      {/* Content */}
      <section className="py-16">
        <div className="container">
          <div className="mx-auto max-w-3xl">
            <div className="space-y-8 text-sm text-muted-foreground leading-relaxed">
              <div>
                <h2 className="text-xl font-semibold text-foreground">1. Agreement to Terms</h2>
                <p className="mt-3">
                  These Terms of Service (&quot;Terms&quot;) constitute a legally binding agreement
                  between you (&quot;you&quot; or &quot;Customer&quot;) and Hanzo AI, Inc. (&quot;{brand.name},&quot;
                  &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;), governing your access to and use of the
                  {brand.domain} website, APIs, documentation, and related services
                  (collectively, the &quot;Service&quot;).
                </p>
                <p className="mt-3">
                  By creating an account, accessing, or using the Service, you agree to be
                  bound by these Terms. If you are using the Service on behalf of an
                  organization, you represent that you have the authority to bind that
                  organization to these Terms.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">2. Description of Service</h2>
                <p className="mt-3">
                  {brand.name} provides blockchain infrastructure services including, but not
                  limited to:
                </p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>Multi-chain JSON-RPC and REST API endpoints</li>
                  <li>Token, NFT, and transfer data APIs</li>
                  <li>Real-time webhook notifications for onchain events</li>
                  <li>Smart wallet creation and management (ERC-4337)</li>
                  <li>Gas sponsorship and paymaster services</li>
                  <li>Dashboard for API key management, usage monitoring, and configuration</li>
                </ul>
                <p className="mt-3">
                  The specific features available to you depend on your subscription plan.
                  We may add, modify, or discontinue features with reasonable notice.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">3. Account Registration</h2>
                <p className="mt-3">
                  To use the Service, you must create an account and provide accurate,
                  complete information. You are responsible for:
                </p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>Maintaining the security of your account credentials and API keys</li>
                  <li>All activities that occur under your account</li>
                  <li>Notifying us immediately of any unauthorized access</li>
                  <li>Ensuring that your contact information remains current</li>
                </ul>
                <p className="mt-3">
                  You may not share your account credentials or API keys with unauthorized
                  parties. You may not create multiple free accounts to circumvent usage
                  limits.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">4. Acceptable Use</h2>
                <p className="mt-3">You agree not to use the Service to:</p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>Violate any applicable law, regulation, or third-party rights</li>
                  <li>Transmit malicious code, viruses, or any destructive content</li>
                  <li>Attempt to gain unauthorized access to any systems or networks</li>
                  <li>Interfere with or disrupt the Service or its infrastructure</li>
                  <li>Circumvent rate limits, usage quotas, or security measures</li>
                  <li>Resell or redistribute the Service without our written consent</li>
                  <li>Use the Service to facilitate money laundering, fraud, or sanctions evasion</li>
                  <li>Scrape, mine, or extract data from the Service beyond your authorized usage</li>
                </ul>
                <p className="mt-3">
                  We reserve the right to suspend or terminate your access if we reasonably
                  believe you have violated these terms, with notice where practicable.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">5. Pricing and Billing</h2>

                <h3 className="mt-4 text-base font-semibold text-foreground">5.1 Subscription Plans</h3>
                <p className="mt-2">
                  The Service is offered under subscription plans as described on our{" "}
                  <Link href="/pricing" className="text-primary hover:underline">
                    Pricing page
                  </Link>
                  . Plan details, including compute unit allocations, feature access, and
                  pricing, are incorporated into these Terms by reference.
                </p>

                <h3 className="mt-4 text-base font-semibold text-foreground">5.2 Payment</h3>
                <p className="mt-2">
                  Paid plans are billed in advance on a monthly or annual basis. Payment is
                  processed through Square via Hanzo Commerce. By providing payment information, you authorize
                  us to charge the applicable fees to your payment method. All fees are
                  stated in US Dollars and are non-refundable except as expressly stated
                  herein or required by law.
                </p>

                <h3 className="mt-4 text-base font-semibold text-foreground">5.3 Overage</h3>
                <p className="mt-2">
                  If you exceed your plan&apos;s compute unit allocation, additional usage may
                  be charged at the overage rate specified in your plan, or your access may
                  be rate-limited until the next billing cycle, depending on your plan
                  configuration.
                </p>

                <h3 className="mt-4 text-base font-semibold text-foreground">5.4 Price Changes</h3>
                <p className="mt-2">
                  We may change our prices with at least 30 days&apos; notice. Price changes
                  take effect at the start of the next billing cycle. Your continued use of
                  the Service after a price change constitutes acceptance of the new pricing.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">6. Service Level Agreement</h2>
                <p className="mt-3">
                  For paid plans, {brand.name} targets the following service levels:
                </p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>
                    <strong className="text-foreground">Growth Plan:</strong> 99.9% monthly uptime for API endpoints
                  </li>
                  <li>
                    <strong className="text-foreground">Enterprise Plan:</strong> 99.999% monthly uptime with custom
                    SLA terms as specified in your enterprise agreement
                  </li>
                </ul>
                <p className="mt-3">
                  Uptime is measured as the percentage of minutes in a calendar month during
                  which the API endpoints are available and responsive. Scheduled maintenance
                  windows (announced at least 48 hours in advance) and force majeure events
                  are excluded from uptime calculations.
                </p>
                <p className="mt-3">
                  If we fail to meet the applicable SLA in any calendar month, you may
                  request a service credit. Credits are calculated as a percentage of your
                  monthly fee proportional to the downtime experienced, up to a maximum of
                  30% of your monthly fee. Service credits are the sole and exclusive remedy
                  for SLA failures.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">7. Intellectual Property</h2>
                <p className="mt-3">
                  The Service, including its software, documentation, APIs, trademarks, and
                  content, is owned by {brand.name} and protected by intellectual property laws.
                  We grant you a limited, non-exclusive, non-transferable, revocable license
                  to use the Service in accordance with these Terms.
                </p>
                <p className="mt-3">
                  You retain ownership of any application code, content, or data you create
                  using the Service. You grant us a limited license to process your data as
                  necessary to provide the Service.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">8. Data and Privacy</h2>
                <p className="mt-3">
                  Our collection and use of personal information is governed by our{" "}
                  <Link href="/privacy" className="text-primary hover:underline">
                    Privacy Policy
                  </Link>
                  , which is incorporated into these Terms by reference. You are responsible
                  for ensuring that your use of the Service complies with applicable data
                  protection laws, including GDPR where applicable.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">9. Confidentiality</h2>
                <p className="mt-3">
                  Each party agrees to protect the confidential information of the other
                  party with the same degree of care it uses for its own confidential
                  information. Confidential information includes API keys, account
                  credentials, pricing terms, and any non-public technical or business
                  information shared between the parties.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">10. Limitation of Liability</h2>
                <p className="mt-3">
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW, BOOTNODE SHALL NOT BE LIABLE FOR
                  ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES,
                  INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, OR BUSINESS
                  OPPORTUNITIES, ARISING FROM OR RELATED TO YOUR USE OF THE SERVICE.
                </p>
                <p className="mt-3">
                  OUR TOTAL AGGREGATE LIABILITY FOR ALL CLAIMS ARISING FROM OR RELATED TO
                  THE SERVICE SHALL NOT EXCEED THE AMOUNT YOU PAID TO BOOTNODE IN THE TWELVE
                  (12) MONTHS PRECEDING THE CLAIM.
                </p>
                <p className="mt-3">
                  This limitation applies regardless of the theory of liability (contract,
                  tort, strict liability, or otherwise) and even if we have been advised of
                  the possibility of such damages.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">11. Disclaimer of Warranties</h2>
                <p className="mt-3">
                  THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; WITHOUT WARRANTIES OF
                  ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED
                  WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
                  NON-INFRINGEMENT. WE DO NOT WARRANT THAT THE SERVICE WILL BE
                  UNINTERRUPTED, ERROR-FREE, OR COMPLETELY SECURE.
                </p>
                <p className="mt-3">
                  {brand.name} does not guarantee the accuracy, completeness, or timeliness of
                  blockchain data provided through the Service. You are responsible for
                  independently verifying any data critical to your application.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">12. Indemnification</h2>
                <p className="mt-3">
                  You agree to indemnify, defend, and hold harmless {brand.name} and its
                  officers, directors, employees, and agents from any claims, damages,
                  losses, liabilities, and expenses (including reasonable attorney fees)
                  arising from: (a) your use of the Service; (b) your violation of these
                  Terms; (c) your violation of any third-party rights; or (d) your
                  application or content.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">13. Termination</h2>
                <p className="mt-3">
                  You may terminate your account at any time through the dashboard or by
                  contacting support. Upon termination, your access to the Service will be
                  revoked and your API keys will be deactivated.
                </p>
                <p className="mt-3">
                  We may suspend or terminate your access to the Service at any time for
                  cause, including violation of these Terms, non-payment, or upon receiving
                  a valid legal order. We will provide reasonable notice where practicable.
                </p>
                <p className="mt-3">
                  Upon termination: (a) all rights granted to you under these Terms will
                  cease; (b) you remain liable for any fees incurred prior to termination;
                  (c) sections regarding intellectual property, limitation of liability,
                  indemnification, and governing law survive termination.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">14. Modifications to Terms</h2>
                <p className="mt-3">
                  We may modify these Terms at any time. We will notify you of material
                  changes at least 30 days in advance via email or a notice on the Service.
                  Your continued use of the Service after the effective date of any
                  modification constitutes acceptance of the modified Terms. If you do not
                  agree to the modified Terms, you must stop using the Service and terminate
                  your account.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">15. Governing Law</h2>
                <p className="mt-3">
                  These Terms are governed by and construed in accordance with the laws of
                  the State of California, United States, without regard to its conflict of
                  law principles. Any disputes arising from these Terms or the Service shall
                  be resolved exclusively in the state or federal courts located in San
                  Francisco County, California.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">16. General Provisions</h2>
                <ul className="mt-3 ml-4 list-disc space-y-2">
                  <li>
                    <strong className="text-foreground">Entire Agreement:</strong> These Terms, together with the
                    Privacy Policy and any applicable enterprise agreement, constitute the
                    entire agreement between you and {brand.name} regarding the Service.
                  </li>
                  <li>
                    <strong className="text-foreground">Severability:</strong> If any provision of these Terms is found
                    to be unenforceable, the remaining provisions will continue in full
                    force and effect.
                  </li>
                  <li>
                    <strong className="text-foreground">Waiver:</strong> Our failure to enforce any right or provision
                    of these Terms shall not constitute a waiver of that right or provision.
                  </li>
                  <li>
                    <strong className="text-foreground">Assignment:</strong> You may not assign your rights or
                    obligations under these Terms without our prior written consent. We may
                    assign our rights and obligations without restriction.
                  </li>
                  <li>
                    <strong className="text-foreground">Force Majeure:</strong> Neither party shall be liable for any
                    failure to perform due to circumstances beyond its reasonable control,
                    including natural disasters, war, pandemic, government action, or
                    infrastructure failures.
                  </li>
                </ul>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">17. Contact</h2>
                <p className="mt-3">
                  For questions about these Terms, please contact us at:
                </p>
                <div className="mt-3 rounded-lg border bg-card p-4">
                  <p className="font-medium text-foreground">Hanzo AI, Inc.</p>
                  <p className="mt-1">
                    Email:{" "}
                    <a
                      href={`mailto:legal@${brand.domain}`}
                      className="text-primary hover:underline"
                    >
                      legal@{brand.domain}
                    </a>
                  </p>
                  <p>San Francisco, California, United States</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
