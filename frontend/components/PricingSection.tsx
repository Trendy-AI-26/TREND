"use client";

import Reveal from "./Reveal";
import { useTranslations } from "next-intl";
import { Check } from "lucide-react";

export default function PricingSection() {
  const t = useTranslations("pricing");

  const PLANS = [
    {
      price: t("plan1Price"),
      title: t("plan1Title"),
      body: t("plan1Body"),
      includesLabel: t("includesLabel"),
      feature: t("plan1Feature"),
      button: t("plan1Button"),
      popular: false,
    },
    {
      price: t("plan2Price"),
      title: t("plan2Title"),
      body: t("plan2Body"),
      includesLabel: t("includesLabelPopular"),
      feature: t("plan2Feature"),
      button: t("plan2Button"),
      popular: true,
    },
    {
      price: t("plan3Price"),
      title: t("plan3Title"),
      body: t("plan3Body"),
      includesLabel: t("includesLabel"),
      feature: t("plan3Feature"),
      button: t("plan3Button"),
      popular: false,
    },
  ];

  return (
    <section className="py-24 bg-brand-cream relative" id="pricing">
      <div className="max-w-7xl mx-auto px-6">
        <Reveal className="mb-14">
          <div className="flex justify-center mb-5">
            <div className="inline-flex items-center gap-2 bg-brand-accent/10 border border-brand-accent/30 text-brand-headline font-bold text-xs px-4 py-1.5 rounded-full font-readex">
              <i className="w-2 h-2 rounded-full bg-[#7A1521] block" />
              {t("badge")}
            </div>
          </div>
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-4xl md:text-5xl mb-4 font-ruqaa text-brand-headline">
              {t("heading")}
            </h2>
            <p className="text-lg opacity-80 leading-relaxed font-readex text-brand-ink">
              {t("subheading")}
            </p>
          </div>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-6 items-center">
          {PLANS.map((plan) => (
            <Reveal key={plan.title} className={plan.popular ? "relative md:-translate-y-4" : "relative"}>
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10 whitespace-nowrap rounded-full border border-brand-primary/30 bg-brand-cream px-4 py-1.5 text-xs font-bold text-brand-primary shadow-sm font-readex">
                  {t("popularRibbon")}
                </div>
              )}
              <div
                className={`h-full rounded-3xl p-8 border flex flex-col ${plan.popular
                  ? "bg-[#7A1521] text-white border-[#7A1521] shadow-vintage"
                  : "bg-white text-brand-headline border-brand-accent/20 shadow-sm"
                  }`}
              >
                <div className="flex items-center justify-between gap-3 mb-4 font-readex">
                  <h3 className="font-ruqaa font-bold text-xl">{plan.title}</h3>
                  <span
                    className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold whitespace-nowrap ${plan.popular
                      ? "bg-white text-brand-primary"
                      : "bg-brand-accent/10 text-brand-headline border border-brand-accent/30"
                      }`}
                  >
                    {plan.price} / {t("perMonth")}
                  </span>
                </div>

                <p
                  className={`text-sm leading-relaxed mb-6 font-readex ${plan.popular ? "text-white/85" : "opacity-70"
                    }`}
                >
                  {plan.body}
                </p>

                <div
                  className={`border-t pt-5 mb-5 ${plan.popular ? "border-white/20" : "border-brand-accent/20"
                    }`}
                >
                  <div
                    className={`text-xs font-bold mb-3 font-readex ${plan.popular ? "text-white/70" : "text-brand-headline/60"
                      }`}
                  >
                    {plan.includesLabel}
                  </div>
                  <div className="flex items-center gap-2 text-sm font-readex">
                    <span
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${plan.popular ? "bg-white/20 text-white" : "bg-brand-primary/10 text-brand-primary"
                        }`}
                    >
                      <Check className="w-3 h-3" />
                    </span>
                    {plan.feature}
                  </div>
                </div>

                <button
                  type="button"
                  className={`mt-auto w-full py-3.5 rounded-xl text-sm font-bold transition-colors font-readex ${plan.popular
                    ? "bg-white text-brand-primary hover:bg-brand-cream"
                    : "border border-brand-headline text-brand-headline hover:bg-brand-headline hover:text-white"
                    }`}
                >
                  {plan.button}
                </button>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
