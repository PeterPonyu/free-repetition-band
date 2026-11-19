export function StratumPlate() {
  return (
    <figure
      className="stratum-plate epoch-band-plate"
      id="band"
      aria-labelledby="stratum-caption"
    >
      <svg
        className="core"
        viewBox="0 0 220 640"
        role="img"
        aria-label="Vertical epoch core: overburden, free-repetition band, and unique-data floor."
      >
        <defs>
          <linearGradient id="decay" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#C4A35A" />
            <stop offset="55%" stopColor="#A87848" />
            <stop offset="100%" stopColor="#8B6B3D" />
          </linearGradient>
          <pattern
            id="grain"
            width="4"
            height="4"
            patternUnits="userSpaceOnUse"
          >
            <rect width="4" height="4" fill="#5F7A52" fillOpacity="0.12" />
            <rect width="1" height="4" fill="#3E5C45" fillOpacity="0.18" />
          </pattern>
        </defs>
        <rect
          x="48"
          y="24"
          width="72"
          height="592"
          rx="2"
          fill="#D9CBA8"
          stroke="#8B6B3D"
          strokeWidth="1.25"
        />
        <rect
          className="stratum-fill"
          x="48"
          y="24"
          width="72"
          height="455.4"
          fill="url(#decay)"
        />
        <rect
          className="stratum-fill"
          x="48"
          y="479"
          width="72"
          height="91.5"
          fill="#5F7A52"
        />
        <rect x="48" y="479" width="72" height="91.5" fill="url(#grain)" />
        <text
          x="84"
          y="534"
          textAnchor="middle"
          fontFamily="Fraunces, serif"
          fontStyle="italic"
          fontSize="13"
          fill="#EDE4CF"
        >
          band
        </text>
        <rect x="48" y="570.5" width="72" height="45.5" fill="#EDE4CF" />
        <rect
          x="48"
          y="24"
          width="72"
          height="592"
          fill="none"
          stroke="#2C2416"
          strokeWidth="1.4"
        />
        <g stroke="#2C2416" strokeWidth="0.75" opacity="0.55">
          <line x1="48" y1="479" x2="120" y2="479" />
          <line x1="48" y1="570.5" x2="120" y2="570.5" />
        </g>
        <g
          fontFamily="Atkinson Hyperlegible, sans-serif"
          fill="#2C2416"
          fontSize="11"
        >
          <text x="128" y="220" fill="#8B6B3D">
            overburden
          </text>
          <text x="128" y="532" fontWeight="700" fill="#3E5C45">
            band
          </text>
          <text x="128" y="600" fill="#8B6B3D">
            floor
          </text>
        </g>
      </svg>
      <figcaption id="stratum-caption">
        Vertical epoch core. Sage bed is the free-repetition band. Ochre
        overburden above; unique-data floor below.
      </figcaption>
    </figure>
  );
}
