import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
const clamp=(n:number)=>Math.max(0,Math.min(1,n));
const smooth=(n:number)=>{const p=clamp(n);return p*p*(3-2*p)};
function Researcher({scene}:{scene:number}) {
 return <div className="section-actor" data-scene={['plant','umbrella','wave'][scene]} aria-hidden="true"><svg viewBox="0 0 260 200">
 <ellipse cx="130" cy="182" rx="90" ry="7" fill="#061b29" opacity=".15"/>
 {scene===2&&<g><path d="M30 191Q130 139 230 191" fill="#275b73" stroke="#93cfce"/><path d="M65 178l25-9 19 8 23-12 22 8 31 2" fill="none" stroke="#81b282" strokeWidth="7"/></g>}
 {scene===0&&<g data-part="seed"><ellipse cx="184" cy="180" rx="14" ry="4" fill="#80684b"/><path d="M184 180v-23" stroke="#8cbf69" strokeWidth="3"/><path d="M184 168q-17 0-16-12 15 0 16 12m0-5q14 0 15-13-14 1-15 13" fill="#a3d77b"/></g>}
 {scene===1&&<g data-part="rain"><path d="M64 20l-8 20m49-28-8 20m54-14-8 20m53-22-8 20m35 24-8 20M45 82l-8 20m49-28-8 20m131 2-8 20m-145 9-8 20m174-12-8 20" stroke="#a3cad9" strokeWidth="1.5" strokeLinecap="round"/></g>}
 <g data-part="body">
 <g data-part="backleg"><path d="M113 122l-3 27 2 25" fill="none" stroke="#56717b" strokeWidth="13" strokeLinecap="round"/><path d="M108 173h17" stroke="#173447" strokeWidth="9" strokeLinecap="round"/></g>
 <g data-part="frontleg"><path d="M130 122l4 27 2 25" fill="none" stroke="#d3ded8" strokeWidth="14" strokeLinecap="round"/><path d="M132 174h18" stroke="#203b4a" strokeWidth="9" strokeLinecap="round"/><path d="M128 145h12" stroke="#6d8a8d" strokeWidth="5"/></g>
 <rect x="91" y="78" width="21" height="44" rx="7" fill="#476872" stroke="#9cb6b5" strokeWidth="2"/><rect x="95" y="81" width="12" height="18" rx="3" fill="#173c40"/><path d="M101 95v-8m0 4-4-4m4 2 4-5" stroke="#b1d783" strokeWidth="1.8"/>
 <path d="M111 75q12-5 25 1l7 41-10 15h-24l-7-17z" fill="#dbe3dc" stroke="#315362" strokeWidth="2"/><path d="M107 109h31v10h-31" fill="#527279"/><rect x="115" y="86" width="18" height="18" rx="3" fill="#1d4552"/><path d="M120 97l4-6 5 6" fill="none" stroke="#b4dd86" strokeWidth="2"/>
 <g data-part="backarm"><path d="M108 83l-8 19 6 17" fill="none" stroke="#90a9ac" strokeWidth="10" strokeLinecap="round"/><circle cx="106" cy="120" r="6" fill="#294651"/></g>
 <g data-part="frontarm"><path d="M136 83l9 20 8 12" fill="none" stroke="#dbe3dc" strokeWidth="10" strokeLinecap="round"/><path d="M143 101l7 4" stroke="#68858b" strokeWidth="4"/><circle cx="155" cy="117" r="6" fill="#294651"/></g>
 <g data-part="helmet"><path d="M108 68h28v10h-28" fill="#6b898e"/><rect x="105" y="37" width="37" height="36" rx="15" fill="#e2e7dc" stroke="#456774" strokeWidth="2"/><path d="M115 43h15q10 0 10 11v9h-25q-7-2-7-10t7-10" fill="#133a4b"/><path d="M117 46h12" stroke="#9acbd1" strokeWidth="2" strokeLinecap="round"/><path d="M107 58v7" stroke="#b4d781" strokeWidth="3"/></g>
 {scene===1&&<g data-part="umbrella"><path d="M156 116V31" stroke="#8caeb9" strokeWidth="3"/><g data-part="canopy"><path d="M110 38q46-52 92 0-13-6-23 0-12-7-23 0-12-7-23 0-12-6-23 0" fill="#315f67" stroke="#a7d0ca" strokeWidth="2"/><path d="M156 13q-19 11-23 25m23-25q19 11 23 25" fill="none" stroke="#7aaba7"/></g></g>}
 </g></svg></div>
}
export function ScrollJourney(){
 const [sections,setSections]=useState<HTMLElement[]>([]);
 useEffect(()=>{setSections(['story','method','sources'].map(id=>document.getElementById(id)).filter((el):el is HTMLElement=>!!el))},[]);
 useEffect(()=>{
  if(sections.length!==3)return;
  const reduce=matchMedia('(prefers-reduced-motion: reduce)');
  const actors=sections.map(s=>s.querySelector<HTMLElement>('.section-actor')!);
  const parts=actors.map(a=>Object.fromEntries(['body','backleg','frontleg','backarm','frontarm','helmet','canopy','umbrella','seed','rain'].map(k=>[k,a.querySelector<SVGElement>(`[data-part="${k}"]`)])));
  const plant=parts[0];
  const limbs={front:plant.frontleg?.querySelector('path'),back:plant.backleg?.querySelector('path'),arm:plant.frontarm?.querySelector('path'),hand:plant.frontarm?.querySelector('circle'),frontBoot:plant.frontleg?.querySelectorAll('path')[1],backBoot:plant.backleg?.querySelectorAll('path')[1]};
  let raf=0,last=0;const targets=[0,0,0],progress=[0,0,0],visible=[false,false,false];
  const sample=()=>{actors.forEach((actor,i)=>{const r=actor.getBoundingClientRect();visible[i]=r.bottom>0&&r.top<innerHeight;targets[i]=smooth((innerHeight*.9-r.top)/Math.max(240,innerHeight*.55));});if(!raf&&!document.hidden)raf=requestAnimationFrame(tick)};
  const set=(el:SVGElement|null,value:string)=>el?.setAttribute('transform',value);
  const tick=(now:number)=>{raf=0;if(document.hidden)return;const dt=last?Math.min(50,now-last):16;last=now;
   parts.forEach((a,i)=>{if(!visible[i])return;progress[i]+=(targets[i]-progress[i])*(reduce.matches?1:1-Math.exp(-dt/85));const p=reduce.matches?1:progress[i],walk=clamp(p/.4),action=smooth((p-.38)/.5),gait=Math.sin(walk*Math.PI*8)*(1-action),bend=i===0?action:0;
    set(a.body,`translate(${-38+walk*45} ${bend*20})`);
    set(a.backleg,`rotate(${gait*22} 113 123)`);set(a.frontleg,`rotate(${-gait*22} 130 123)`);
    if(i===0){limbs.front?.setAttribute('d',`M130 122L${134+18*bend} ${149-7*bend}L${136+14*bend} ${174-20*bend}`);limbs.back?.setAttribute('d',`M113 122L${110-16*bend} ${149-2*bend}L${112+4*bend} ${174-20*bend}`);limbs.frontBoot?.setAttribute('transform',`translate(${14*bend} ${-20*bend})`);limbs.backBoot?.setAttribute('transform',`translate(${4*bend} ${-20*bend})`);limbs.arm?.setAttribute('d',`M136 83L${145+13*bend} ${103+28*bend}L${153+24*bend} ${115+40*bend}`);limbs.hand?.setAttribute('cx',String(155+24*bend));limbs.hand?.setAttribute('cy',String(117+40*bend));}
    set(a.backarm,`rotate(${-gait*17-bend*40} 108 83)`);
    const arm=i===0?0:i===1?-action*25:-action*(125+(reduce.matches?0:Math.sin(now/280)*10));
    set(a.frontarm,`rotate(${arm+gait*15} 136 83)`);set(a.helmet,`rotate(${bend*14} 123 72)`);
    set(a.canopy,`translate(156 38) scale(${.12+.88*action} 1) translate(-156 -38)`);
    if(a.umbrella)a.umbrella.style.opacity=String(action);if(a.seed)a.seed.style.opacity=String(smooth((p-.62)/.25));
    if(a.rain){a.rain.style.opacity=String(action*.65);set(a.rain,`translate(0 ${reduce.matches?0:(now/70)%14})`)}
    actors[i].dataset.progress=p.toFixed(3);actors[i].dataset.phase=p<.4?'walk':['plant','shelter','wave'][i];
   });if(!reduce.matches&&visible.some(Boolean))raf=requestAnimationFrame(tick);
  };
  const visibility=()=>{cancelAnimationFrame(raf);raf=0;last=0;if(!document.hidden)sample()};
  sample();addEventListener('scroll',sample,{passive:true});addEventListener('resize',sample);document.addEventListener('visibilitychange',visibility);reduce.addEventListener('change',sample);
  return()=>{cancelAnimationFrame(raf);removeEventListener('scroll',sample);removeEventListener('resize',sample);document.removeEventListener('visibilitychange',visibility);reduce.removeEventListener('change',sample)};
 },[sections]);
 return <>{sections.map((section,i)=>createPortal(<Researcher scene={i}/>,section,String(i)))}</>;
}
