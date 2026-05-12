import './TopicDiagram.css'

/* ── Colour palette (matches dark theme) ───────────────── */
const V  = '#7B2FFF'   // violet  accent-1
const C  = '#00E5FF'   // cyan    accent-2
const P  = '#FF2D87'   // pink    accent-3
const O  = '#FF9500'   // orange
const G  = '#00D68F'   // green
const W  = 'rgba(240,244,255,0.85)'   // text
const DW = 'rgba(240,244,255,0.5)'    // dim text
const font = 'Inter, system-ui, sans-serif'

/* ══════════════════════════════════════════════════════════
   1. Human Digestive System
   ══════════════════════════════════════════════════════════ */
function DigestiveSystemDiagram() {
  const organs = [
    { y: 48,  label: 'Mouth',           color: P,  detail: 'chews + amylase'    },
    { y: 120, label: 'Esophagus',       color: V,  detail: 'peristalsis'         },
    { y: 192, label: 'Stomach',         color: O,  detail: 'HCl + pepsin'        },
    { y: 280, label: 'Small Intestine', color: C,  detail: 'villi → nutrients'   },
    { y: 368, label: 'Large Intestine', color: G,  detail: 'water absorption'    },
    { y: 436, label: 'Rectum / Anus',   color: V,  detail: 'waste expelled'      },
  ]
  const cx = 160

  return (
    <svg viewBox="0 0 380 490" xmlns="http://www.w3.org/2000/svg" className="diagram-svg">
      <defs>
        <marker id="arr-d" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M1 1 L7 4 L1 7 Z" fill={DW}/>
        </marker>
      </defs>

      {/* Central tract line */}
      <line x1={cx} y1="60" x2={cx} y2="430"
            stroke="rgba(255,255,255,0.12)" strokeWidth="2" strokeDasharray="6 4"/>

      {/* Liver branch */}
      <line x1={cx - 28} y1="208" x2="60" y2="208"
            stroke={O} strokeWidth="1.5" markerEnd="url(#arr-d)" opacity="0.7"/>
      <ellipse cx="38" cy="208" rx="22" ry="14"
               fill={O} opacity="0.25" stroke={O} strokeWidth="1.5"/>
      <text x="38" y="212" fill={W} fontSize="10" textAnchor="middle" fontFamily={font}>Liver</text>

      {/* Pancreas branch */}
      <line x1={cx + 28} y1="208" x2="316" y2="208"
            stroke={P} strokeWidth="1.5" markerEnd="url(#arr-d)" opacity="0.7"/>
      <ellipse cx="338" cy="208" rx="26" ry="14"
               fill={P} opacity="0.2" stroke={P} strokeWidth="1.5"/>
      <text x="338" y="212" fill={W} fontSize="10" textAnchor="middle" fontFamily={font}>Pancreas</text>

      {/* Organ nodes */}
      {organs.map(({ y, label, color, detail }, i) => (
        <g key={i}>
          {/* Downward arrow between nodes */}
          {i < organs.length - 1 && (
            <line x1={cx} y1={y + 24} x2={cx} y2={organs[i+1].y - 24}
                  stroke={DW} strokeWidth="1.5" markerEnd="url(#arr-d)" opacity="0.6"/>
          )}
          {/* Circle node */}
          <circle cx={cx} cy={y} r="22" fill={color} opacity="0.22" stroke={color} strokeWidth="2"/>
          <circle cx={cx} cy={y} r="8"  fill={color} opacity="0.9"/>
          {/* Label right */}
          <text x={cx + 32} y={y - 4} fill={W} fontSize="12" fontWeight="600" fontFamily={font}>{label}</text>
          <text x={cx + 32} y={y + 11} fill={DW} fontSize="10" fontFamily={font}>{detail}</text>
        </g>
      ))}

      {/* Title */}
      <text x="190" y="480" fill={DW} fontSize="10" textAnchor="middle" fontFamily={font}>
        Human Digestive System — 8–9 m alimentary canal
      </text>
    </svg>
  )
}

/* ══════════════════════════════════════════════════════════
   2. Photosynthesis
   ══════════════════════════════════════════════════════════ */
