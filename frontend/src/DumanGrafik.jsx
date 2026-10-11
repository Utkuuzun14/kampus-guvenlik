import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

const API = "http://127.0.0.1:8000";
const ESIK = 1800; // duman eşiği (config.py ile aynı)

function DumanGrafik() {
  const [veri, setVeri] = useState([]);

  const getir = async () => {
    try {
      const cevap = await fetch(`${API}/api/gecmis?sensor=duman&limit=40`);
      if (!cevap.ok) return;
      const gelen = await cevap.json();
      const bicimli = gelen.map((o) => ({
        saat: new Date(o.zaman * 1000).toLocaleTimeString("tr-TR", {
          hour: "2-digit", minute: "2-digit", second: "2-digit",
        }),
        deger: o.deger,
      }));
      setVeri(bicimli);
    } catch (e) {
      // sessiz geç
    }
  };

  useEffect(() => {
    getir();
    const z = setInterval(getir, 3000);
    return () => clearInterval(z);
  }, []);

  const eksenYazi = { fill: "#8b97ad", fontSize: 11, fontFamily: "JetBrains Mono, monospace" };

  return (
    <section className="kart grafik-bolum">
      <h2 className="kart-baslik">Duman/Gaz Seviyesi (canlı)</h2>
      <div className="grafik-kutu">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={veri} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2a44" vertical={false} />
            <XAxis
              dataKey="saat"
              stroke="#1f2a44"
              tick={eksenYazi}
              tickLine={false}
              minTickGap={30}
            />
            <YAxis
              stroke="#1f2a44"
              tick={eksenYazi}
              tickLine={false}
              domain={[0, 4095]}
            />
            <Tooltip
              contentStyle={{
                background: "#0b1120", border: "1px solid #1f2a44",
                borderRadius: 8, color: "#e2e8f0",
                fontFamily: "JetBrains Mono, monospace", fontSize: 12,
              }}
              labelStyle={{ color: "#8b97ad" }}
              itemStyle={{ color: "#22d3ee" }}
              cursor={{ stroke: "#22d3ee", strokeOpacity: 0.3 }}
            />
            <ReferenceLine
              y={ESIK}
              stroke="#ef4444"
              strokeDasharray="6 4"
              label={{ value: "Eşik (1800)", fill: "#ef4444", fontSize: 11, position: "insideTopRight" }}
            />
            <Line
              type="monotone"
              dataKey="deger"
              stroke="#22d3ee"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#22d3ee", stroke: "#0b1120" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default DumanGrafik;
