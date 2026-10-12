// docs/tasarim/KomutaMerkezi.dc.html'deki dört harita görünümünün STATİK SVG katmanları
// (zemin, binalar, sahalar, ağaçlar, etiketler). Tasarımdan birebir çevrildi; modül
// yüklenirken bir kez oluşturulur. Canlı katman (alarm halesi, akış çizgileri,
// Mosquitto, düğümler) KampusHaritasi.jsx'te çizilir.

// <sc-if gKroki>
export const KUS_KROKI = (
  <>
    <rect x="15" y="0" width="1985" height="1230" fill="#060a14" />
    <polygon points="745,60 2000,0 2000,1230 15,1230 15,794" fill="#0a111f" />
    <g fill="#0e1626" stroke="#18233b" strokeWidth="2">
      <rect x="15" y="170" width="185" height="130" rx="3" />
      <rect x="90" y="85" width="75" height="35" rx="2" />
      <rect x="15" y="390" width="185" height="80" rx="2" />
    </g>
    <g fill="rgba(190,80,70,.35)">
      <rect x="15" y="230" width="230" height="22" /><rect x="15" y="262" width="200" height="22" /><rect x="15" y="300" width="160" height="22" /><rect x="15" y="335" width="120" height="22" /><rect x="15" y="362" width="80" height="20" />
    </g>
    <g stroke="#16213a" strokeLinecap="round" fill="none">
      <line x1="15" y1="213" x2="2000" y2="210" strokeWidth="22" />
      <line x1="15" y1="545" x2="415" y2="215" strokeWidth="16" />
      <line x1="1690" y1="40" x2="2000" y2="205" strokeWidth="18" />
      <line x1="1880" y1="222" x2="2000" y2="330" strokeWidth="10" />
      <path d="M960 262 C1000 262 1010 250 1060 245" strokeWidth="12" />
      <line x1="1040" y1="355" x2="1460" y2="352" strokeWidth="10" />
      <line x1="1450" y1="400" x2="2000" y2="398" strokeWidth="10" />
      <path d="M1300 225 L1560 640" strokeWidth="10" />
    </g>
    <line x1="745" y1="60" x2="15" y2="794" stroke="rgba(34,211,238,.35)" strokeWidth="4" strokeDasharray="6 14" />
    <line x1="700" y1="112" x2="1050" y2="112" stroke="#1d2a44" strokeWidth="3" />
    <polygon points="1085,225 1370,222 1445,345 1100,350" fill="#0f1829" stroke="#1c2945" strokeWidth="2" />
    <line x1="1250" y1="230" x2="1275" y2="348" stroke="#10301f" strokeWidth="22" />
    <g stroke="#1f2c4a" strokeWidth="2">
      <line x1="1110" y1="232" x2="1110" y2="262" /><line x1="1135" y1="232" x2="1135" y2="262" /><line x1="1160" y1="232" x2="1160" y2="262" /><line x1="1185" y1="232" x2="1185" y2="262" /><line x1="1210" y1="232" x2="1210" y2="262" />
      <line x1="1300" y1="232" x2="1300" y2="262" /><line x1="1325" y1="232" x2="1325" y2="262" /><line x1="1350" y1="232" x2="1350" y2="262" />
    </g>
    <g fill="#2a3a5c"><rect x="1115" y="236" width="16" height="24" rx="3" /><rect x="1140" y="236" width="16" height="24" rx="3" /><rect x="1165" y="250" width="16" height="24" rx="3" /><rect x="1190" y="262" width="16" height="24" rx="3" /></g>
    <rect x="1400" y="222" width="600" height="172" fill="rgba(52,211,153,.05)" />
    <g fill="none" stroke="rgba(52,211,153,.4)" strokeWidth="4">
      <ellipse cx="1690" cy="285" rx="125" ry="42" strokeDasharray="10 8" />
      <path d="M1440 262 C1480 245 1530 250 1570 268" />
      <path d="M1690 300 A55 22 0 0 1 1800 300" /><path d="M1705 300 A40 15 0 0 1 1785 300" />
    </g>
    <g fill="#16223a" stroke="#24345a" strokeWidth="2">
      <rect x="960" y="5" width="70" height="95" rx="3" />
      <rect x="1130" y="25" width="230" height="75" rx="3" />
      <rect x="530" y="0" width="120" height="35" rx="3" />
      <rect x="700" y="0" width="90" height="30" rx="3" />
      <rect x="865" y="0" width="85" height="30" rx="3" />
      <rect x="1760" y="170" width="50" height="25" rx="2" />
      <rect x="1975" y="240" width="25" height="25" rx="2" />
      <rect x="390" y="455" width="60" height="30" rx="2" />
    </g>
    <g fill="rgba(190,80,70,.5)"><rect x="960" y="5" width="70" height="22" /><rect x="1130" y="25" width="230" height="10" /></g>
    <g><circle cx="1766" cy="460" r="37" fill="#10301f" /><circle cx="1720" cy="1155" r="30" fill="#0d2419" /><circle cx="1621" cy="458" r="28" fill="#10301f" /><circle cx="1370" cy="869" r="45" fill="#0b2016" /><circle cx="1750" cy="1187" r="38" fill="#10301f" /><circle cx="1703" cy="511" r="34" fill="#0b2016" /><circle cx="1409" cy="656" r="42" fill="#0d2419" /><circle cx="1399" cy="874" r="30" fill="#0d2419" /><circle cx="1697" cy="452" r="27" fill="#0d2419" /><circle cx="1663" cy="841" r="42" fill="#10301f" /><circle cx="1722" cy="776" r="32" fill="#0d2419" /><circle cx="1798" cy="603" r="37" fill="#0b2016" /><circle cx="1662" cy="685" r="35" fill="#0b2016" /><circle cx="1987" cy="498" r="34" fill="#10301f" /><circle cx="1432" cy="806" r="27" fill="#0b2016" /><circle cx="1382" cy="863" r="42" fill="#10301f" /><circle cx="1558" cy="691" r="36" fill="#10301f" /><circle cx="1511" cy="979" r="27" fill="#0b2016" /><circle cx="1800" cy="937" r="46" fill="#10301f" /><circle cx="1521" cy="720" r="39" fill="#0d2419" /><circle cx="1960" cy="695" r="38" fill="#10301f" /><circle cx="1369" cy="1038" r="29" fill="#0d2419" /><circle cx="1597" cy="1161" r="36" fill="#0d2419" /><circle cx="1631" cy="856" r="44" fill="#10301f" /><circle cx="1909" cy="631" r="34" fill="#10301f" /><circle cx="1787" cy="716" r="31" fill="#0d2419" /><circle cx="1486" cy="803" r="38" fill="#10301f" /><circle cx="1688" cy="906" r="32" fill="#0d2419" /><circle cx="1793" cy="828" r="38" fill="#0b2016" /><circle cx="1826" cy="779" r="43" fill="#0b2016" /><circle cx="1865" cy="726" r="34" fill="#0d2419" /><circle cx="1653" cy="732" r="30" fill="#0d2419" /><circle cx="1625" cy="491" r="38" fill="#0d2419" /><circle cx="1398" cy="702" r="27" fill="#0d2419" /><circle cx="1741" cy="523" r="31" fill="#10301f" /><circle cx="1734" cy="794" r="28" fill="#10301f" /><circle cx="1995" cy="787" r="36" fill="#0d2419" /><circle cx="1427" cy="1022" r="41" fill="#10301f" /><circle cx="1885" cy="534" r="26" fill="#0b2016" /><circle cx="1572" cy="973" r="44" fill="#0b2016" /><circle cx="1530" cy="934" r="28" fill="#10301f" /><circle cx="1677" cy="1154" r="33" fill="#0d2419" /><circle cx="1687" cy="1047" r="33" fill="#0d2419" /><circle cx="1741" cy="1054" r="41" fill="#0d2419" /><circle cx="1870" cy="1079" r="41" fill="#0d2419" /><circle cx="1464" cy="809" r="41" fill="#0d2419" /><circle cx="1859" cy="792" r="30" fill="#0b2016" /><circle cx="1971" cy="771" r="45" fill="#10301f" /><circle cx="1970" cy="703" r="30" fill="#0d2419" /><circle cx="1645" cy="680" r="36" fill="#0b2016" /><circle cx="1893" cy="798" r="39" fill="#0b2016" /><circle cx="1387" cy="948" r="44" fill="#0b2016" /><circle cx="1833" cy="797" r="30" fill="#0b2016" /><circle cx="1553" cy="1065" r="45" fill="#10301f" /><circle cx="1640" cy="1017" r="28" fill="#0d2419" /><circle cx="1431" cy="1151" r="42" fill="#0d2419" /><circle cx="1740" cy="895" r="35" fill="#10301f" /><circle cx="1434" cy="855" r="26" fill="#0b2016" /><circle cx="1765" cy="837" r="45" fill="#10301f" /><circle cx="1991" cy="562" r="43" fill="#0d2419" /><circle cx="1499" cy="643" r="31" fill="#0b2016" /><circle cx="1548" cy="852" r="43" fill="#0d2419" /><circle cx="1940" cy="694" r="35" fill="#0b2016" /><circle cx="1876" cy="829" r="43" fill="#0b2016" /><circle cx="1672" cy="1124" r="42" fill="#0b2016" /><circle cx="1445" cy="793" r="41" fill="#0b2016" /><circle cx="1371" cy="966" r="37" fill="#10301f" /><circle cx="1855" cy="488" r="37" fill="#0d2419" /><circle cx="1395" cy="775" r="27" fill="#0d2419" /><circle cx="1627" cy="908" r="36" fill="#0b2016" /><circle cx="1420" cy="320" r="22" fill="#10301f" /><circle cx="1470" cy="300" r="22" fill="#10301f" /><circle cx="1520" cy="330" r="22" fill="#10301f" /><circle cx="1600" cy="240" r="22" fill="#10301f" /><circle cx="1640" cy="330" r="22" fill="#10301f" /><circle cx="1690" cy="350" r="22" fill="#10301f" /><circle cx="1760" cy="330" r="22" fill="#10301f" /><circle cx="1840" cy="250" r="22" fill="#10301f" /><circle cx="1880" cy="310" r="22" fill="#10301f" /><circle cx="1930" cy="360" r="22" fill="#10301f" /><circle cx="1980" cy="300" r="22" fill="#10301f" /><circle cx="1500" cy="250" r="22" fill="#10301f" /><circle cx="600" cy="196" r="13" fill="#10301f" /><circle cx="648" cy="196" r="13" fill="#10301f" /><circle cx="696" cy="196" r="13" fill="#10301f" /><circle cx="744" cy="196" r="13" fill="#10301f" /><circle cx="792" cy="196" r="13" fill="#10301f" /><circle cx="840" cy="196" r="13" fill="#10301f" /><circle cx="888" cy="196" r="13" fill="#10301f" /><circle cx="936" cy="196" r="13" fill="#10301f" /><circle cx="984" cy="196" r="13" fill="#10301f" /><circle cx="1032" cy="196" r="13" fill="#10301f" /><circle cx="1080" cy="196" r="13" fill="#10301f" /><circle cx="1128" cy="196" r="13" fill="#10301f" /><circle cx="1176" cy="196" r="13" fill="#10301f" /><circle cx="1224" cy="196" r="13" fill="#10301f" /><circle cx="1272" cy="196" r="13" fill="#10301f" /><circle cx="1320" cy="196" r="13" fill="#10301f" /><circle cx="1368" cy="196" r="13" fill="#10301f" /><circle cx="1416" cy="196" r="13" fill="#10301f" /><circle cx="1464" cy="196" r="13" fill="#10301f" /><circle cx="1512" cy="196" r="13" fill="#10301f" /><circle cx="1560" cy="196" r="13" fill="#10301f" /><circle cx="1608" cy="196" r="13" fill="#10301f" /><circle cx="205" cy="198" r="12" fill="#10301f" /><circle cx="245" cy="198" r="12" fill="#10301f" /><circle cx="285" cy="198" r="12" fill="#10301f" /><circle cx="325" cy="198" r="12" fill="#10301f" /><circle cx="365" cy="198" r="12" fill="#10301f" /><circle cx="405" cy="198" r="12" fill="#10301f" /><circle cx="180" cy="705" r="20" fill="#0d2419" /><circle cx="230" cy="690" r="20" fill="#0d2419" /><circle cx="300" cy="705" r="20" fill="#0d2419" /><circle cx="330" cy="680" r="20" fill="#0d2419" /><circle cx="1040" cy="140" r="20" fill="#0d2419" /><circle cx="1180" cy="130" r="20" fill="#0d2419" /><circle cx="1250" cy="140" r="20" fill="#0d2419" /><circle cx="1330" cy="150" r="20" fill="#0d2419" /><circle cx="1400" cy="140" r="20" fill="#0d2419" /><circle cx="1480" cy="150" r="20" fill="#0d2419" /></g>
    <polygon points="770,450 1000,450 1000,560 770,560" fill="#101a2c" />
    <polygon points="820,490 985,490 985,550 820,550" fill="rgba(190,80,70,.28)" />
    <polygon points="790,930 980,930 990,1230 780,1230" fill="#0f1828" />
    <g fill="#0f3a2a" stroke="#2f7d5c" strokeWidth="3">
      <polygon points="610,612 880,608 880,930 470,930 470,880" />
      <polygon points="985,595 1175,595 1210,860 982,860" />
      <polygon points="982,866 1212,866 1275,1230 980,1230" />
    </g>
    <g fill="none" stroke="rgba(230,237,247,.35)" strokeWidth="2.5">
      <line x1="490" y1="765" x2="860" y2="765" /><ellipse cx="710" cy="765" rx="28" ry="16" /><rect x="680" y="640" width="120" height="38" /><rect x="590" y="885" width="150" height="45" />
      <line x1="995" y1="737" x2="1190" y2="737" /><ellipse cx="1090" cy="737" rx="22" ry="12" /><rect x="1045" y="598" width="90" height="28" /><rect x="1045" y="820" width="110" height="38" />
      <line x1="985" y1="1020" x2="1245" y2="1020" /><ellipse cx="1108" cy="1020" rx="28" ry="17" /><rect x="1050" y="868" width="110" height="38" /><rect x="1050" y="1160" width="125" height="60" />
    </g>
    <g fill="#0f3a2a" stroke="#2f6d55" strokeWidth="2">
      <polygon points="1060,395 1500,395 1515,487 1060,487" />
      <polygon points="1235,495 1555,495 1580,628 1248,628" />
    </g>
    <g fill="#5a2230" stroke="rgba(230,237,247,.35)" strokeWidth="2">
      <rect x="1100" y="418" width="75" height="54" />
      <rect x="1205" y="405" width="125" height="76" />
      <rect x="1365" y="405" width="132" height="76" />
    </g>
    <g fill="none" stroke="rgba(230,237,247,.35)" strokeWidth="2"><line x1="1100" y1="445" x2="1175" y2="445" /><line x1="1267" y1="405" x2="1267" y2="481" /><ellipse cx="1267" cy="443" rx="14" ry="9" /><line x1="1431" y1="405" x2="1431" y2="481" /><ellipse cx="1431" cy="443" rx="14" ry="9" /></g>
    <polygon points="1328,405 1360,405 1372,470 1340,470" fill="rgba(251,146,60,.55)" />
    <g fill="#0f4466" stroke="rgba(230,237,247,.4)" strokeWidth="2">
      <polygon points="1262,515 1378,515 1385,600 1265,600" />
      <polygon points="1405,515 1522,515 1532,600 1410,600" />
    </g>
    <g stroke="rgba(230,237,247,.45)" strokeWidth="2"><line x1="1320" y1="515" x2="1325" y2="600" /><line x1="1463" y1="515" x2="1471" y2="600" /></g>
    <g fill="#1c2842" stroke="#30416a" strokeWidth="2">
      <polygon points="515,560 1145,555 1145,608 515,612" />
      <polygon points="1025,478 1140,478 1140,555 1025,555" />
      <polygon points="850,610 980,610 965,900 855,900" />
    </g>
    <g stroke="#4a5f8c" strokeWidth="3"><line x1="520" y1="584" x2="1140" y2="580" /><line x1="915" y1="586" x2="910" y2="898" /><line x1="1082" y1="482" x2="1082" y2="582" /></g>
    <polygon points="782,450 848,450 848,480 782,480" fill="#1c2842" stroke="#30416a" strokeWidth="2" />
    <g fill="#101a2e" stroke="#2c3f68" strokeWidth="3">
      <polygon points="912,200 962,198 962,305 915,312" />
      <polygon points="550,322 942,322 945,455 800,480 790,515 780,545 685,550 670,480 575,455" />
      <path d="M645,246 L645,284 A133,38 0 0 0 910,284 L910,246 Z" />
    </g>
    <g stroke="#1c2a46" strokeWidth="2">
      <line x1="580" y1="360" x2="940" y2="360" /><line x1="582" y1="400" x2="942" y2="400" /><line x1="600" y1="440" x2="940" y2="440" />
      <line x1="672" y1="440" x2="782" y2="440" /><line x1="680" y1="500" x2="785" y2="500" />
    </g>
    <g fill="#1b2a47" stroke="#4a6aa0" strokeWidth="3">
      <polygon points="660,190 670,177 730,161 800,151 855,150 920,165 957,185 960,200 660,212" />
      <ellipse cx="777" cy="246" rx="133" ry="38" />
      <polygon points="550,315 567,302 685,289 790,286 937,300 942,322 550,330" />
      <polygon points="660,355 670,317 755,316 772,357 755,392 670,396" />
    </g>
    <g stroke="#2e4677" strokeWidth="2">
      <line x1="777" y1="208" x2="777" y2="284" /><line x1="644" y1="246" x2="910" y2="246" /><line x1="683" y1="219" x2="871" y2="273" /><line x1="871" y1="219" x2="683" y2="273" />
      <line x1="812" y1="160" x2="680" y2="205" /><line x1="812" y1="160" x2="950" y2="195" /><line x1="735" y1="300" x2="570" y2="318" /><line x1="735" y1="300" x2="930" y2="315" />
    </g>
    <g fill="#2a3f66" stroke="#5b7fbf" strokeWidth="2">
      <polygon points="762,240 770,232 784,232 792,240 792,252 784,260 770,260 762,252" />
      <polygon points="800,156 806,152 818,152 824,156 824,166 818,170 806,170 800,166" />
      <polygon points="722,295 728,291 742,291 748,295 748,305 742,309 728,309 722,305" />
    </g>
    <g fontFamily="IBM Plex Sans, sans-serif" fontWeight="600" style={{ paintOrder: "stroke" }} stroke="#050912" strokeWidth="7" strokeLinejoin="round">
      <text x="540" y="395" textAnchor="end" fill="#e6edf7" fontSize="28">A Kanadı</text>
      <text x="975" y="200" fill="#e6edf7" fontSize="28">B Kanadı</text>
      <text x="1250" y="372" textAnchor="middle" fill="#fed7aa" fontSize="26">Spor kompleksi</text>
      <text x="480" y="972" fill="#a7f3d0" fontSize="26">Halı sahalar</text>
      <text x="1240" y="300" textAnchor="middle" fill="#c9d4e8" fontSize="24">Otopark</text>
      <text x="1690" y="250" textAnchor="middle" fill="#a7f3d0" fontSize="24">Park</text>
      <text x="1245" y="130" textAnchor="middle" fill="#e6edf7" fontSize="26">Yurt</text>
      <text x="40" y="150" fill="#8b9bb8" fontSize="24">Sanayi bölgesi · kampüs dışı</text>
      <text x="1650" y="760" textAnchor="middle" fill="#6ee7b7" fontSize="24">Ağaçlık alan</text>
      <text x="1010" y="640" fill="#94a3b8" fontSize="20">Kapalı yol</text>
    </g>
  </>
);

