"use client";

import Image from 'next/image'
import { useTranslations } from 'next-intl';
import { Mail, Share2 } from 'lucide-react';

export default function Footer() {
  const t = useTranslations();

  const PRODUCT_LINKS = [
    { href: "#studio", label: t("footer.studioLink") },
    { href: "#audiences", label: t("footer.audiencesLink") },
  ];

  const COMPANY_LINKS = [
    { href: "#", label: t("footer.aboutLink") },
    { href: "#", label: t("footer.contactLink") },
    { href: "#", label: t("footer.careersLink") },
  ];

  const LEGAL_LINKS = [
    { href: "#", label: t("footer.privacyLink") },
    { href: "#", label: t("footer.termsLink") },
  ];

  return (
    <footer className="bg-brand-cream text-brand-headline pt-20 pb-8 border-t border-brand-accent/20 font-readex" id="footer">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-12 pb-12 border-b border-brand-headline/10">
          <div className="lg:col-span-1">
            <div className="flex items-center gap-3 font-logo text-2xl font-bold text-brand-headline mb-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white p-2 shadow-sm">
                <Image
                  src="/trendy_logo.png"
                  alt="TRENDY AI"
                  width={54}
                  height={54}
                  className="h-12 w-12 object-contain"
                />
              </div>
              Trendy AI
            </div>
            <p className="text-sm leading-relaxed max-w-xs text-brand-ink/70 mb-5">
              {t("footer.tagline")}
            </p>
            <div className="flex gap-3">
              <a
                href="mailto:hello@trendy.ai"
                aria-label="Email"
                className="w-9 h-9 rounded-full border border-brand-accent/40 bg-white text-brand-headline flex items-center justify-center hover:bg-brand-primary hover:text-white hover:border-brand-primary transition-colors"
              >
                <Mail className="w-4 h-4" />
              </a>
              <a
                href="#"
                aria-label="Share"
                className="w-9 h-9 rounded-full border border-brand-accent/40 bg-white text-brand-headline flex items-center justify-center hover:bg-brand-primary hover:text-white hover:border-brand-primary transition-colors"
              >
                <Share2 className="w-4 h-4" />
              </a>
            </div>
          </div>

          <div>
            <h5 className="text-brand-headline font-bold text-sm mb-5 font-ruqaa">{t("footer.product")}</h5>
            <div className="flex flex-col gap-3 text-sm">
              {PRODUCT_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-brand-ink/70 hover:text-brand-primary transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>

          <div>
            <h5 className="text-brand-headline font-bold text-sm mb-5 font-ruqaa">{t("footer.company")}</h5>
            <div className="flex flex-col gap-3 text-sm">
              {COMPANY_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-brand-ink/70 hover:text-brand-primary transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>

          <div>
            <h5 className="text-brand-headline font-bold text-sm mb-5 font-ruqaa">{t("footer.legal")}</h5>
            <div className="flex flex-col gap-3 text-sm">
              {LEGAL_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  className="text-brand-ink/70 hover:text-brand-primary transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="flex flex-col md:flex-row justify-between items-center pt-8 gap-4 text-xs text-brand-ink/60">
          <div className="flex flex-col md:flex-row items-center gap-1 md:gap-3">
            <span>{t("footer.copyright")}</span>
            <span className="hidden md:inline text-brand-accent/60">·</span>
            <span>{t("footer.designCredit")}</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