function PhotosynthesisDiagram() {
  return (
    <svg viewBox="0 0 380 320" xmlns="http://www.w3.org/2000/svg" className="diagram-svg">
      <defs>
        <marker id="arr-p" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M1 1 L7 4 L1 7 Z" fill={C}/>
        </marker>
        <marker id="arr-p2" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M1 1 L7 4 L1 7 Z" fill={G}/>
        </marker>
        <radialGradient id="sunGrad" cx="50%" cy="50%">
          <stop offset="0%"   stopColor="#FFE066" stopOpacity="1"/>
          <stop offset="100%" stopColor="#FF9500" stopOpacity="0.4"/>
        </radialGradient>
        <radialGradient id="leafGrad" cx="40%" cy="40%">
          <stop offset="0%"   stopColor="#00D68F" stopOpacity="0.5"/>
          <stop offset="100%" stopColor="#00A060" stopOpacity="0.3"/>
        </radialGradient>
      </defs>

      {/* Sun */}
      {[0,45,90,135,180,225,270,315].map((angle, i) => {
        const r = 28, len = 14
        const rad = angle * Math.PI / 180
        return (
          <line key={i}
            x1={66 + r * Math.cos(rad)} y1={60 + r * Math.sin(rad)}
            x2={66 + (r + len) * Math.cos(rad)} y2={60 + (r + len) * Math.sin(rad)}
            stroke="#FFE066" strokeWidth="2" opacity="0.7"/>
        )
      })}
      <circle cx="66" cy="60" r="24" fill="url(#sunGrad)"/>
      <text x="66" y="64" fill="#0B0F19" fontSize="10" textAnchor="middle" fontWeight="700" fontFamily={font}>SUN</text>

      {/* Leaf shape */}
      <path d="M 190 60 Q 280 80 290 160 Q 280 240 190 260 Q 100 240 110 160 Q 100 80 190 60 Z"
            fill="url(#leafGrad)" stroke={G} strokeWidth="1.5"/>
      {/* Midrib */}
      <line x1="190" y1="72" x2="190" y2="248" stroke={G} strokeWidth="1.5" opacity="0.5"/>
      {/* Veins */}
      {[-30,-15,0,15,30].map((a, i) => {
        const rad = a * Math.PI / 180
        return <line key={i} x1="190" y1={110 + i*30}
                              x2={190 + 60*Math.cos(rad)} y2={110 + i*30 + 30*Math.sin(rad)}
                              stroke={G} strokeWidth="1" opacity="0.35"/>
      })}

      {/* Chloroplast label */}
      <text x="190" y="155" fill={W} fontSize="11" textAnchor="middle" fontWeight="600" fontFamily={font}>Chloroplast</text>
      <text x="190" y="170" fill={DW} fontSize="9.5" textAnchor="middle" fontFamily={font}>(light reactions</text>
      <text x="190" y="182" fill={DW} fontSize="9.5" textAnchor="middle" fontFamily={font}>+ Calvin cycle)</text>

      {/* Sunlight arrow */}
      <line x1="90" y1="90" x2="140" y2="115" stroke="#FFE066" strokeWidth="2" markerEnd="url(#arr-p)" opacity="0.8"/>
      <text x="82" y="105" fill="#FFE066" fontSize="10" fontFamily={font}>Light</text>

      {/* CO₂ arrow in */}
      <line x1="60" y1="160" x2="108" y2="160" stroke={C} strokeWidth="2" markerEnd="url(#arr-p)"/>
      <text x="8" y="155" fill={C} fontSize="11" fontFamily={font} fontWeight="600">CO₂</text>
      <text x="8" y="168" fill={DW} fontSize="9" fontFamily={font}>(air)</text>

      {/* H₂O arrow in */}
      <line x1="130" y1="280" x2="165" y2="255" stroke={C} strokeWidth="2" markerEnd="url(#arr-p)"/>
      <text x="85" y="292" fill={C} fontSize="11" fontFamily={font} fontWeight="600">H₂O</text>
      <text x="85" y="305" fill={DW} fontSize="9" fontFamily={font}>(roots/soil)</text>

      {/* O₂ arrow out */}
      <line x1="272" y1="160" x2="320" y2="140" stroke={G} strokeWidth="2" markerEnd="url(#arr-p2)"/>
      <text x="322" y="138" fill={G} fontSize="11" fontFamily={font} fontWeight="600">O₂</text>
      <text x="322" y="150" fill={DW} fontSize="9" fontFamily={font}>(released)</text>

      {/* Glucose arrow out */}
      <line x1="248" y1="240" x2="300" y2="270" stroke={G} strokeWidth="2" markerEnd="url(#arr-p2)"/>
      <text x="300" y="270" fill={G} fontSize="11" fontFamily={font} fontWeight="600">Glucose</text>
      <text x="300" y="283" fill={DW} fontSize="9" fontFamily={font}>(stored)</text>

      <text x="190" y="314" fill={DW} fontSize="9.5" textAnchor="middle" fontFamily={font}>
        6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂
      </text>
    </svg>
  )
}

