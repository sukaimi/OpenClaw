// cc-sp-manifest: COMPLETE rendered-content inventory of a SharePoint page (authed).
// Captures <img> AND css background-image, links, nav, footer, text — the manifest the
// build must reproduce and the completeness-gate diffs against. Usage: node cc-sp-manifest.mjs <url> <out.json> [--auth]
import { chromium } from "playwright"; import { existsSync, writeFileSync, mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
const url=process.argv[2], out=process.argv[3], useAuth=process.argv.includes("--auth");
// --download-images <dir>: also DOWNLOAD each CONTENT image's bytes (fresh in-session,
//   so expiring afdcache URLs resolve) into <dir>, and merge an images-map.json at
//   --images-map <path> keyed by the SAME normalized server-relative src that
//   sp-audit/image_migrate use. This closes the capture-byte gap: cc-sp-capture only
//   parses stored page-body <img>, missing rendered-only images (e.g. jes_red.jpg).
const dlDir=(()=>{const i=process.argv.indexOf("--download-images");return i>0?process.argv[i+1]:null;})();
const imgMapPath=(()=>{const i=process.argv.indexOf("--images-map");return i>0?process.argv[i+1]:null;})();
// state file: per-host (~/.codecraft/verify-<host>.json), so the same tool can
// capture SOURCE (intranet.mdlz.com) and BUILT (codeandcanvas.sharepoint.com) pages.
// Override with --state <path>. Falls back to the legacy intranet state if the
// per-host file is absent (preserves prior behaviour).
const stateArg=(()=>{const i=process.argv.indexOf("--state");return i>0?process.argv[i+1]:null;})();
const hostOf=u=>{try{return new URL(u).host;}catch{return"";}};
const perHost=process.env.HOME+"/.codecraft/verify-"+hostOf(url)+".json";
const legacy=process.env.HOME+"/.codecraft/verify-intranet.mdlz.com.json";
const STATE=stateArg||(existsSync(perHost)?perHost:legacy);
const b=await chromium.launch({headless:true}); const opts={viewport:{width:1440,height:1200}};
if(useAuth&&existsSync(STATE))opts.storageState=STATE;
const ctx=await b.newContext(opts); const page=await ctx.newPage();
await page.goto(url,{waitUntil:"networkidle",timeout:60000}).catch(()=>{}); await page.waitForTimeout(4500);
const m=await page.evaluate(()=>{
  const abs=u=>{try{return new URL(u,location.href).href;}catch{return u;}};
  const CH='#suiteBarTop,#suiteBarDelta,.o365cs-base,.o365cs-nav,#s4-ribbonrow,.ms-cui-ribbon,#sideNavBox,.ms-core-navigation,#suiteBar,#ms-cui-ribbonTopBars,#DeltaSPWebPartManager';
  const NAVSEL='#DeltaTopNavigation,.ms-breadcrumb,#zz1_TopNavigationMenuV4';
  const FOOT='#footerControl,footer,.ms-footer,[class*=Footer],[id*= footer i]';
  const inChrome=el=>el.closest&&el.closest(CH)!=null;
  const inFooter=el=>el.closest&&el.closest(FOOT)!=null;
  const inNav=el=>el.closest&&el.closest(NAVSEL)!=null;
  const zone=el=>{let c=el;for(let i=0;i<6&&c;i++){const id=c.id||(c.getAttribute&&(c.getAttribute('aria-label')||c.getAttribute('data-name')));if(id&&!/^ctl|^MSO|^ctl00/.test(id))return id.slice(0,38);c=c.parentElement;}return'';};
  const seen=new Set(), images=[];
  const add=(src,alt,link,el,kind)=>{src=abs(src);if(!src||seen.has(src)||/gradient|\.svg($|\?)|spacer|blank\.gif|^data:/i.test(src))return;seen.add(src);images.push({src,alt:(alt||'').slice(0,60),link:link?abs(link):'',zone:zone(el),area:inFooter(el)?'footer':inNav(el)?'nav':'content',kind});};
  document.querySelectorAll('img').forEach(im=>{if(inChrome(im))return;const r=im.getBoundingClientRect();if(r.width<22||r.height<22)return;add(im.currentSrc||im.src,im.alt,(im.closest('a')||{}).href,im,'img');});
  document.querySelectorAll('*').forEach(el=>{if(inChrome(el))return;const bg=getComputedStyle(el).backgroundImage;if(bg&&bg.indexOf('url(')===0){const mm=bg.match(/url\(["']?(.*?)["']?\)/);if(mm){const r=el.getBoundingClientRect();if(r.width>=40&&r.height>=40)add(mm[1],el.getAttribute('aria-label')||el.title,(el.closest('a')||{}).href,el,'bg');}}});
  const lseen=new Set(),links=[];
  document.querySelectorAll('a[href]').forEach(a=>{if(inChrome(a))return;const t=(a.innerText||a.textContent||'').trim();const h=abs(a.href);const raw=a.getAttribute('href')||'';if(!t||t.length>60||/^javascript|^#$/.test(raw))return;const k=t.toLowerCase()+'|'+h;if(lseen.has(k))return;lseen.add(k);links.push({text:t,link:h,area:inFooter(a)?'footer':inNav(a)?'nav':'content',zone:zone(a)});});
  const text=[...new Set([...document.querySelectorAll('h1,h2,h3,p')].filter(e=>!inChrome(e)).map(e=>(e.innerText||'').trim()).filter(t=>t.length>14&&t.length<300))].slice(0,40);
  return {title:document.title,images,links,text};
});
writeFileSync(out,JSON.stringify({source:url,...m},null,1));
const byArea=a=>m.images.filter(i=>i.area===a).length, lByArea=a=>m.links.filter(l=>l.area===a).length;
console.log("IMAGES total:",m.images.length,"(content",byArea('content'),"nav",byArea('nav'),"footer",byArea('footer'),")");
console.log("  content image zones:",[...new Set(m.images.filter(i=>i.area==='content').map(i=>i.zone))].slice(0,12).join(" | "));
console.log("LINKS total:",m.links.length,"(content",lByArea('content'),"nav",lByArea('nav'),"footer",lByArea('footer'),")");
console.log("  nav links:",m.links.filter(l=>l.area==='nav').map(l=>l.text).slice(0,12).join(" | "));
console.log("  footer:",[...m.images.filter(i=>i.area==='footer').map(i=>'IMG:'+(i.alt||i.src.split('/').pop())), ...m.links.filter(l=>l.area==='footer').map(l=>l.text)].slice(0,8).join(" | "));
console.log("TEXT blocks:",m.text.length);

// DOWNLOAD content image bytes (closes the capture-byte gap). Mirrors the gate's
// CONTENT scope: area==='content' AND zone not chrome (lnkLogo / s4-*).
if(dlDir){
  const normSrc=s=>{s=(s||"").split("?")[0];const i=s.indexOf("://");if(i>=0){const rest=s.slice(i+3);const sl=rest.indexOf("/");s=sl>=0?rest.slice(sl):"/";}const mk="/_vti_bin/afdcache.ashx/authitem";const j=s.indexOf(mk);if(j>=0)s=s.slice(j+mk.length);return s;};
  const isChromeZone=z=>{const zz=(z||"").trim();return zz==="lnkLogo"||zz.startsWith("s4-");};
  mkdirSync(dlDir,{recursive:true});
  let map={};
  if(imgMapPath&&existsSync(imgMapPath)){try{map=JSON.parse(readFileSync(imgMapPath,"utf8"));}catch{}}
  let idx=Object.keys(map).length, dl=0, skip=0, fail=0;
  for(const im of m.images){
    if(im.area!=="content"||isChromeZone(im.zone))continue;
    const key=normSrc(im.src);
    if(!key||map[key]){skip++;continue;}
    const r=await ctx.request.get(im.src,{timeout:60000}).catch(()=>null);
    if(!r||r.status()>=300){fail++;console.log("  [DL-FAIL]",key,r?r.status():"err");continue;}
    const buf=await r.body();
    const base=(key.split("/").pop()||("img-"+idx)).replace(/[^A-Za-z0-9._-]/g,"-");
    const local="images/"+String(idx).padStart(3,"0")+"-"+base;
    writeFileSync(join(dlDir,String(idx).padStart(3,"0")+"-"+base),buf);
    map[key]=local; idx++; dl++;
  }
  if(imgMapPath)writeFileSync(imgMapPath,JSON.stringify(map,null,1));
  console.log("IMAGE DOWNLOAD: +"+dl+" new, "+skip+" already-mapped, "+fail+" failed -> "+(imgMapPath||dlDir));
}
await b.close();
