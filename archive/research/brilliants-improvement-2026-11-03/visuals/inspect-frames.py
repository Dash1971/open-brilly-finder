#!/usr/bin/env python3
"""Small study contact sheet from exported GIFs; no browser or engine."""
import json,sys
from pathlib import Path
sys.path.insert(0,'/private/tmp/mute-research-plot')
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs';cases=json.loads((ROOT/'cases.json').read_text());contact=Image.new('RGB',(1280,1440),'#fafbf7');draw=ImageDraw.Draw(contact);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',14);audit=[]
for row,case in enumerate(cases):
 path=OUT/(case['id']+'.gif');gif=Image.open(path);count=gif.n_frames;indices=[0,4,13,count-1] if count>14 else[0,3,6,count-1];times=[];elapsed=0
 for i in range(count):
  gif.seek(i);times.append(elapsed);elapsed+=gif.info.get('duration',0)
 for col,index in enumerate(indices):
  gif.seek(index);image=gif.convert('RGB').crop((24,104,664,744)).resize((320,320),Image.Resampling.LANCZOS);contact.paste(image,(320*col,360*row+40));draw.text((320*col+6,360*row+5),case['id']+' · frame'+str(index),font=font,fill='#172723');draw.text((320*col+6,360*row+23),f'{times[index]/1000:.2f}s',font=font,fill='#496357')
 audit.append({'case':case['id'],'gif_frames':count,'duration_ms':elapsed,'inspected_frames':indices,'inspected_times_ms':[times[i] for i in indices]})
contact.save(OUT/'animation-contact-sheet.png');(OUT/'animation-frame-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit))