/* ══════════════════════════════════════════════════════════
   3. Human Eye
   ══════════════════════════════════════════════════════════ */
function HumanEyeDiagram() {
  const labelLine = (x1,y1,x2,y2,label,sub,anchor='start') => (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(255,255,255,0.25)" strokeWidth="1"/>
      <circle cx={x1} cy={y1} r="2" fill={C}/>
      <text x={x2 + (anchor==='end'?-4:4)} y={y2-4}  fill={W}  fontSize="11" fontWeight="600"
            textAnchor={anchor} fontFamily={font}>{label}</text>
      {sub && <text x={x2 + (anchor==='end'?-4:4)} y={y2+9} fill={DW} fontSize="9"
                    textAnchor={anchor} fontFamily={font}>{sub}</text>}
    </g>
  )
  return (
    <svg viewBox="0 0 400 310" xmlns="http://www.w3.org/2000/svg" className="diagram-svg">
      {/* Sclera (white outer) */}
      <ellipse cx="200" cy="155" rx="110" ry="80" fill="#1a2035" stroke="rgba(255,255,255,0.2)" strokeWidth="2"/>

      {/* Retina inner surface */}
      <ellipse cx="200" cy="155" rx="100" ry="70" fill="rgba(0,229,255,0.04)" stroke={C} strokeWidth="1" opacity="0.6"/>

      {/* Vitreous humour */}
      <ellipse cx="200" cy="155" rx="90" ry="62" fill="rgba(123,47,255,0.06)"/>

      {/* Lens */}
      <ellipse cx="164" cy="155" rx="18" ry="28" fill="rgba(0,229,255,0.25)" stroke={C} strokeWidth="1.5"/>

      {/* Iris */}
      <ellipse cx="136" cy="155" rx="22" ry="34"
               fill={V} opacity="0.55" stroke={V} strokeWidth="1.5"/>

      {/* Pupil */}
      <ellipse cx="136" cy="155" rx="10" ry="16" fill="#050810"/>

      {/* Cornea bulge (left cap) */}
      <path d="M 93 121 Q 72 155 93 189" fill="none" stroke={C} strokeWidth="2.5"/>

      {/* Optic nerve (right) */}
      <rect x="296" y="148" width="22" height="14" rx="4" fill={P} opacity="0.6"/>
      <line x1="300" y1="155" x2="336" y2="155" stroke={P} strokeWidth="3" opacity="0.7"/>

      {/* Macula / Fovea dot */}
      <circle cx="264" cy="155" r="6" fill={O} opacity="0.75"/>

      {/* Light ray */}
      <line x1="30" y1="130" x2="92" y2="145" stroke="#FFE066" strokeWidth="1.5"
            strokeDasharray="4 3" opacity="0.7"/>
      <line x1="30" y1="180" x2="92" y2="165" stroke="#FFE066" strokeWidth="1.5"
            strokeDasharray="4 3" opacity="0.7"/>
      <text x="18" y="158" fill="#FFE066" fontSize="10" fontFamily={font}>Light</text>

      {/* Labels */}
      {labelLine(80,  138, 28,  80,  'Cornea',       'clear front',  'end')}
      {labelLine(136, 121, 110, 60,  'Iris',          'controls pupil size', 'end')}
      {labelLine(136, 139, 178, 52,  'Pupil',         'light entry',  'start')}
      {labelLine(164, 128, 218, 44,  'Lens',          'focuses light', 'start')}
      {labelLine(264, 149, 312, 58,  'Fovea',         'sharpest vision','start')}
      {labelLine(280, 155, 340, 100, 'Retina',        'photoreceptors','start')}
      {labelLine(308, 155, 356, 195, 'Optic Nerve',   'signal to brain','start')}
      {labelLine(200, 220, 140, 275, 'Vitreous',      'gel-filled cavity','end')}
      {labelLine(100, 180, 50,  250, 'Sclera',        'white outer layer','end')}

      <text x="200" y="302" fill={DW} fontSize="9.5" textAnchor="middle" fontFamily={font}>
        Human Eye — cross-section (schematic)
      </text>
    </svg>
  )
}

/* ══════════════════════════════════════════════════════════
   4. Water Cycle
   ══════════════════════════════════════════════════════════ */
