import { useMemo, useRef } from "react";
import { geoEqualEarth, geoPath } from "d3-geo";
import { feature, mesh } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import worldTopo from "../data/world-110m.json";

const WIDTH = 800;
const HEIGHT = 500;

export interface Pin {
  lat: number;
  lng: number;
}

interface Props {
  guess: Pin | null;
  truth?: Pin | null; // shown on the reveal screen
  onGuess?: (pin: Pin) => void;
}

export default function WorldMap({ guess, truth, onGuess }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);

  const countries = useMemo(() => {
    const topo = worldTopo as unknown as Topology;
    return feature(topo, topo.objects.countries as GeometryCollection);
  }, []);

  const borders = useMemo(() => {
    const topo = worldTopo as unknown as Topology;
    // Includes both shared country borders and coastlines (mesh treats the
    // ocean side of a coastal arc as an implicit second, distinct object).
    return mesh(topo, topo.objects.countries as GeometryCollection, (a, b) => a !== b);
  }, []);

  const projection = useMemo(() => {
    return geoEqualEarth().fitSize([WIDTH, HEIGHT], countries);
  }, [countries]);

  const path = useMemo(() => geoPath(projection), [projection]);

  function handleClick(e: React.MouseEvent<SVGSVGElement>) {
    if (!onGuess || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * WIDTH;
    const y = ((e.clientY - rect.top) / rect.height) * HEIGHT;
    const inverted = projection.invert?.([x, y]);
    if (!inverted) return;
    const [lng, lat] = inverted;
    onGuess({ lat, lng });
  }

  function project(pin: Pin): [number, number] | null {
    return projection([pin.lng, pin.lat]);
  }

  const guessXY = guess ? project(guess) : null;
  const truthXY = truth ? project(truth) : null;

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="world-map"
      onClick={handleClick}
      role="img"
      aria-label="World map — click to place your guess"
    >
      <rect x={0} y={0} width={WIDTH} height={HEIGHT} className="world-map-ocean" />
      {countries.features.map((f, i) => (
        <path key={i} d={path(f) ?? undefined} className="world-map-land" />
      ))}
      <path d={path(borders) ?? undefined} className="world-map-borders" />
      {guessXY && <circle cx={guessXY[0]} cy={guessXY[1]} r={6} className="pin pin-guess" />}
      {truthXY && <circle cx={truthXY[0]} cy={truthXY[1]} r={6} className="pin pin-truth" />}
      {guessXY && truthXY && (
        <line x1={guessXY[0]} y1={guessXY[1]} x2={truthXY[0]} y2={truthXY[1]} className="pin-line" />
      )}
    </svg>
  );
}