// <sc-if gKus>
export const KUS_FOTO = (
  <>
    <line x1="598" y1="105" x2="15" y2="794" stroke="rgba(34,211,238,.35)" strokeWidth="4" strokeDasharray="6 14" />
    <g fill="rgba(52,211,153,.06)" stroke="rgba(52,211,153,.55)" strokeWidth="3" strokeDasharray="14 10">
      <polygon points="610,612 880,608 880,930 470,930 470,880" />
      <polygon points="985,595 1175,595 1275,1230 980,1230" />
    </g>
    <line x1="982" y1="860" x2="1215" y2="860" stroke="rgba(52,211,153,.45)" strokeWidth="3" strokeDasharray="14 10" />
    <g fill="rgba(244,114,94,.06)" stroke="rgba(251,146,60,.6)" strokeWidth="3" strokeDasharray="14 10">
      <polygon points="1030,388 1470,388 1470,485 1030,485" />
      <polygon points="1180,485 1535,485 1535,628 1180,628" />
    </g>
    <g fill="rgba(148,163,184,.06)" stroke="rgba(203,213,225,.4)" strokeWidth="3">
      <polygon points="515,560 1145,555 1145,608 515,612" />
      <polygon points="1025,478 1140,478 1140,555 1025,555" />
      <polygon points="850,610 980,610 965,900 855,900" />
    </g>
    <g fill="rgba(34,211,238,.07)" stroke="rgba(34,211,238,.7)" strokeWidth="3.5">
      <polygon points="660,190 670,177 730,161 800,151 855,150 920,165 957,185 962,305 915,312 915,215 660,215" />
      <polygon points="550,315 567,302 685,289 790,286 937,300 942,322 945,455 800,480 790,515 780,545 685,550 670,480 575,455" />
    </g>
    <ellipse cx="777" cy="246" rx="133" ry="38" fill="rgba(34,211,238,.08)" stroke="rgba(34,211,238,.8)" strokeWidth="3.5" />
    <g fontFamily="IBM Plex Sans, sans-serif" fontWeight="600" style={{ paintOrder: "stroke" }} stroke="#050912" strokeWidth="7" strokeLinejoin="round">
      <text x="540" y="395" textAnchor="end" fill="#e6edf7" fontSize="28">A Kanadı</text>
      <text x="975" y="200" fill="#e6edf7" fontSize="28">B Kanadı</text>
      <text x="777" y="196" textAnchor="middle" fill="#a5f3fc" fontSize="24">Rotunda</text>
      <text x="1250" y="372" textAnchor="middle" fill="#fed7aa" fontSize="26">Spor kompleksi</text>
      <text x="480" y="972" fill="#a7f3d0" fontSize="26">Halı sahalar</text>
      <text x="1240" y="300" textAnchor="middle" fill="#c9d4e8" fontSize="24">Otopark</text>
      <text x="1700" y="350" textAnchor="middle" fill="#a7f3d0" fontSize="24">Park</text>
      <text x="1245" y="130" textAnchor="middle" fill="#e6edf7" fontSize="26">Yurt</text>
      <text x="40" y="120" fill="#8b9bb8" fontSize="24">Sanayi bölgesi · kampüs dışı</text>
      <text x="1650" y="760" textAnchor="middle" fill="#6ee7b7" fontSize="24">Ağaçlık alan</text>
    </g>
  </>
);

