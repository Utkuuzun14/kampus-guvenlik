import { DURUM_AD } from "../sabitler";
import { durumu } from "../hesaplar";

// Yeni / Görüldü / Müdahalede / Çözüldü rozeti (yalnızca akıştaki olaylar için)
export default function DurumRozeti({ olay }) {
  const d = durumu(olay);
  return <span className={`rozet rozet-durum-${d}`}>{DURUM_AD[d]}</span>;
}
