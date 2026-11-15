import { useEffect, useState } from 'react';
type Geometry = { type: string; coordinates: number[][][] | number[][][][] };
let countries: Promise<Geometry[]> | undefined;
export function mapExtent(bbox: number[]) {
  const [w,s,e,n]=bbox, cy=(s+n)/2,cx=(w+e)/2;
  const height=Math.max((n-s)*1.7,(e-w)*1.7/1.8,8), width=height*1.8;
  return [cx-width/2,cy-height/2,cx+width/2,cy+height/2];
}
export function GeoBackdrop({bbox=[-20,-5,55,45]}:{bbox?:number[]}) {
  const [shapes,setShapes]=useState<Geometry[]>([]);
  useEffect(()=>{let active=true; countries ??= fetch(`${import.meta.env.BASE_URL}world-countries.geojson`).then(r=>{if(!r.ok)throw Error('Map unavailable');return r.json()}).then(d=>d.features.map((f:{geometry:Geometry})=>f.geometry)); countries.then(s=>{if(active)setShapes(s)}).catch(()=>{});return()=>{active=false}},[]);
  const [w,s,e,n]=bbox;
  return <svg className="geo-backdrop" viewBox={`${w} ${-n} ${e-w} ${n-s}`} preserveAspectRatio="none" role="img" aria-label="Geographic context map, Natural Earth country boundaries">
    <rect x={w} y={-n} width={e-w} height={n-s} fill="#0b3447"/>
    <image href={`${import.meta.env.BASE_URL}africa-blue-marble.jpg`} x={-40} y={-50} width={110} height={70} preserveAspectRatio="none"/>
    {shapes.map((g,i)=>{const polygons=g.type==='Polygon'?[g.coordinates]:g.coordinates;return <path key={i} d={(polygons as number[][][][]).map(p=>p.map(r=>r.map(([x,y],j)=>`${j?'L':'M'}${x},${-y}`).join(' ')+'Z').join(' ')).join(' ')} fill="none" stroke="#d7e7df" strokeOpacity=".55" strokeWidth=".06" fillRule="evenodd"/>})}
  </svg>
}