// <sc-if gPerspKroki>
export const PERSP_KROKI = (
  <>
    <rect x="0" y="60" width="2000" height="1239" fill="#060a14" />
    <polygon points="0,135 780,255 2000,415 2000,1299 0,1299" fill="#0a111f" />
    <g fill="#0e1626" stroke="#18233b" strokeWidth="2">
      <polygon points="960,105 1250,95 2000,110 2000,290 1400,250 1150,225 960,165" />
      <rect x="590" y="60" width="130" height="80" rx="3" />
      <rect x="570" y="100" width="130" height="50" rx="3" />
      <rect x="820" y="105" width="120" height="45" rx="3" />
      <ellipse cx="520" cy="120" rx="40" ry="16" />
    </g>
    <g stroke="#131c30" strokeWidth="2"><line x1="1000" y1="140" x2="2000" y2="160" /><line x1="1080" y1="185" x2="2000" y2="215" /><line x1="1200" y1="215" x2="2000" y2="255" /></g>
    <g fill="rgba(190,80,70,.4)"><rect x="1520" y="262" width="80" height="33" /><rect x="1795" y="305" width="195" height="62" /></g>
    <polygon points="900,225 1400,250 1380,300 900,270" fill="#0f1829" />
    <line x1="0" y1="135" x2="2000" y2="415" stroke="rgba(34,211,238,.35)" strokeWidth="4" strokeDasharray="6 14" />
    <g stroke="#16213a" strokeLinecap="round" fill="none">
      <path d="M1000 700 C 900 760 760 900 600 1040" strokeWidth="30" />
      <line x1="275" y1="1299" x2="640" y2="1040" strokeWidth="40" />
      <line x1="600" y1="1040" x2="250" y2="830" strokeWidth="18" />
      <path d="M1000 700 C 1100 690 1180 700 1250 740" strokeWidth="22" />
    </g>
    <polygon points="900,1010 1180,830 1880,880 2000,900 2000,1299 1150,1299" fill="#0f1829" stroke="#1c2945" strokeWidth="2" />
    <line x1="1060" y1="925" x2="1830" y2="1255" stroke="rgba(16,48,31,.9)" strokeWidth="36" />
    <polygon points="1175,775 1875,815 1875,880 1180,835" fill="rgba(52,211,153,.07)" />
    <g fill="#2a3a5c"><rect x="1685" y="985" width="20" height="32" rx="4" /><rect x="1728" y="1010" width="20" height="32" rx="4" /><rect x="1866" y="1047" width="20" height="32" rx="4" /><rect x="1903" y="1060" width="20" height="32" rx="4" /><rect x="1941" y="1072" width="20" height="32" rx="4" /><rect x="1672" y="1104" width="20" height="32" rx="4" /><rect x="1735" y="1129" width="20" height="32" rx="4" /></g>
    <g><circle cx="68" cy="543" r="47" fill="#10301f" /><circle cx="68" cy="608" r="33" fill="#0b2016" /><circle cx="71" cy="555" r="33" fill="#10301f" /><circle cx="46" cy="440" r="45" fill="#0b2016" /><circle cx="95" cy="551" r="37" fill="#10301f" /><circle cx="98" cy="555" r="33" fill="#0d2419" /><circle cx="125" cy="434" r="31" fill="#0d2419" /><circle cx="90" cy="591" r="36" fill="#0b2016" /><circle cx="126" cy="534" r="42" fill="#10301f" /><circle cx="1" cy="439" r="42" fill="#10301f" /><circle cx="379" cy="1298" r="52" fill="#0b2016" /><circle cx="97" cy="1194" r="45" fill="#0d2419" /><circle cx="27" cy="1197" r="42" fill="#10301f" /><circle cx="147" cy="1282" r="52" fill="#0d2419" /><circle cx="81" cy="1268" r="35" fill="#10301f" /><circle cx="373" cy="1035" r="36" fill="#0b2016" /><circle cx="75" cy="1157" r="41" fill="#10301f" /><circle cx="126" cy="1284" r="50" fill="#0d2419" /><circle cx="51" cy="1171" r="34" fill="#10301f" /><circle cx="303" cy="938" r="46" fill="#10301f" /><circle cx="193" cy="1294" r="50" fill="#10301f" /><circle cx="245" cy="911" r="43" fill="#0d2419" /><circle cx="0" cy="1240" r="54" fill="#0b2016" /><circle cx="116" cy="1249" r="38" fill="#10301f" /><circle cx="378" cy="1125" r="46" fill="#0d2419" /><circle cx="376" cy="954" r="39" fill="#0b2016" /><circle cx="125" cy="990" r="36" fill="#0d2419" /><circle cx="79" cy="1140" r="34" fill="#10301f" /><circle cx="141" cy="1059" r="54" fill="#10301f" /><circle cx="316" cy="920" r="42" fill="#0b2016" /><circle cx="59" cy="1260" r="51" fill="#0d2419" /><circle cx="276" cy="930" r="47" fill="#0b2016" /><circle cx="415" cy="1293" r="43" fill="#0b2016" /><circle cx="394" cy="1157" r="32" fill="#0b2016" /><circle cx="553" cy="1186" r="41" fill="#10301f" /><circle cx="456" cy="1286" r="37" fill="#0b2016" /><circle cx="412" cy="1258" r="31" fill="#0d2419" /><circle cx="466" cy="1248" r="39" fill="#0d2419" /><circle cx="785" cy="970" r="16" fill="#10301f" /><circle cx="830" cy="935" r="16" fill="#10301f" /><circle cx="870" cy="905" r="16" fill="#10301f" /><circle cx="920" cy="870" r="16" fill="#10301f" /><circle cx="1010" cy="815" r="16" fill="#10301f" /><circle cx="700" cy="1030" r="16" fill="#10301f" /><circle cx="1205" cy="780" r="16" fill="#10301f" /><circle cx="1300" cy="790" r="16" fill="#10301f" /><circle cx="1380" cy="800" r="16" fill="#10301f" /><circle cx="1460" cy="810" r="16" fill="#10301f" /><circle cx="1560" cy="830" r="16" fill="#10301f" /><circle cx="1650" cy="850" r="16" fill="#10301f" /><circle cx="1760" cy="850" r="16" fill="#10301f" /><circle cx="1240" cy="970" r="16" fill="#10301f" /><circle cx="1320" cy="990" r="16" fill="#10301f" /><circle cx="1400" cy="1010" r="16" fill="#10301f" /><circle cx="1480" cy="1030" r="16" fill="#10301f" /><circle cx="1560" cy="1045" r="16" fill="#10301f" /><circle cx="1640" cy="1060" r="16" fill="#10301f" /><circle cx="205" cy="195" r="18" fill="#0d2419" /><circle cx="250" cy="200" r="18" fill="#0d2419" /><circle cx="320" cy="205" r="18" fill="#0d2419" /><circle cx="400" cy="210" r="18" fill="#0d2419" /><circle cx="470" cy="220" r="18" fill="#0d2419" /><circle cx="840" cy="280" r="18" fill="#0d2419" /><circle cx="900" cy="275" r="18" fill="#0d2419" /><circle cx="1450" cy="330" r="18" fill="#0d2419" /><circle cx="1560" cy="320" r="18" fill="#0d2419" /><circle cx="1640" cy="330" r="18" fill="#0d2419" /><circle cx="1700" cy="330" r="18" fill="#0d2419" /><circle cx="1820" cy="330" r="18" fill="#0d2419" /></g>
    <polygon points="620,500 890,470 980,500 1000,600 700,610" fill="#101a2c" />
    <polygon points="640,555 860,505 885,525 700,578" fill="rgba(190,80,70,.3)" />
    <g fill="#0f3a2a" stroke="#2f7d5c" strokeWidth="3">
      <polygon points="40,425 165,385 500,522 400,562 90,467" />
      <polygon points="367,397 497,354 705,406 590,465" />
    </g>
    <g fill="none" stroke="rgba(230,237,247,.35)" strokeWidth="2.5">
      <ellipse cx="160" cy="445" rx="22" ry="9" /><ellipse cx="350" cy="510" rx="22" ry="9" /><ellipse cx="537" cy="414" rx="20" ry="8" />
      <line x1="250" y1="440" x2="215" y2="500" /><line x1="590" y1="380" x2="485" y2="445" />
    </g>
    <g fill="#0f3a2a" stroke="#2f6d55" strokeWidth="2">
      <polygon points="85,715 295,610 590,660 460,790 315,850" />
      <polygon points="322,868 600,700 705,615 970,670 905,775 600,1020" />
    </g>
    <g fill="#0f4466" stroke="rgba(230,237,247,.4)" strokeWidth="2">
      <polygon points="160,733 255,695 410,760 330,815" />
      <polygon points="310,662 390,625 548,677 470,722" />
    </g>
    <g stroke="rgba(230,237,247,.45)" strokeWidth="2"><line x1="207" y1="714" x2="370" y2="788" /><line x1="350" y1="644" x2="509" y2="700" /></g>
    <g fill="#5a2230" stroke="rgba(230,237,247,.35)" strokeWidth="2">
      <polygon points="365,890 490,802 720,898 610,995" />
      <polygon points="560,760 660,695 880,775 790,850" />
      <polygon points="725,670 790,642 905,690 850,720" />
    </g>
    <g fill="none" stroke="rgba(230,237,247,.35)" strokeWidth="2"><line x1="428" y1="846" x2="665" y2="947" /><ellipse cx="540" cy="898" rx="18" ry="10" /><line x1="610" y1="728" x2="835" y2="813" /><ellipse cx="720" cy="772" rx="16" ry="9" /></g>
    <polygon points="530,790 560,775 740,850 715,870" fill="rgba(251,146,60,.6)" />
    <g fill="#1c2842" stroke="#30416a" strokeWidth="2">
      <polygon points="790,380 805,405 605,500 588,478" />
      <polygon points="283,388 602,474 594,502 277,416" />
      <polygon points="425,547 505,525 737,578 665,622" />
    </g>
    <g stroke="#4a5f8c" strokeWidth="3"><line x1="797" y1="392" x2="597" y2="489" /><line x1="280" y1="402" x2="598" y2="488" /><line x1="465" y1="536" x2="701" y2="600" /></g>
    <polygon points="970,500 1110,500 1135,600 1000,600" fill="rgba(190,80,70,.35)" stroke="#5a2a30" strokeWidth="2" />
    <g fill="#101a2e" stroke="#2c3f68" strokeWidth="3">
      <polygon points="780,320 860,300 1030,300 1160,315 1162,350 1115,380 1110,500 1010,500 1000,595 910,595 895,545 865,480 795,465 785,400" />
      <polygon points="1600,405 1745,410 1800,460 2000,500 2000,750 1940,770 1750,720 1650,730 1560,770 1465,740 1470,580 1490,550 1590,490 1590,430" />
      <path d="M1112,405 L1112,595 A180,48 0 0 0 1472,595 L1472,405 Z" />
      <polygon points="1135,600 1260,600 1480,600 1480,700 1440,730 1260,720 1135,640" />
    </g>
    <g fill="none" stroke="#1f3050" strokeWidth="2">
      <line x1="790" y1="390" x2="890" y2="395" /><line x1="795" y1="430" x2="890" y2="440" /><line x1="905" y1="450" x2="1000" y2="450" /><line x1="905" y1="500" x2="1000" y2="500" /><line x1="905" y1="550" x2="998" y2="550" /><line x1="1012" y1="400" x2="1110" y2="400" /><line x1="1012" y1="450" x2="1110" y2="450" />
      <path d="M1112,455 A180,48 0 0 0 1472,455" /><path d="M1112,505 A180,48 0 0 0 1472,505" /><path d="M1112,550 A180,48 0 0 0 1472,550" />
      <line x1="1470" y1="620" x2="2000" y2="590" /><line x1="1468" y1="670" x2="2000" y2="645" /><line x1="1466" y1="715" x2="2000" y2="700" />
      <line x1="1140" y1="660" x2="1480" y2="650" />
    </g>
    <g fill="#1b2a47" stroke="#4a6aa0" strokeWidth="3">
      <polygon points="780,320 860,300 1030,300 1160,315 1160,345 1030,352 1012,345 895,345 785,348" />
      <polygon points="893,348 915,335 990,335 1012,348 995,412 905,412" />
      <polygon points="1490,548 1590,490 1600,410 1745,410 1800,460 2000,500 2000,560 1800,525 1700,510 1600,530 1500,570" />
      <ellipse cx="1292" cy="405" rx="180" ry="52" />
    </g>
    <g stroke="#2e4677" strokeWidth="2">
      <line x1="1292" y1="353" x2="1292" y2="457" /><line x1="1112" y1="405" x2="1472" y2="405" /><line x1="1165" y1="368" x2="1419" y2="442" /><line x1="1419" y1="368" x2="1165" y2="442" />
      <line x1="945" y1="312" x2="790" y2="330" /><line x1="945" y1="312" x2="1150" y2="330" /><line x1="1690" y1="440" x2="1600" y2="420" /><line x1="1690" y1="440" x2="1950" y2="510" />
    </g>
    <g fill="#2a3f66" stroke="#5b7fbf" strokeWidth="2">
      <polygon points="1272,398 1280,390 1304,390 1312,398 1312,412 1304,420 1280,420 1272,412" />
      <polygon points="930,308 938,302 954,302 962,308 962,318 954,324 938,324 930,318" />
      <polygon points="1672,433 1680,426 1700,426 1708,433 1708,445 1700,452 1680,452 1672,445" />
    </g>
    <g fontFamily="IBM Plex Sans, sans-serif" fontWeight="600" style={{ paintOrder: "stroke" }} stroke="#050912" strokeWidth="7" strokeLinejoin="round">
      <text x="900" y="285" textAnchor="middle" fill="#e6edf7" fontSize="28">A Kanadı</text>
      <text x="1760" y="390" textAnchor="middle" fill="#e6edf7" fontSize="28">B Kanadı</text>
      <text x="1310" y="768" textAnchor="middle" fill="#c9d4e8" fontSize="24">Ana giriş</text>
      <text x="640" y="1068" textAnchor="middle" fill="#fed7aa" fontSize="26">Spor kompleksi</text>
      <text x="250" y="365" textAnchor="middle" fill="#a7f3d0" fontSize="26">Halı sahalar</text>
      <text x="660" y="660" textAnchor="middle" fill="#c9d4e8" fontSize="22">Kapalı yol</text>
      <text x="1380" y="1010" textAnchor="middle" fill="#c9d4e8" fontSize="26">Otopark</text>
      <text x="1100" y="130" textAnchor="middle" fill="#8b9bb8" fontSize="24">Sanayi bölgesi · kampüs dışı</text>
      <text x="1975" y="950" textAnchor="end" fill="#e6edf7" fontSize="22">Yurt → kadraj dışı</text>
    </g>
  </>
);

