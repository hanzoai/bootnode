import Link from "next/link"
import type { Metadata } from "next"
import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import { Badge } from "@/components/ui/badge"
import { Shield } from "lucide-react"
import { getBrand } from "@/lib/brand"

const brand = getBrand()

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    `${brand.name} Privacy Policy. Learn how we collect, use, and protect your personal information.`,
}

export default function PrivacyPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      {/* Hero */}
      <section className="border-b bg-gradient-to-b from-background to-muted/20">
        <div className="container py-16 md:py-20">
          <div className="mx-auto max-w-3xl">
            <Badge variant="secondary" className="mb-4">
              <Shield className="mr-1 h-3 w-3" />
              Legal
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Privacy Policy
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
          <div className="prose prose-invert mx-auto max-w-3xl">
            <div className="space-y-8 text-sm text-muted-foreground leading-relaxed">
              <div>
                <h2 className="text-xl font-semibold text-foreground">1. Introduction</h2>
                <p className="mt-3">
                  Hanzo AI, Inc. (&quot;Hanzo,&quot; &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;) operates the
                  hanzo.ai website and the Hanzo Web3 API platform (collectively, the
                  &quot;Service&quot;). This Privacy Policy explains how we collect, use, disclose,
                  and safeguard your information when you use our Service.
                </p>
                <p className="mt-3">
                  By accessing or using the Service, you agree to this Privacy Policy. If
                  you do not agree with the terms of this policy, please do not access the
                  Service.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">2. Information We Collect</h2>

                <h3 className="mt-4 text-base font-semibold text-foreground">2.1 Information You Provide</h3>
                <p className="mt-2">We collect information you voluntarily provide when you:</p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>Create an account (email address, name, password)</li>
                  <li>Subscribe to a paid plan (billing address, payment information via our payment processor)</li>
                  <li>Contact us via email or our contact form (name, email, message content)</li>
                  <li>Participate in surveys or promotions</li>
                </ul>

                <h3 className="mt-4 text-base font-semibold text-foreground">2.2 Information Collected Automatically</h3>
                <p className="mt-2">When you use the Service, we automatically collect:</p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>API usage data (request counts, methods called, response times, error rates)</li>
                  <li>IP addresses used to make API requests</li>
                  <li>Device and browser information when using the dashboard</li>
                  <li>Cookies and similar tracking technologies for authentication and analytics</li>
                  <li>Log data (timestamps, request paths, HTTP status codes)</li>
                </ul>

                <h3 className="mt-4 text-base font-semibold text-foreground">2.3 Information We Do Not Collect</h3>
                <p className="mt-2">
                  We do not inspect, store, or log the content of your API request bodies or
                  response bodies beyond what is necessary for rate limiting and abuse
                  prevention. We do not collect or store private keys, seed phrases, or
                  wallet passwords.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">3. How We Use Your Information</h2>
                <p className="mt-3">We use collected information to:</p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>Provide, operate, and maintain the Service</li>
                  <li>Process transactions and send related billing information</li>
                  <li>Monitor API usage for rate limiting, abuse prevention, and capacity planning</li>
                  <li>Send service-related notices, including downtime alerts and security notifications</li>
                  <li>Respond to your comments, questions, and support requests</li>
                  <li>Analyze usage patterns to improve the Service</li>
                  <li>Detect, prevent, and address technical issues, fraud, and security breaches</li>
                  <li>Comply with legal obligations</li>
                </ul>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">4. How We Share Your Information</h2>
                <p className="mt-3">We do not sell your personal information. We may share information with:</p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>
                    <strong className="text-foreground">Service providers:</strong> Third-party vendors who assist
                    in operating the Service (e.g., Square for payments, cloud infrastructure
                    providers for hosting, analytics providers). These vendors are
                    contractually obligated to protect your information.
                  </li>
                  <li>
                    <strong className="text-foreground">Legal requirements:</strong> When required by law, subpoena,
                    or other legal process, or when we believe disclosure is necessary to
                    protect our rights, your safety, or the safety of others.
                  </li>
                  <li>
                    <strong className="text-foreground">Business transfers:</strong> In connection with a merger,
                    acquisition, or sale of assets, your information may be transferred as
                    part of the transaction.
                  </li>
                  <li>
                    <strong className="text-foreground">With your consent:</strong> We may share information for any
                    other purpose with your explicit consent.
                  </li>
                </ul>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">5. Data Retention</h2>
                <p className="mt-3">
                  We retain your account information for as long as your account is active or
                  as needed to provide the Service. API usage logs are retained for 30 days
                  (Growth plan) or 90 days (Enterprise plan). After account deletion, we
                  retain minimal data as required by law or legitimate business purposes
                  (e.g., fraud prevention) for up to 12 months, after which it is permanently
                  deleted.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">6. Data Security</h2>
                <p className="mt-3">
                  We implement industry-standard security measures to protect your
                  information, including encryption in transit (TLS 1.3), encryption at rest
                  (AES-256), API key hashing (bcrypt), and strict access controls. However,
                  no method of transmission over the Internet is 100% secure. See our{" "}
                  <Link href="/security" className="text-primary hover:underline">
                    Security page
                  </Link>{" "}
                  for detailed information about our security practices.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">7. Your Rights</h2>
                <p className="mt-3">Depending on your location, you may have the right to:</p>
                <ul className="mt-2 ml-4 list-disc space-y-1">
                  <li>Access the personal data we hold about you</li>
                  <li>Correct inaccurate personal data</li>
                  <li>Delete your personal data</li>
                  <li>Export your data in a portable format</li>
                  <li>Restrict or object to processing of your personal data</li>
                  <li>Withdraw consent at any time (where processing is based on consent)</li>
                </ul>
                <p className="mt-3">
                  To exercise these rights, contact us at{" "}
                  <a
                    href="mailto:privacy@hanzo.ai"
                    className="text-primary hover:underline"
                  >
                    privacy@hanzo.ai
                  </a>
                  . We will respond within 30 days.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">8. Cookies</h2>
                <p className="mt-3">
                  We use essential cookies for authentication and session management. We
                  use analytics cookies (which can be opted out of) to understand how the
                  Service is used. We do not use advertising cookies or sell cookie data to
                  third parties. You can control cookie settings through your browser
                  preferences.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">9. International Data Transfers</h2>
                <p className="mt-3">
                  Your information may be transferred to and processed in countries other than
                  your own. We ensure appropriate safeguards are in place, including Standard
                  Contractual Clauses approved by the European Commission, for any transfers
                  of personal data outside the European Economic Area.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">10. Children&apos;s Privacy</h2>
                <p className="mt-3">
                  The Service is not intended for individuals under 16 years of age. We do not
                  knowingly collect personal information from children under 16. If you become
                  aware that a child has provided us with personal information, please contact
                  us and we will take steps to delete such information.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">11. Changes to This Policy</h2>
                <p className="mt-3">
                  We may update this Privacy Policy from time to time. We will notify you of
                  material changes by posting the new policy on this page and updating the
                  &quot;Effective date&quot; above. For significant changes, we will provide additional
                  notice via email or a banner on the Service. Your continued use of the
                  Service after changes become effective constitutes acceptance of the revised
                  policy.
                </p>
              </div>

              <div>
                <h2 className="text-xl font-semibold text-foreground">12. Contact Us</h2>
                <p className="mt-3">
                  If you have questions about this Privacy Policy or our data practices,
                  please contact us at:
                </p>
                <div className="mt-3 rounded-lg border bg-card p-4">
                  <p className="font-medium text-foreground">Hanzo AI, Inc.</p>
                  <p className="mt-1">Email:{" "}
                    <a
                      href="mailto:privacy@hanzo.ai"
                      className="text-primary hover:underline"
                    >
                      privacy@hanzo.ai
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
