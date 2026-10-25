"use client";

import Image from "next/image";
import Reveal from "./Reveal";
import { useTranslations } from "next-intl";

export default function FinalCtaSection() {
  const t = useTranslations("finalCta");

  return (
    <section className="relative overflow-hidden" id="final-cta">
      <div className="absolute inset-0" aria-hidden="true">
        <Image
          src="/cta/rug-bg.jpg"
          alt=""
          fill
          sizes="100vw"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-brand-headline/20" />

      </div>

      <Reveal className="relative z-10 mx-auto flex max-w-3xl flex-col items-center px-6 py-24 text-center md:py-32">
        <h2 className="mb-5 font-ruqaa text-3xl leading-tight text-white md:text-5xl">
          {t("heading")}
        </h2>
        <p className="mb-10 max-w-xl text-base leading-relaxed text-brand-bg/85 font-readex md:text-lg">
          {t("subheading")}
        </p>
        <a
          href="#trial"
          className="inline-flex items-center gap-2 rounded-full bg-white px-8 py-3.5 text-base font-bold text-brand-headline shadow-vintage transition-all duration-200 hover:-translate-y-1 hover:shadow-xl font-readex"
        >
          {t("cta")}
          <span aria-hidden="true">←</span>
        </a>
      </Reveal>
    </section>
  );
}
