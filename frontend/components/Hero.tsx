"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";

const SLIDES = [
  { src: "/hero/arch-1.jpg", alt: "", position: "center" },
  { src: "/hero/arch-2.jpg", alt: "", position: "center 70%" },
  { src: "/hero/arch-3.jpg", alt: "", position: "center" },
];

export default function Hero() {
  const t = useTranslations("hero");
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setActive((i) => (i + 1) % SLIDES.length);
    }, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <section
      className="relative overflow-hidden bg-brand-headline text-brand-cream"
      id="hero"
    >
      {/* Background photo carousel */}
      <div className="absolute inset-0" aria-hidden="true">
        {SLIDES.map((slide, i) => (
          <div
            key={slide.src}
            className={`absolute inset-0 transition-opacity duration-[1500ms] ease-out ${i === active ? "opacity-100" : "opacity-0"
              }`}
          >
            <Image
              src={slide.src}
              alt={slide.alt}
              fill
              priority={i === 0}
              sizes="100vw"
              className="object-cover"
              style={{ objectPosition: slide.position }}
            />
          </div>
        ))}
        <div className="absolute inset-0 bg-gradient-to-t from-brand-headline via-brand-headline/50 to-brand-headline/30" />
        <div className="absolute inset-0 bg-black/25" />
      </div>

      <div className="relative z-10 mx-auto flex max-w-4xl flex-col items-center px-6 pb-24 pt-40 text-center md:pb-32 md:pt-48">
        <div className="mb-5 font-logo text-2xl text-brand-accent md:text-3xl">
          {t("wordmark")}
        </div>
        <h1 className="mb-6 font-ruqaa text-4xl font-bold leading-tight text-white md:text-6xl">
          {t("headline1")}
          <br />
          {t("headline2")}
        </h1>
        <p className="mb-10 max-w-xl text-base leading-relaxed text-brand-cream/80 font-readex md:text-lg">
          {t("subheading")}
        </p>
        <a
          href="#idea-to-brand"
          className="inline-flex items-center gap-2 rounded-full bg-brand-primary px-8 py-3.5 text-base font-bold text-white shadow-vintage transition-all duration-200 hover:-translate-y-1 hover:shadow-xl hover:bg-white font-readex"
        >
          {t("cta")}
          <span aria-hidden="true">↓</span>
        </a>

        {/* Carousel dots */}
        <div className="mt-14 flex items-center gap-2" role="tablist" aria-label={t("wordmark")}>
          {SLIDES.map((slide, i) => (
            <button
              key={slide.src}
              type="button"
              role="tab"
              aria-selected={i === active}
              aria-label={`${i + 1}`}
              onClick={() => setActive(i)}
              className={`h-1.5 rounded-full transition-all duration-300 ${i === active ? "w-8 bg-brand-accent" : "w-1.5 bg-white/40 hover:bg-white/70"
                }`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
