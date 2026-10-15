import { KURAL_AD } from "../sabitler";

// Olayı üreten kuralın küçük rozeti ("Gece kuralı", "Korelasyon"...).
// Eski kayıtlarda kural yoktur; o zaman hiçbir şey çizilmez.
export default function KuralRozeti({ kural }) {
  if (!kural) return null;
  return (
    <span className={`kural-rozet kural-${kural}`} title="Olayı üreten kural">
      {KURAL_AD[kural] ?? kural}
    </span>
  );
}
