"use client";

import Reveal from "./Reveal";
import { useTranslations } from "next-intl";
import { RefreshCw, LayoutGrid, Download, Heart, Instagram, Linkedin, Twitter, Check } from "lucide-react";

export default function StudioSection() {
  const t = useTranslations("studio");

  const WORKFLOW_STEPS = [
    { n: "1", label: t("step1"), done: true },
    { n: "2", label: t("step2"), done: true },
    { n: "3", label: t("step3"), done: false, active: true },
    { n: "4", label: t("step4"), done: false },
  ];

  const STUDIO_FEATURES = [
    { icon: RefreshCw, title: t("feature1Title"), body: t("feature1Body") },
    { icon: LayoutGrid, title: t("feature2Title"), body: t("feature2Body") },
    { icon: Download, title: t("feature3Title"), body: t("feature3Body") },
  ];

  const SLIDES = [
    { tag: t("slide1Tag"), label: t("slide1Title"), heading: t("slide1Heading"), body: t("slide1Body"), link: t("slide1Link"), dark: true },
    { tag: t("slide2Tag"), label: t("slide2Title"), heading: t("slide2Heading"), body: t("slide2Body"), link: t("slide2Link"), dark: false },
    { tag: t("slide3Tag"), label: t("slide3Title"), heading: t("slide3Heading"), sub: t("slide3Sub"), body: t("slide3Body"), link: t("slide3Link"), dark: true, badge: t("slide3Badge") },
  ];

  const PLATFORM_TABS = [
    { icon: Instagram, label: t("tabInstagram"), active: true },
    { icon: Linkedin, label: t("tabLinkedin"), active: false },
    { icon: Twitter, label: t("tabX"), active: false },
  ];

  return (
    <section className="py-24 bg-brand-cream relative" id="studio">
      <div className="max-w-7xl mx-auto px-6 flex flex-col items-center gap-14">
        <Reveal className="max-w-2xl text-center">
          <div className="inline-flex items-center gap-2 bg-brand-accent/10 border border-brand-accent/30 text-brand-headline font-bold text-xs px-4 py-1.5 rounded-full mb-5 font-readex">
            <i className="w-2 h-2 rounded-full bg-brand-primary block" />
            {t("badge")}
          </div>
          <h2 className="text-4xl md:text-5xl mb-6 font-ruqaa text-brand-headline">
            {t("heading")}
          </h2>
          <p className="text-lg opacity-80 leading-relaxed mb-8 font-readex text-brand-ink">
            {t("subheading")}
          </p>

          <div className="flex flex-wrap justify-center gap-2 font-readex">
            {WORKFLOW_STEPS.map((step) => (
              <div
                key={step.n}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-bold border transition-colors ${step.active
                  ? "bg-brand-primary text-white border-brand-primary shadow-md"
                  : "bg-white text-brand-headline border-brand-accent/30"
                  }`}
              >
                {step.done ? (
                  <Check className="w-3.5 h-3.5 shrink-0" />
                ) : (
                  <b className="font-ruqaa text-base">{step.n}</b>
                )}
                {step.label}
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal className="relative w-full max-w-3xl mx-auto">
          <div className="bg-white rounded-3xl p-6 shadow-card border border-brand-accent/20 relative z-10">
            <div className="flex justify-between items-center mb-4 border-b border-gray-100 pb-4 font-readex">
              <div className="flex items-center gap-3 font-bold text-sm text-brand-headline">
                <div className="w-8 h-8 rounded-full bg-brand-headline flex items-center justify-center text-brand-accent font-logo text-xs">
                  N
                </div>
                Noura Coffee
                <span className="text-[10px] font-bold text-brand-primary bg-brand-primary/10 px-2 py-0.5 rounded-full">
                  {t("verifiedBadge")}
                </span>
              </div>
              <span className="w-2.5 h-2.5 rounded-full bg-brand-primary" />
            </div>

            <div className="flex gap-4 mb-4 text-xs font-bold font-readex">
              {PLATFORM_TABS.map((tab) => (
                <div
                  key={tab.label}
                  className={`flex items-center gap-1.5 pb-2 border-b-2 ${tab.active
                    ? "text-brand-headline border-brand-primary"
                    : "text-gray-400 border-transparent"
                    }`}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  {tab.label}
                </div>
              ))}
            </div>

            <div className="text-xs text-gray-500 mb-4 font-readex">
              {t("previewCaption")}
            </div>

            <div className="grid grid-cols-3 gap-2.5 mb-4">
              {SLIDES.map((slide, i) => (
                <div
                  key={i}
                  className={`aspect-[4/5] rounded-xl border border-brand-accent/30 flex flex-col justify-between p-2.5 text-center shadow-inner ${slide.dark ? "bg-brand-headline text-white" : "bg-brand-bg text-brand-headline"
                    }`}
                >
                  <div className="flex items-center justify-between text-[8px] opacity-70 font-readex">
                    <span>{slide.tag}</span>
                    {slide.badge && (
                      <span className="rounded-full bg-brand-primary px-1.5 py-0.5 text-white">{slide.badge}</span>
                    )}
                  </div>
                  <div>
                    <div className="text-[7px] uppercase tracking-wide opacity-60 mb-1 font-readex">{slide.label}</div>
                    <div className="font-ruqaa text-[11px] leading-tight whitespace-pre-line">{slide.heading}</div>
                    {slide.sub && <div className="text-[8px] mt-1 opacity-80 font-readex">{slide.sub}</div>}
                  </div>
                  <div className="text-[7px] opacity-60 font-readex">{slide.link} ‹</div>
                </div>
              ))}
            </div>

            <div className="bg-gray-50 border border-gray-100 rounded-xl p-3 mb-2 font-readex">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[11px] font-bold text-brand-headline">{t("captionHeading")}</span>
                <button type="button" className="text-[10px] font-bold text-brand-primary shrink-0 ms-2">
                  {t("copyText")}
                </button>
              </div>
              <p className="text-[11px] text-gray-600 leading-relaxed">{t("captionBody")}</p>
            </div>
          </div>

          <div className="grid sm:grid-cols-3 gap-3 mt-5 font-readex">
            {STUDIO_FEATURES.map((feature) => (
              <div key={feature.title} className="bg-white border border-brand-accent/20 rounded-2xl p-4 flex flex-col items-start gap-2 shadow-sm">
                <div className="w-9 h-9 rounded-lg bg-brand-primary/10 text-brand-primary flex items-center justify-center shrink-0 border border-brand-primary/20">
                  <feature.icon className="w-4 h-4" />
                </div>
                <h4 className="text-xs font-bold font-ruqaa text-brand-headline">{feature.title}</h4>
                <p className="text-[11px] opacity-70 leading-relaxed">{feature.body}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-col items-start gap-3 mt-4 font-readex">
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-bold border border-brand-headline text-brand-headline hover:bg-white transition-colors"
            >
              <Heart className="w-4 h-4" />
              {t("saveFavorite")}
            </button>
            <button
              type="button"
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold bg-brand-primary text-white hover:bg-brand-primary/90 shadow-md transition-colors"
            >
              <Download className="w-4 h-4" />
              {t("downloadZip")}
            </button>
          </div>

          <div className="absolute -top-6 -left-6 w-32 h-32 bg-brand-accent/20 rounded-full blur-3xl -z-10" />
          <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-brand-primary/10 rounded-full blur-3xl -z-10" />
        </Reveal>
      </div>
    </section>
  );
}