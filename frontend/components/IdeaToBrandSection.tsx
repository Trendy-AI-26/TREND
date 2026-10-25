"use client";

import Reveal from "./Reveal";
import { useTranslations } from "next-intl";

export default function IdeaToBrandSection() {
  const t = useTranslations("ideaToBrand");

  const PHONE_STEPS = [
    { n: "1", label: t("phoneStep1"), active: true },
    { n: "2", label: t("phoneStep2"), active: false },
    { n: "3", label: t("phoneStep3"), active: false },
    { n: "4", label: t("phoneStep4"), active: false },
  ];

  return (
    <section className="relative overflow-hidden bg-brand-cream py-20 md:py-28" id="idea-to-brand">
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-6 lg:grid-cols-[0.95fr_1.05fr]">
        <Reveal className="relative flex justify-center order-last">
          <div className="relative w-[280px] rounded-[2.5rem] border border-white/10 bg-[#111] p-3 shadow-2xl">
            <div className="flex h-[520px] flex-col overflow-hidden rounded-[1.75rem] bg-white">
              <div className="flex items-center justify-between bg-brand-headline px-4 py-3 text-white">
                <div className="flex items-center gap-1 font-logo text-sm text-brand-accent">
                  <span className="h-1.5 w-1.5 rounded-full bg-brand-primary" /> Trendy
                </div>
                <div className="text-[10px] opacity-70 font-readex">{t("phoneHeader")}</div>
              </div>

              <div className="flex justify-between px-4 pb-1 pt-3 text-[10px] font-bold text-gray-400 font-readex">
                {PHONE_STEPS.map((step) => (
                  <div
                    key={step.n}
                    className={`flex flex-1 flex-col items-center gap-1.5 ${step.active ? "text-brand-headline" : ""}`}
                  >
                    <div
                      className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] ${step.active ? "bg-brand-primary text-white" : "bg-gray-100"
                        }`}
                    >
                      {step.n}
                    </div>
                    {step.label}
                  </div>
                ))}
              </div>

              <div className="flex-1 bg-brand-cream/30 p-4 text-[11px] text-brand-headline font-readex">
                <div className="mb-1.5 mt-2 text-[12px] font-bold">{t("phoneField1")}</div>
                <div className="mb-2 rounded-lg border border-brand-accent/30 bg-white p-2.5 text-[10.5px] text-gray-500">
                  {t("phoneField1Placeholder")}
                </div>
                <div className="mb-1.5 mt-3 text-[12px] font-bold">{t("phoneField2")}</div>
                <div className="mb-2 rounded-lg border border-brand-accent/30 bg-white p-2.5 text-[10.5px] text-gray-400">
                  {t("phoneField2Placeholder")}
                </div>
                <div className="mb-1.5 mt-3 text-[12px] font-bold">{t("phoneField3")}</div>
                <div className="mb-2 flex gap-2">
                  <div className="flex-1 text-center">
                    <div className="mb-1 h-6 rounded-md border border-black/10 bg-brand-headline" />
                    <span className="text-[8.5px] text-gray-500">{t("phonePrimary")}</span>
                  </div>
                  <div className="flex-1 text-center">
                    <div className="mb-1 h-6 rounded-md border border-black/10 bg-brand-primary" />
                    <span className="text-[8.5px] text-gray-500">{t("phoneSecondary")}</span>
                  </div>
                  <div className="flex-1 text-center">
                    <div className="mb-1 h-6 rounded-md border border-black/10 bg-brand-accent" />
                    <span className="text-[8.5px] text-gray-500">{t("phoneAccent")}</span>
                  </div>
                </div>
                <div className="mt-4 rounded-lg bg-brand-primary p-2.5 text-center text-[12px] font-bold text-white shadow-sm">
                  {t("phoneNext")} ←
                </div>
              </div>
            </div>
          </div>

          <div className="absolute -top-3 start-0 z-20 hidden items-center gap-2 rounded-2xl border border-brand-accent/20 bg-white p-3 text-xs font-bold text-brand-headline shadow-xl sm:flex font-readex">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary">✎</span>
            {t("phoneBadgeTop")}
          </div>
          <div className="absolute -bottom-4 end-4 z-20 hidden items-center gap-2 rounded-2xl border border-brand-accent/20 bg-white p-3 text-xs font-bold text-brand-headline shadow-xl sm:flex font-readex">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-50 text-sm text-green-600">✓</span>
            {t("phoneBadgeBottom")}
          </div>
        </Reveal>

        <Reveal>
          <div className="mb-5 flex flex-wrap items-center gap-2 font-readex">
            <span className="inline-flex items-center gap-2 rounded-full border border-brand-accent/30 bg-brand-accent/10 px-4 py-1.5 text-xs font-bold text-brand-headline">
              <i className="block h-2 w-2 rounded-full bg-brand-primary" />
              {t("badge1")}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-brand-accent/30 bg-white px-4 py-1.5 text-xs font-bold text-brand-headline">
              <i className="block h-2 w-2 rounded-full bg-brand-accent" />
              {t("badge2")}
            </span>
          </div>
          <h2 className="mb-6 font-ruqaa text-4xl leading-tight text-brand-headline md:text-5xl">
            {t("heading1")}
            <br />
            <em className="not-italic text-brand-primary">{t("heading2")}</em>
            <br />
            {t("heading3")}
          </h2>
          <p className="mb-10 max-w-lg text-lg leading-relaxed text-brand-ink/80 font-readex">
            {t("body")}
          </p>
          <a
            href="#trial"
            className="inline-flex items-center gap-2 rounded-full bg-brand-primary px-8 py-3.5 text-base font-bold text-white shadow-vintage transition-all duration-200 hover:-translate-y-1 hover:shadow-xl font-readex"
          >
            {t("button")}
            <span aria-hidden="true">←</span>
          </a>
        </Reveal>
      </div>
    </section>
  );
}
