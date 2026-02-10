// Simplified world continent outlines as SVG path data
// Coordinates are in Mercator-projected SVG space (960x500 viewBox)
// Derived from Natural Earth 110m simplified to ~20-40 vertices per continent
// Each path is an array of [x, y] points that will be joined as an SVG polygon

export interface ContinentPath {
  id: string
  name: string
  d: string
}

// Helper: convert lat/lng to Mercator SVG coords in a 960x500 viewBox
function p(lat: number, lng: number): [number, number] {
  const x = (lng + 180) * (960 / 360)
  const latRad = (lat * Math.PI) / 180
  const mercN = Math.log(Math.tan(Math.PI / 4 + latRad / 2))
  const y = 250 - (960 * mercN) / (2 * Math.PI)
  return [Math.round(x * 10) / 10, Math.round(y * 10) / 10]
}

function toPath(coords: [number, number][]): string {
  return (
    "M" +
    coords.map(([x, y]) => `${x},${y}`).join("L") +
    "Z"
  )
}

// North America (simplified outline)
const northAmerica = toPath([
  p(49, -125), p(60, -140), p(70, -140), p(72, -120),
  p(75, -95),  p(72, -75),  p(60, -65),  p(50, -55),
  p(47, -60),  p(45, -67),  p(43, -70),  p(40, -74),
  p(30, -82),  p(25, -80),  p(25, -90),  p(20, -87),
  p(15, -88),  p(15, -92),  p(20, -105), p(23, -110),
  p(30, -115), p(32, -117), p(34, -120), p(38, -123),
  p(42, -124), p(46, -124),
])

// South America
const southAmerica = toPath([
  p(12, -72),  p(10, -62),  p(8, -60),   p(5, -52),
  p(0, -50),   p(-5, -35),  p(-10, -37), p(-15, -39),
  p(-22, -41), p(-28, -49), p(-33, -52), p(-40, -62),
  p(-48, -66), p(-55, -68), p(-55, -70), p(-50, -75),
  p(-42, -73), p(-35, -72), p(-20, -70), p(-15, -76),
  p(-5, -80),  p(0, -78),   p(5, -77),   p(10, -75),
])

// Europe (including British Isles roughly)
const europe = toPath([
  p(36, -10),  p(38, -5),   p(43, -9),   p(44, -1),
  p(47, -2),   p(49, 0),    p(51, 2),    p(54, -3),
  p(58, -5),   p(60, 5),    p(64, 10),   p(70, 20),
  p(71, 28),   p(70, 32),   p(65, 30),   p(60, 30),
  p(56, 24),   p(55, 20),   p(54, 14),   p(51, 7),
  p(48, 8),    p(46, 15),   p(44, 12),   p(42, 3),
  p(37, -2),   p(36, -5),
])

// Africa
const africa = toPath([
  p(37, -10),  p(37, 10),   p(35, 12),   p(32, 13),
  p(30, 33),   p(22, 37),   p(12, 44),   p(10, 42),
  p(5, 42),    p(0, 42),    p(-5, 40),   p(-12, 44),
  p(-20, 36),  p(-26, 33),  p(-34, 26),  p(-35, 20),
  p(-30, 17),  p(-22, 14),  p(-15, 12),  p(-5, 10),
  p(0, 10),    p(5, 2),     p(5, -5),    p(7, -5),
  p(10, -15),  p(15, -17),  p(20, -17),  p(25, -15),
  p(30, -10),  p(35, -5),
])

// Asia (simplified -- includes Middle East through East Asia)
const asia = toPath([
  p(70, 32),   p(72, 60),   p(75, 80),   p(73, 100),
  p(72, 120),  p(70, 135),  p(65, 140),  p(60, 143),
  p(55, 135),  p(50, 140),  p(45, 142),  p(40, 140),
  p(35, 140),  p(35, 130),  p(30, 120),  p(22, 120),
  p(20, 110),  p(10, 107),  p(5, 105),   p(1, 104),
  p(8, 80),    p(12, 78),   p(20, 73),   p(25, 68),
  p(27, 56),   p(30, 48),   p(32, 36),   p(35, 36),
  p(40, 44),   p(42, 40),   p(44, 38),   p(50, 40),
  p(55, 38),   p(55, 32),   p(60, 30),   p(65, 30),
])

// Australia
const australia = toPath([
  p(-12, 131), p(-12, 136), p(-15, 140), p(-20, 148),
  p(-28, 153), p(-33, 152), p(-37, 150), p(-39, 146),
  p(-38, 141), p(-35, 137), p(-32, 133), p(-35, 117),
  p(-33, 115), p(-28, 114), p(-22, 114), p(-17, 122),
  p(-14, 126), p(-12, 129),
])

// Greenland
const greenland = toPath([
  p(60, -45),  p(65, -55),  p(70, -55),  p(76, -60),
  p(80, -50),  p(82, -35),  p(80, -20),  p(76, -18),
  p(70, -22),  p(65, -40),  p(62, -43),
])

export const WORLD_PATHS: ContinentPath[] = [
  { id: "na", name: "North America", d: northAmerica },
  { id: "sa", name: "South America", d: southAmerica },
  { id: "eu", name: "Europe", d: europe },
  { id: "af", name: "Africa", d: africa },
  { id: "as", name: "Asia", d: asia },
  { id: "oc", name: "Oceania", d: australia },
  { id: "gl", name: "Greenland", d: greenland },
]

// Grid lines for the map background (every 30 degrees)
export function generateGridLines(
  width: number,
  height: number
): { x1: number; y1: number; x2: number; y2: number }[] {
  const lines: { x1: number; y1: number; x2: number; y2: number }[] = []

  // Longitude lines (vertical)
  for (let lng = -180; lng <= 180; lng += 30) {
    const x = (lng + 180) * (width / 360)
    lines.push({ x1: x, y1: 0, x2: x, y2: height })
  }

  // Latitude lines (horizontal) -- Mercator spaced
  for (let lat = -60; lat <= 75; lat += 15) {
    const [, y] = p(lat, 0)
    lines.push({ x1: 0, y1: y, x2: width, y2: y })
  }

  return lines
}

/** Convert lat/lng to SVG coordinates in 960x500 viewBox */
export function latLngToSVG(lat: number, lng: number): { x: number; y: number } {
  const [x, y] = p(lat, lng)
  return { x, y }
}