function WaterCycleDiagram() {
  return (
    <svg viewBox="0 0 400 310" xmlns="http://www.w3.org/2000/svg" className="diagram-svg">
      <defs>
        <marker id="arr-w" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M1 1 L7 4 L1 7 Z" fill={C}/>
        </marker>
        <radialGradient id="sunW" cx="50%" cy="50%">
          <stop offset="0%" stopColor="#FFE066" stopOpacity="0.9"/>
          <stop offset="100%" stopColor="#FF9500" stopOpacity="0.3"/>
        </radialGradient>
      </defs>

      {/* Ocean / Lake at bottom */}
      <path d="M 0 245 Q 100 235 200 245 Q 300 255 400 245 L 400 310 L 0 310 Z"
            fill="rgba(0,229,255,0.18)" stroke={C} strokeWidth="1" opacity="0.8"/>
      <text x="195" y="278" fill={C} fontSize="12" textAnchor="middle"
            fontWeight="600" fontFamily={font}>Ocean / Lake</text>

      {/* Mountain */}
      <path d="M 18 244 L 85 130 L 152 244 Z"
            fill="rgba(123,47,255,0.2)" stroke={V} strokeWidth="1.5"/>
      {/* Snow cap */}
      <path d="M 68 147 L 85 130 L 102 147 Q 85 143 68 147 Z"
            fill="white" opacity="0.55"/>
      <text x="85" y="260" fill={DW} fontSize="10" textAnchor="middle" fontFamily={font}>Mountains</text>

      {/* Cloud */}
      <ellipse cx="245" cy="72" rx="48" ry="28" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5"/>
      <ellipse cx="220" cy="80" rx="32" ry="22" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5"/>
      <ellipse cx="270" cy="82" rx="28" ry="20" fill="rgba(255,255,255,0.1)"  stroke="rgba(255,255,255,0.25)" strokeWidth="1.5"/>
      <text x="245" y="76" fill={W} fontSize="11" textAnchor="middle"
            fontWeight="600" fontFamily={font}>Cloud</text>

      {/* Sun */}
      {[0,60,120,180,240,300].map((a,i)=>{
        const r=22, len=10, rad=a*Math.PI/180
        return <line key={i} x1={355+r*Math.cos(rad)} y1={55+r*Math.sin(rad)}
                              x2={355+(r+len)*Math.cos(rad)} y2={55+(r+len)*Math.sin(rad)}
                              stroke="#FFE066" strokeWidth="1.8" opacity="0.7"/>
      })}
      <circle cx="355" cy="55" r="18" fill="url(#sunW)"/>
      <text x="355" y="59" fill="#0B0F19" fontSize="9" textAnchor="middle"
            fontWeight="700" fontFamily={font}>SUN</text>

      {/* EVAPORATION arrow — ocean → cloud */}
      <path d="M 195 238 Q 175 160 210 98" fill="none" stroke={C} strokeWidth="2"
            strokeDasharray="6 3" markerEnd="url(#arr-w)"/>
      <text x="155" y="172" fill={C} fontSize="10" fontFamily={font}>Evaporation</text>

      {/* CONDENSATION label near cloud */}
      <text x="302" y="68" fill={DW} fontSize="10" fontFamily={font}>Condensation</text>

      {/* PRECIPITATION — rain drops from cloud */}
      {[220,240,260,280].map((x,i)=>(
        <line key={i} x1={x} y1={104+i*3} x2={x-8} y2={135+i*3}
              stroke={C} strokeWidth="1.5" opacity="0.7"/>
      ))}
      <text x="234" y="148" fill={C} fontSize="10" textAnchor="middle" fontFamily={font}>Precipitation</text>

      {/* SURFACE RUNOFF — mountain → ocean */}
      <path d="M 110 228 Q 155 255 185 248" fill="none" stroke={G} strokeWidth="2"
            markerEnd="url(#arr-w)"/>
      <text x="128" y="222" fill={G} fontSize="10" fontFamily={font}>Runoff</text>

      {/* TRANSPIRATION — from mountain upward */}
      <path d="M 85 130 Q 120 90 185 82" fill="none" stroke={G} strokeWidth="1.5"
            strokeDasharray="4 3" markerEnd="url(#arr-w)" opacity="0.7"/>
      <text x="108" y="95" fill={G} fontSize="9" fontFamily={font}>Transpiration</text>

      {/* INFILTRATION label */}
      <text x="60" y="240" fill={DW} fontSize="9" fontFamily={font}>Infiltration</text>

      <text x="200" y="302" fill={DW} fontSize="9.5" textAnchor="middle" fontFamily={font}>
        Water Cycle — continuous movement of water through Earth's systems
      </text>
    </svg>
  )
}

