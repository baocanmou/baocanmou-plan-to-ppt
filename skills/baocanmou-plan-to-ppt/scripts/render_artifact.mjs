#!/usr/bin/env node
// Optional host adapter. The proprietary SDK is not included or downloaded.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  if (!['--plan', '--out', '--preview'].includes(process.argv[i]) || !process.argv[i+1]) throw new Error('Usage: --plan plan.json --out draft.pptx [--preview directory]');
  args[process.argv[i].slice(2)] = process.argv[i+1];
}
if (!args.plan || !args.out) throw new Error('--plan and --out are required');
const planPath = path.resolve(args.plan), outputPath = path.resolve(args.out);
if (planPath === outputPath) throw new Error('Output cannot overwrite plan');
try { await fs.access(outputPath); throw new Error('Output exists; choose a new version filename'); }
catch (e) { if (e.code !== 'ENOENT') throw e; }
const plan = JSON.parse(await fs.readFile(planPath, 'utf8'));
const supported = new Set(['cover','statement','editorial','quote','image','table','chart','closing','framework']);
for (const s of plan.slides ?? []) if (!supported.has(s.layout)) throw new Error(`Unsupported layout: ${s.layout}`);
const sdkPath = process.env.BCM_ARTIFACT_MODULE;
if (sdkPath && !path.isAbsolute(sdkPath)) throw new Error('BCM_ARTIFACT_MODULE must be an absolute module path');
let sdk;
try { sdk = await import(sdkPath ? pathToFileURL(sdkPath).href : '@oai/artifact-tool'); }
catch { throw new Error('Host Artifact Tool unavailable. Use the host PPTX capability described in references/rendering.md; this adapter never downloads a private SDK.'); }
const { Presentation, PresentationFile } = sdk;
const p = Presentation.create({slideSize:{width:1280,height:720}});
const theme = {paper:'#F4F1E8',ink:'#183E34',accent:'#CADD80',muted:'#586B60',font:'Source Han Sans CN',...plan.theme};
const claimMap = new Map((plan.claims ?? []).map(c=>[c.id,c]));

