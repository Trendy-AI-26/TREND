import Header from "@/components/Header";
import Hero from "@/components/Hero";
import PricingSection from "@/components/PricingSection";
import IdeaToBrandSection from "@/components/IdeaToBrandSection";
import WhySection from "@/components/WhySection";
import StudioSection from "@/components/StudioSection";
import TrialSection from "@/components/TrialSection";
import AudiencesSection from "@/components/AudiencesSection";
import FinalCtaSection from "@/components/FinalCtaSection";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <>
      <Header />
      <Hero />
      <IdeaToBrandSection />
      <WhySection />
      <StudioSection />
      <TrialSection />
      <AudiencesSection />
      <PricingSection />
      <FinalCtaSection />
      <Footer />
    </>
  );
}
