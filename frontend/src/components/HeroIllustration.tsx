import trustHero from '../assets/trustmedai-hero.svg';

export default function HeroIllustration() {
  return (
    <div className="relative min-h-[360px] overflow-hidden rounded border border-teal-900/10 bg-white shadow-panel">
      <img src={trustHero} alt="AI diagnosis and blockchain trust network" className="h-full min-h-[360px] w-full object-cover" />
      <div className="absolute bottom-4 left-4 right-4 grid grid-cols-3 gap-2">
        {['AECS 0.94', 'DTEI 0.91', 'Hash anchored'].map((item) => (
          <div key={item} className="rounded bg-white/88 px-3 py-2 text-center text-sm font-semibold text-trust-ink shadow">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
