import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { saatBicim } from "./hesaplar";

const EKSEN = { fill: "#6b7a96", fontSize: 10, fontFamily: "JetBrains Mono, monospace" };

// Duman göstergesinin altındaki küçük grafik (son 60 sn)
function DumanGrafik({ veri, esik, ust }) {
  const noktalar = veri.map((o) => ({ saat: saatBicim(o.zaman), deger: o.deger }));

  return (
    <div className="mini-grafik">
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={noktalar} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#16213a" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="saat" tick={EKSEN} tickLine={false} axisLine={false} minTickGap={40} />
          <YAxis tick={EKSEN} tickLine={false} axisLine={false} width={34} domain={[0, ust]} />
          <Tooltip
            contentStyle={{
              background: "#060b16", border: "1px solid #24345a", borderRadius: 8,
              color: "#e6edf7", fontFamily: "JetBrains Mono, monospace", fontSize: 12,
            }}
            labelStyle={{ color: "#8b9bb8" }}
            itemStyle={{ color: "#22d3ee" }}
            cursor={{ stroke: "#22d3ee", strokeOpacity: 0.3 }}
            formatter={(v) => [v, "MQ-2"]}
          />
          <ReferenceLine y={esik} stroke="#f43f5e" strokeDasharray="6 4" />
          <Line
            type="monotone"
            dataKey="deger"
            stroke="#22d3ee"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: "#22d3ee", stroke: "#050912" }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default DumanGrafik;
