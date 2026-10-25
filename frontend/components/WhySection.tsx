"use client";

import Reveal from "./Reveal";
import { useTranslations } from 'next-intl';

export default function WhySection() {
  const t = useTranslations();

  const FEATURES = [
    {
      tag: t("why.tag1"),
      title: t("why.title1"),
      body: t("why.body1"),
    },
    {
      tag: t("why.tag2"),
      title: t("why.title2"),
      body: t("why.body2"),
    },
    {
      tag: t("why.tag3"),
      title: t("why.title3"),
      body: t("why.body3"),
    },
  ];

  return (
    <section className="py-24 bg-brand-headline text-brand-bg relative border-y border-brand-accent/20" id="why">
      <div className="max-w-7xl mx-auto px-6">
        <Reveal className="max-w-2xl mb-14">
          <div className="inline-flex items-center gap-2 bg-brand-bg/10 border border-brand-bg/20 text-brand-bg font-bold text-xs px-4 py-1.5 rounded-full mb-5 font-readex">
            <i className="w-2 h-2 rounded-full bg-brand-accent block" />
            {t("why.badge")}
          </div>
          <h2 className="text-4xl md:text-5xl mb-4 text-white font-ruqaa">
            {t("why.heading")}
          </h2>
          <p className="text-lg opacity-80 leading-relaxed font-readex">
            {t("why.subheading")}
          </p>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-8">
          {FEATURES.map((feature) => (
            <Reveal
              key={feature.title}
              className="bg-brand-bg/5 border border-brand-accent/20 rounded-2xl p-8 hover:-translate-y-1.5 hover:bg-brand-bg/10 transition-all duration-300 group"
            >
              <div className="font-ruqaa text-brand-accent text-lg mb-4 tracking-wider group-hover:text-brand-primary transition-colors">
                {feature.tag}
              </div>
              <h3 className="font-ruqaa font-bold text-2xl text-white mb-3">
                {feature.title}
              </h3>
              <p className="text-sm opacity-70 leading-relaxed font-readex">
                {feature.body}
              </p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
