import { MarketingNav } from "@/components/marketing/marketing-nav";
import { Hero } from "@/components/marketing/hero";
import { Features } from "@/components/marketing/features";
import { IntegrationsSection } from "@/components/marketing/integrations-section";
import { ShowcaseGallery } from "@/components/marketing/showcase-gallery";
import { WhyScotch } from "@/components/marketing/why-scotch";
import { AboutSection } from "@/components/marketing/about-section";
import { Faq } from "@/components/marketing/faq";
import { CtaBand } from "@/components/marketing/cta-band";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

export default function LandingPage() {
  return (
    <div className="flex flex-1 flex-col">
      <MarketingNav />
      <main className="flex-1">
        <Hero />
        <Features />
        <IntegrationsSection />
        <ShowcaseGallery />
        <WhyScotch />
        <AboutSection />
        <Faq />
        <CtaBand />
      </main>
      <MarketingFooter />
    </div>
  );
}
