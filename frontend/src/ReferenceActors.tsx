import {useEffect,useState} from 'react';
import {createPortal} from 'react-dom';
export function ReferenceActors(){
 const [hosts,setHosts]=useState<HTMLElement[]>([]);
 useEffect(()=>{setHosts(['#story','.window-visual'].map(s=>document.querySelector<HTMLElement>(s)).filter((x):x is HTMLElement=>!!x))},[]);
 useEffect(()=>{
  if(hosts.length!==2)return;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const canvases=hosts.map(h=>h.querySelector<HTMLCanvasElement>('.reference-actor')!);
  const images=['astro-plant-atlas.png','astro-seated-atlas.png'].map(file=>{const im=new Image();im.src=import.meta.env.BASE_URL+file;return im});
  let raf=0,last=0;const progress=[0,0],target=[0,0],visible=[false,false];
  const paint=(time:number)=>{raf=0;const dt=last?Math.min(50,time-last):16;last=time;
   canvases.forEach((c,i)=>{if(!visible[i]||!images[i].naturalWidth)return;progress[i]+=(target[i]-progress[i])*(reduced.matches?1:1-Math.exp(-dt/95));const count=i?8:4;const frame=reduced.matches?(i?3:3):Math.min(count-1,Math.floor(progress[i]*count));const ctx=c.getContext('2d');if(!ctx)return;const image=images[i];ctx.clearRect(0,0,c.width,c.height);ctx.drawImage(image,frame*image.width/count,0,image.width/count,image.height,0,0,c.width,c.height);c.dataset.frame=String(frame)});
   if(!document.hidden&&!reduced.matches&&progress.some((p,i)=>visible[i]&&Math.abs(p-target[i])>.001))raf=requestAnimationFrame(paint);
  };
  const sample=()=>{canvases.forEach((c,i)=>{const r=c.getBoundingClientRect();visible[i]=r.bottom>0&&r.top<innerHeight;target[i]=Math.max(0,Math.min(.999,(innerHeight*.92-r.top)/(innerHeight*.7)));});if(!raf&&!document.hidden)raf=requestAnimationFrame(paint)};
  images.forEach(im=>im.decode().then(sample).catch(()=>{}));sample();addEventListener('scroll',sample,{passive:true});addEventListener('resize',sample);reduced.addEventListener('change',sample);
  return()=>{cancelAnimationFrame(raf);removeEventListener('scroll',sample);removeEventListener('resize',sample);reduced.removeEventListener('change',sample)};
 },[hosts]);
 return <>{hosts.map((h,i)=>createPortal(<canvas width={i?272:360} height={i?724:480} className={`reference-actor ${i?'seated':'gardener'}`} aria-hidden="true"/>,h,String(i)))}</>;
}