/* ══════════════════════════════════════════════════════════
   5. Food Chain
   ══════════════════════════════════════════════════════════ */
function FoodChainDiagram() {
  const levels = [
    { icon: '☀️', label: 'Sun',         sub: 'Energy source',   color: '#FFE066' },
    { icon: '🌿', label: 'Grass',        sub: 'Producer',        color: G },
    { icon: '🦗', label: 'Grasshopper', sub: '1° Consumer',      color: C },
    { icon: '🐸', label: 'Frog',         sub: '2° Consumer',     color: V },
    { icon: '🐍', label: 'Snake',        sub: '3° Consumer',     color: O },
    { icon: '🦅', label: 'Eagle',        sub: 'Apex predator',   color: P },
  ]
  const spacing = 60

  return (
    <svg viewBox="0 0 380 290" xmlns="http://www.w3.org/2000/svg" className="diagram-svg">
      <defs>
        <marker id="arr-f" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
          <path d="M1 1 L7 4 L1 7 Z" fill="rgba(255,255,255,0.5)"/>
        </marker>
      </defs>

      {/* Energy flow bar */}
      <rect x="14" y="225" width="350" height="6" rx="3"
            fill="url(#sunW)" opacity="0.2"/>
      <text x="190" y="248" fill={DW} fontSize="9.5" textAnchor="middle" fontFamily={font}>
        ← Energy decreases along the chain (10% rule)
      </text>

      {levels.map(({ icon, label, sub, color }, i) => {
        const x = 20 + i * spacing
        const barH = 130 - i * 18   // trophic pyramid effect
        const barY = 218 - barH
        return (
          <g key={i}>
            {/* Energy bar */}
            <rect x={x + 4} y={barY} width={42} height={barH} rx="4"
                  fill={color} opacity="0.18"/>
            <rect x={x + 4} y={barY} width={42} height={4} rx="2"
                  fill={color} opacity="0.8"/>

            {/* Icon */}
            <text x={x + 25} y={barY - 20} fontSize="22" textAnchor="middle" fontFamily={font}>{icon}</text>

            {/* Arrow to next */}
            {i < levels.length - 1 && (
              <line x1={x + 46} y1={barY - 12} x2={x + 58} y2={barY - 12}
                    stroke="rgba(255,255,255,0.35)" strokeWidth="1.5" markerEnd="url(#arr-f)"/>
            )}

            {/* Labels */}
            <text x={x + 25} y={barY - 6}  fill={color} fontSize="10" fontWeight="700"
                  textAnchor="middle" fontFamily={font}>{label}</text>
            <text x={x + 25} y={210}        fill={DW}   fontSize="8.5"
                  textAnchor="middle" fontFamily={font}>{sub}</text>
          </g>
        )
      })}

      {/* Decomposers note */}
      <text x="190" y="270" fill={DW} fontSize="9" textAnchor="middle" fontFamily={font}>
        Decomposers (fungi/bacteria) recycle nutrients from every level
      </text>
    </svg>
  )
}

/* ══════════════════════════════════════════════════════════
   Topic → Diagram matcher
   ══════════════════════════════════════════════════════════ */
const MAP = [
  { keys: ['digest', 'stomach', 'intestine', 'alimentary'], component: DigestiveSystemDiagram },
  { keys: ['photo',  'chlorophyll', 'chloroplast', 'glucose', 'co2'],  component: PhotosynthesisDiagram },
  { keys: ['eye',    'retina', 'cornea', 'pupil', 'lens', 'vision'],   component: HumanEyeDiagram },
  { keys: ['water',  'cycle',  'evaporation', 'rain', 'runoff'],       component: WaterCycleDiagram },
  { keys: ['food',   'chain',  'prey', 'predator', 'producer', 'consumer'], component: FoodChainDiagram },
]

export default function TopicDiagram({ topic = '', keywords = [] }) {
  const search = [topic, ...keywords].join(' ').toLowerCase()
  const match  = MAP.find(({ keys }) => keys.some(k => search.includes(k)))
  if (!match) return null

  const Diagram = match.component
  return (
    <div className="diagram-wrapper">
      <Diagram />
    </div>
  )
}