// <sc-if gPersp>
export const PERSP_FOTO = (
  <>
    <g fill="rgba(52,211,153,.06)" stroke="rgba(52,211,153,.55)" strokeWidth="3" strokeDasharray="14 10">
      <polygon points="40,425 165,385 500,522 400,562 90,467" />
      <polygon points="367,397 497,354 705,406 590,465" />
    </g>
    <g fill="rgba(244,114,94,.06)" stroke="rgba(251,146,60,.6)" strokeWidth="3" strokeDasharray="14 10">
      <polygon points="85,715 295,610 590,660 460,790 315,850" />
      <polygon points="322,868 600,700 705,615 970,670 905,775 600,1020" />
    </g>
    <g stroke="rgba(203,213,225,.32)" strokeWidth="26" strokeLinecap="round">
      <line x1="795" y1="395" x2="598" y2="488" />
      <line x1="280" y1="402" x2="598" y2="488" />
    </g>
    <polygon points="425,547 505,525 737,578 665,622" fill="rgba(148,163,184,.08)" stroke="rgba(203,213,225,.45)" strokeWidth="3" />
    <g fill="rgba(34,211,238,.07)" stroke="rgba(34,211,238,.7)" strokeWidth="3.5">
      <polygon points="780,320 860,300 1030,300 1160,315 1162,350 1115,380 1110,500 1010,500 1000,595 910,595 895,545 865,480 795,465 785,400" />
      <polygon points="1600,405 1745,410 1800,460 2000,500 2000,750 1940,770 1750,720 1650,730 1560,770 1465,740 1470,580 1490,550 1590,490 1590,430" />
      <path d="M1112,405 L1112,595 A180,48 0 0 0 1472,595 L1472,405" />
    </g>
    <ellipse cx="1292" cy="405" rx="180" ry="52" fill="rgba(34,211,238,.1)" stroke="rgba(34,211,238,.85)" strokeWidth="3.5" />
    <polygon points="1135,600 1260,600 1480,600 1480,700 1440,730 1260,720 1135,640" fill="rgba(203,213,225,.06)" stroke="rgba(203,213,225,.45)" strokeWidth="3" strokeDasharray="10 8" />
    <g fontFamily="IBM Plex Sans, sans-serif" fontWeight="600" style={{ paintOrder: "stroke" }} stroke="#050912" strokeWidth="7" strokeLinejoin="round">
      <text x="900" y="285" textAnchor="middle" fill="#e6edf7" fontSize="28">A Kanadı</text>
      <text x="1292" y="338" textAnchor="middle" fill="#a5f3fc" fontSize="26">Rotunda</text>
      <text x="1760" y="390" textAnchor="middle" fill="#e6edf7" fontSize="28">B Kanadı</text>
      <text x="1310" y="768" textAnchor="middle" fill="#c9d4e8" fontSize="24">Ana giriş</text>
      <text x="640" y="1068" textAnchor="middle" fill="#fed7aa" fontSize="26">Spor kompleksi</text>
      <text x="250" y="365" textAnchor="middle" fill="#a7f3d0" fontSize="26">Halı sahalar</text>
      <text x="660" y="660" textAnchor="middle" fill="#c9d4e8" fontSize="22">Kapalı yol</text>
      <text x="1380" y="1010" textAnchor="middle" fill="#c9d4e8" fontSize="26">Otopark</text>
      <text x="1100" y="130" textAnchor="middle" fill="#8b9bb8" fontSize="24">Sanayi bölgesi · kampüs dışı</text>
      <text x="1975" y="950" textAnchor="end" fill="#e6edf7" fontSize="22">Yurt → kadraj dışı</text>
    </g>
  </>
);
