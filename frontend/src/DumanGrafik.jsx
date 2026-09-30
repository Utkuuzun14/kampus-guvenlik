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

  return (
    <div className="grafik-bolum">
      <h2>Duman/Gaz Seviyesi (canlı)</h2>
      <div className="grafik-kutu">
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={veri} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="saat" stroke="#64748b" fontSize={11} minTickGap={30} />
            <YAxis stroke="#64748b" fontSize={11} domain={[0, 4095]} />
            <Tooltip
              contentStyle={{
                background: "#1e293b", border: "1px solid #334155",
                borderRadius: 8, color: "#e2e8f0",
              }}
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
              stroke="#38bdf8"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default DumanGrafik;
