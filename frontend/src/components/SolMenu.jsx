// Sol dikey menü: bölümlere kaydırır (ayrı sayfa yok). Admin için en altta
// "Kullanıcılar" (kullanıcı yönetimi penceresi); operatöre gösterilmez.
const OGELER = [
  {
    ad: "Panel",
    hedef: null,
    ikon: (
      <>
        <rect x="3" y="3" width="7" height="9" rx="1" />
        <rect x="14" y="3" width="7" height="5" rx="1" />
        <rect x="14" y="12" width="7" height="9" rx="1" />
        <rect x="3" y="16" width="7" height="5" rx="1" />
      </>
    ),
  },
  {
    ad: "Harita",
    hedef: "harita",
    ikon: (
      <>
        <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
        <line x1="8" y1="2" x2="8" y2="18" />
        <line x1="16" y1="6" x2="16" y2="22" />
      </>
    ),
  },
  {
    ad: "Olaylar",
    hedef: "olaylar",
    ikon: (
      <>
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </>
    ),
  },
  {
    ad: "Analitik",
    hedef: "analitik",
    ikon: (
      <>
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </>
    ),
  },
];

const git = (hedef) => {
  if (!hedef) {
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }
  document.getElementById(hedef)?.scrollIntoView({ behavior: "smooth", block: "start" });
};

function Ikon({ children }) {
  return (
    <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

export default function SolMenu({ admin, onKullanicilar }) {
  return (
    <nav className="sol-menu" aria-label="Ana menü">
      <div className="logo">
        <svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="#04202a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      </div>
      {OGELER.map((o, i) => (
        <button
          key={o.ad}
          type="button"
          className={i === 0 ? "menu-btn aktif" : "menu-btn"}
          aria-label={o.ad}
          title={o.ad}
          aria-current={i === 0 ? "page" : undefined}
          onClick={() => git(o.hedef)}
        >
          <Ikon>{o.ikon}</Ikon>
        </button>
      ))}
      {admin && (
        <button type="button" className="menu-btn" aria-label="Kullanıcılar"
          title="Kullanıcılar" onClick={onKullanicilar}>
          <Ikon>
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </Ikon>
        </button>
      )}
    </nav>
  );
}