function text(slide, value, x, y, w, h, opts={}) {
  if (value === undefined || value === null || value === '') return;
  const shape = slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text = String(value);
  shape.text.style = {typeface:theme.font,fontSize:opts.size??28,color:opts.color??theme.ink,bold:opts.bold??false,autoFit:'none',...opts.style};
  return shape;
}
async function picture(slide, spec, x,y,w,h) {
  if (!spec?.path) throw new Error('Image layout needs an existing image.path');
  const file = path.resolve(path.dirname(planPath),spec.path);
  if (!/\.(png|jpe?g)$/i.test(file)) throw new Error(`Use PNG/JPEG image: ${file}`);
  const bytes = await fs.readFile(file);
  slide.images.add({blob:bytes,contentType:/\.png$/i.test(file)?'image/png':'image/jpeg',alt:spec.alt??'',fit:spec.fit??'cover',position:{left:x,top:y,width:w,height:h}});
}
function body(slide, rows, x,y,w,opts={}) {
  let cursor=y;
  for (const item of rows??[]) {
    const row = typeof item === 'string' ? {text:item} : item;
    if (row.heading) { text(slide,row.heading,x,cursor,w,42,{size:opts.headingSize??30,bold:true,color:opts.color}); cursor+=50; }
    text(slide,row.text,x,cursor,w,opts.rowHeight??72,{size:opts.size??26,color:opts.color});
    cursor+=(opts.rowHeight??72)+(opts.gap??20);
  }
}
for (let n=0;n<plan.slides.length;n++) {
  const s=plan.slides[n], slide=p.slides.add();
  const dark=s.tone==='dark';
  slide.background.fill=dark?theme.ink:theme.paper;
  const ink=dark?theme.paper:theme.ink, muted=dark?'#CDDACF':theme.muted;
  if (s.layout==='cover') {
    if(s.image) await picture(slide,s.image,0,0,1280,720);
    text(slide,s.eyebrow??plan.project.title,64,64,490,48,{size:22,color:theme.muted});
    text(slide,s.title,64,174,650,240,{size:62,bold:true});
    text(slide,s.lead,68,381,620,65,{size:25});
  } else if (s.layout==='closing') {
    text(slide,s.title,64,78,1136,112,{size:60,bold:true,color:ink});
    body(slide,s.body,70,245,1090,{size:32,rowHeight:65,gap:28,color:ink});
    text(slide,s.lead,70,575,1100,55,{size:24,color:muted});
  } else {
    text(slide,s.title,64,54,1148,94,{size:46,bold:true,color:ink});
    if(s.layout==='framework') {
      slide.shapes.add({geometry:'rect',position:{left:68,top:171,width:1136,height:148},fill:theme.ink,line:{fill:'none',width:0}});
      text(slide,s.center?.heading,86,204,278,70,{size:29,bold:true,color:theme.paper});
      text(slide,s.center?.text,390,188,780,120,{size:25,color:theme.paper});
      const cols=s.columns??[];
      if(cols.length!==3)throw new Error(`${s.id}: framework needs three action columns`);
      for(let j=0;j<3;j++){
        const x=80+j*398;
        text(slide,cols[j].heading,x,375,330,55,{size:32,bold:true});
        text(slide,cols[j].text,x,448,330,154,{size:26});
        if(j<2)text(slide,'→',x+332,379,48,48,{size:28,color:theme.muted});
      }
    } else if(s.layout==='statement') {
      text(slide,s.lead,65,211,1110,152,{size:60,bold:true,color:ink});
      body(slide,s.body,70,405,1050,{size:27,rowHeight:70,gap:17,color:ink});
    } else if(s.layout==='quote') {
      text(slide,s.lead,80,214,1090,195,{size:53,bold:true,color:ink});
      body(slide,s.body,85,460,1050,{size:25,rowHeight:75,gap:16,color:muted});
    } else if(s.layout==='editorial') {
      if(s.lead)text(slide,s.lead,68,168,1100,76,{size:29,color:muted});
      const cols=s.columns??[];
      if(cols.length<1||cols.length>3) throw new Error(`${s.id}: editorial requires 1-3 columns`);
      const colWidth=(1136-(cols.length-1)*60)/cols.length;
      for(let j=0;j<cols.length;j++) {
        const x=68+j*(colWidth+60);
        text(slide,cols[j].heading,x,285,colWidth,94,{size:36,bold:true,color:ink});
        text(slide,cols[j].text,x,406,colWidth,186,{size:27,color:ink});
      }
    } else if(s.layout==='image') {
      await picture(slide,s.image,604,167,612,445);
      text(slide,s.lead,68,190,466,113,{size:38,bold:true,color:ink});
      body(slide,s.body,70,360,452,{size:25,rowHeight:78,gap:15,color:ink});
    } else if(s.layout==='table') {
      if(s.lead) text(slide,s.lead,68,166,1110,58,{size:27,color:muted});
      const rows=s.table.rows,top=252,height=Math.min(342,rows.length*58);
      const table=slide.tables.add({rows:rows.length,columns:rows[0].length,left:68,top,width:1136,height,values:rows,columnWidths:s.table.widths});
      table.cells.block({row:0,column:0,rowCount:rows.length,columnCount:rows[0].length}).assign({textStyle:{typeface:theme.font,fontSize:s.table.fontSize??25,color:ink},fill:dark?theme.ink:theme.paper,margins:{left:15,right:15,top:10,bottom:10}});
      table.cells.block({row:0,column:0,rowCount:1,columnCount:rows[0].length}).assign({textStyle:{typeface:theme.font,fontSize:23,bold:true,color:theme.paper},fill:theme.ink});
      table.borders.assign({fill:'#CCD4C5',width:0.65,style:'solid'});
      for(let r=0;r<rows.length;r++) table.rows[r].height=height/rows.length;
      if(s.body?.length) body(slide,s.body,70,top+height+18,1110,{size:22,rowHeight:36,gap:0,color:muted});
    } else if(s.layout==='chart') {
      const d=s.chart;

      text(slide,s.lead,820,227,382,112,{size:43,bold:true,color:ink});
      body(slide,s.body,822,390,366,{size:24,rowHeight:102,gap:14,color:muted});
      const chart=slide.charts.add(d.type??'bar',{position:{left:64,top:198,width:698,height:410},categories:d.categories,series:d.series.map(x=>({...x,fill:theme.ink})),hasLegend:d.series.length>1,barOptions:{direction:d.direction??'bar',grouping:'clustered',gapWidth:80},chartFill:theme.paper,plotAreaFill:theme.paper,chartLine:{fill:'none',width:0},dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:theme.font,fontSize:22}},xAxis:{textStyle:{typeface:theme.font,fontSize:19},numberFormatCode:'0',min:0},yAxis:{textStyle:{typeface:theme.font,fontSize:21}},title:d.title??`${d.series[0]?.name??'数据'}（${d.unit}）`,titleTextStyle:{typeface:theme.font,fontSize:20}});

    }
  }
  if(s.method_attribution)text(slide,s.method_attribution,68,625,1120,30,{size:16,color:muted});
  const footer=[plan.project.disclosure,s.disclosure].filter(Boolean).join(' · ');
  if(footer)text(slide,footer,68,660,1094,36,{size:15,color:s.layout==='cover'?theme.paper:muted});
  text(slide,String(n+1).padStart(2,'0'),1190,662,54,28,{size:16,color:s.layout==='cover'?theme.paper:muted});
  const notes=[s.notes,...(s.claim_ids??[]).flatMap(id=>{const c=claimMap.get(id);return c?.sources?.map(r=>`来源 ${r.chunk_id}: ${r.quote}`)??[];}),s.image?.source?`图像来源：${s.image.source}`:''].filter(Boolean).join('\n');
  if(notes)slide.speakerNotes.textFrame.setText(notes);
  if(args.preview) {
    await fs.mkdir(args.preview,{recursive:true});
    const blob=await p.export({slide,format:'png',scale:1});
    await fs.writeFile(path.join(args.preview,`slide-${String(n+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
  }
}
await fs.mkdir(path.dirname(outputPath),{recursive:true});
await (await PresentationFile.exportPptx(p)).save(outputPath);
console.log(JSON.stringify({draft:outputPath,slides:plan.slides.length,preview:args.preview??null,finalized:false}));
