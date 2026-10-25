"use client";

import { useState } from "react";
import { useTranslations } from 'next-intl';
import { ArrowLeft, Mail } from "lucide-react";
import Reveal from "./Reveal";

export default function TrialSection() {
  const [submitted, setSubmitted] = useState(false);
  const t = useTranslations();

  const TRIAL_STEPS = [
    {
      n: "1",
      title: t("trial.step1Title"),
      body: t("trial.step1Body"),
    },
    {
      n: "2",
      title: t("trial.step2Title"),
      body: t("trial.step2Body"),
    },
    {
      n: "3",
      title: t("trial.step3Title"),
      body: t("trial.step3Body"),
    },
  ];

  return (
    <section className="py-24 bg-brand-bg relative" id="trial">
      <div className="max-w-7xl mx-auto px-6">
        <Reveal className="max-w-2xl mx-auto text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-brand-accent/10 border border-brand-accent/30 text-brand-headline font-bold text-xs px-4 py-1.5 rounded-full mb-5 font-readex">
            <i className="w-2 h-2 rounded-full bg-brand-primary block" />
            {t("trial.badge")}
          </div>
          <h2 className="text-4xl md:text-5xl mb-5 font-ruqaa text-brand-headline">
            {t("trial.heading")}
          </h2>
          <p className="text-lg opacity-80 leading-relaxed font-readex text-brand-ink">
            {t("trial.subheading")}
          </p>
        </Reveal>

        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <Reveal className="flex flex-col gap-5  mt-2 font-readex text-brand-ink">
            {TRIAL_STEPS.map((step) => (
              <div
                key={step.n}
                className="flex items-center justify-center gap-4 rounded-[28px] bg-[#FDFBF7] border border-brand-accent/15 p-6"
              >
                <div className="w-8 h-8 rounded-full bg-brand-headline text-white flex items-center justify-center text-sm font-ruqaa font-bold shrink-0">
                  {step.n}
                </div>
                <div className="flex-1">
                  <h4 className="text-base font-bold mb-1.5 font-ruqaa text-brand-headline">
                    {step.title}
                  </h4>
                  <p className="text-sm opacity-75 leading-relaxed">{step.body}</p>
                </div>
              </div>
            ))}
          </Reveal>

          <Reveal className="relative">
            <div className="absolute -top-4 left-6 z-10 inline-flex items-center gap-2 bg-[#D4B996] border border-brand-accent/30 text-brand-headline font-bold text-xs px-4 py-1.5 rounded-full font-readex shadow-sm">
              {t("trial.quickBadge")}
            </div>

            <div className="bg-white rounded-[2rem] p-8 md:p-10 pt-10 shadow-card border border-brand-accent/20">
              <h3 className="text-3xl mb-3 font-ruqaa text-brand-headline">
                {t("trial.formHeading")}
              </h3>
              <p className="text-sm text-gray-600 leading-relaxed mb-8 font-readex">
                {t("trial.formSubheading")}
              </p>
              <form
                className="flex flex-col gap-4 font-readex"
                onSubmit={(e) => {
                  e.preventDefault();
                  setSubmitted(true);
                }}
              >
                <div>
                  <label className="block text-xs font-bold text-brand-headline mb-1.5">
                    {t("trial.emailLabel")}
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-gray-400 absolute left-4 top-1/2 -translate-y-1/2" />
                    <input
                      className="w-full ps-11 pe-5 py-4 rounded-xl border border-gray-200 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none bg-gray-50 font-readex text-sm transition-all text-brand-ink"
                      placeholder={t("trial.emailPlaceholder")}
                      required
                      type="email"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-brand-headline mb-1.5">
                    {t("trial.ideaLabel")}
                  </label>
                  <input
                    className="w-full px-5 py-4 rounded-xl border border-gray-200 focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none bg-gray-50 font-readex text-sm transition-all text-brand-ink"
                    placeholder={t("trial.ideaPlaceholder")}
                    required
                    type="text"
                  />
                </div>
                <button
                  className="bg-brand-primary text-white w-full py-4 rounded-full font-bold text-base mt-2 shadow-lg hover:bg-brand-primary/90 transition-colors flex items-center justify-center gap-2"
                  type="submit"
                >
                  <ArrowLeft className="w-4 h-4" />
                  {submitted ? t("trial.submitted") : t("trial.submit")}
                </button>
              </form>
              <div className="text-xs text-center mt-5 text-gray-400 font-medium font-readex">
                {t("trial.noCard")}
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}