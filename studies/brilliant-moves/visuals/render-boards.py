#!/usr/bin/env python3
"""Study-only native-piece PNG/GIF/SVG exports. No engine, browser, or live service."""
from pathlib import Path
import argparse,hashlib,html,io,json,math,re,resource,subprocess,sys,textwrap,time
import chess
from PIL import Image,ImageDraw,ImageFont,ImageChops
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/cburnett';RESVG=Path('resvg')
LIGHT='#c7cfba';DARK='#668478';GOLD=(217,178,95,107);INK='#172723';PAPER='#fafbf7';MINT='#aad6bd'
SQUARE=80;MARGIN=24;TOP=104;WIDTH=688;HEIGHT=920;BOARD=SQUARE*8

def font(size):
 for p in ('/System/Library/Fonts/Supplemental/Arial.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
  if Path(p).exists():return ImageFont.truetype(p,size)
 return ImageFont.load_default(size=size)

def xy(square,orientation):
 f=chess.square_file(square);r=chess.square_rank(square)
 return (MARGIN+(f if orientation=='white' else 7-f)*SQUARE,TOP+(7-r if orientation=='white' else r)*SQUARE)

def key(piece):return ('w' if piece.color else 'b')+piece.symbol().upper()

def pieces():
 """Rasterize each exact native SVG once; each subprocess exits immediately."""
 out={};cache=ROOT/'assets/raster';cache.mkdir(exist_ok=True)
 for source in sorted(ASSETS.glob('*.svg')):
  target=cache/(source.stem+'.png');digest=hashlib.sha256(source.read_bytes()).hexdigest();receipt=target.with_suffix('.sha256')
  if not target.exists() or not receipt.exists() or receipt.read_text()!=digest:
   subprocess.run([str(RESVG),str(source),'--width',str(SQUARE*2),str(target)],check=True,capture_output=True);receipt.write_text(digest)
  out[source.stem]=Image.open(target).convert('RGBA').resize((SQUARE,SQUARE),Image.Resampling.LANCZOS)
 return out

def state(case):
 board=chess.Board(case['fen_before']);moves=[];states=[board.copy()];sans=[]
 for text in case['moves']:
  move=board.parse_san(text);sans.append(board.san(move));moves.append(move);board.push(move);states.append(board.copy())
 return moves,states,sans

def canvas(case,caption,last,orientation):
 im=Image.new('RGBA',(WIDTH,HEIGHT),PAPER);d=ImageDraw.Draw(im)
 d.text((MARGIN,20),case['title'],font=font(25),fill=INK)
 d.text((MARGIN,58),case.get('subtitle',''),font=font(16),fill='#496357')
 for square in chess.SQUARES:
  x,y=xy(square,orientation);d.rectangle((x,y,x+SQUARE,y+SQUARE),fill=LIGHT if (chess.square_file(square)+chess.square_rank(square))%2 else DARK)
 if last:
  layer=Image.new('RGBA',im.size);ld=ImageDraw.Draw(layer)
  for square in (last.from_square,last.to_square):x,y=xy(square,orientation);ld.rectangle((x,y,x+SQUARE,y+SQUARE),fill=GOLD)
  im.alpha_composite(layer)
 # Coordinates stay outside the board so no piece overlaps them.
 for i in range(8):
  d.text((MARGIN+i*SQUARE+35,TOP+BOARD+5),'abcdefgh'[i if orientation=='white' else 7-i],font=font(13),fill='#557064')
  d.text((7,TOP+i*SQUARE+32),str(8-i if orientation=='white' else i+1),font=font(13),fill='#557064')
 d.text((MARGIN,TOP+BOARD+31),case.get('line_label','Illustrative continuation; replies are not forced.'),font=font(14),fill='#557064')
 for i,line in enumerate(textwrap.wrap(caption,76)[:3]):d.text((MARGIN,TOP+BOARD+57+i*21),line,font=font(17),fill=INK)
 d.text((MARGIN,HEIGHT-25),'Mute Chess Moss board · Cburnett pieces · Study illustration',font=font(12),fill='#557064')
 return im

def paste(im,piece,square,sprites,orientation,opacity=1,position=None):
 tile=sprites[key(piece)]
 if opacity<1:tile=tile.copy();tile.putalpha(tile.getchannel('A').point(lambda a:round(a*max(0,opacity))))
 im.alpha_composite(tile,tuple(round(v) for v in (position or xy(square,orientation))))

def still(case,board,caption,last,sprites,orientation):
 im=canvas(case,caption,last,orientation)
 for sq,p in board.piece_map().items():paste(im,p,sq,sprites,orientation)
 return im.convert('RGB')

def motion(case,before,after,move,caption,t,sprites,orientation):
 im=canvas(case,caption,move,orientation);eased=t*t*(3-2*t);moving={move.from_square:(move.to_square,before.piece_at(move.from_square))}
 if before.is_castling(move):
  rank=chess.square_rank(move.from_square);short=chess.square_file(move.to_square)>chess.square_file(move.from_square)
  moving[chess.square(7 if short else 0,rank)]=(chess.square(5 if short else 3,rank),chess.Piece(chess.ROOK,before.turn))
 capture=move.to_square if before.is_capture(move) else None
 if before.is_en_passant(move):capture=move.to_square+(-8 if before.turn else 8)
 for sq,p in before.piece_map().items():
  if sq in moving:continue
  # Native-style short capture fade; never retain captured material in the next state.
  paste(im,p,sq,sprites,orientation,max(0,1-t/0.48) if sq==capture else 1)
 for source,(target,piece) in moving.items():
  a=xy(source,orientation);b=xy(target,orientation);position=(a[0]+(b[0]-a[0])*eased,a[1]+(b[1]-a[1])*eased)
  if move.promotion and source==move.from_square and t>.8:
   fade=(t-.8)/.2;paste(im,piece,source,sprites,orientation,1-fade,position);paste(im,after.piece_at(target),target,sprites,orientation,fade,position)
  else:paste(im,piece,source,sprites,orientation,position=position)
 return im.convert('RGB')

def svg(case,board,caption,last,orientation):
 esc=html.escape;body=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img"><title>{esc(case["title"])}</title><desc>{esc(caption)}</desc><defs>']
 for p in sorted(ASSETS.glob('*.svg')):
  inner=re.sub(r'^.*?<svg[^>]*>|</svg>\s*$','',p.read_text(),flags=re.S)
  body.append(f'<symbol id="{p.stem}" viewBox="0 0 45 45">{inner}</symbol>')
 body+=['</defs>',f'<rect width="100%" height="100%" fill="{PAPER}"/>']
 def text(x,y,value,size=17,color=INK):body.append(f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" fill="{color}">{esc(value)}</text>')
 text(MARGIN,45,case['title'],25);text(MARGIN,76,case.get('subtitle',''),16,'#496357')
 for sq in chess.SQUARES:
  x,y=xy(sq,orientation);color=LIGHT if (chess.square_file(sq)+chess.square_rank(sq))%2 else DARK;body.append(f'<rect x="{x}" y="{y}" width="{SQUARE}" height="{SQUARE}" fill="{color}"/>')
 if last:
  for sq in (last.from_square,last.to_square):x,y=xy(sq,orientation);body.append(f'<rect x="{x}" y="{y}" width="{SQUARE}" height="{SQUARE}" fill="#d9b25f" fill-opacity=".42"/>')
 for sq,p in board.piece_map().items():x,y=xy(sq,orientation);body.append(f'<use xlink:href="#{key(p)}" x="{x}" y="{y}" width="{SQUARE}" height="{SQUARE}"/>')
 for i in range(8):
  text(MARGIN+i*SQUARE+35,TOP+BOARD+18,'abcdefgh'[i if orientation=='white' else 7-i],13,'#557064');text(7,TOP+i*SQUARE+46,str(8-i if orientation=='white' else i+1),13,'#557064')
 text(MARGIN,TOP+BOARD+44,case.get('line_label','Illustrative continuation; replies are not forced.'),14,'#557064')
 for i,line in enumerate(textwrap.wrap(caption,76)[:3]):text(MARGIN,TOP+BOARD+73+i*21,line)
 text(MARGIN,HEIGHT-12,'Mute Chess Moss board · Cburnett pieces · Study illustration',12,'#557064');body.append('</svg>');return ''.join(body)

def render(case,formats,output):
 started=time.monotonic()
 moves,states,sans=state(case);assert len(moves)<=8,'Study export limited to eight plies per animation';orientation=case.get('orientation','white');captions=case.get('captions',sans);output.mkdir(parents=True,exist_ok=True)
 if 'svg' in formats:(output/(case['id']+'.svg')).write_text(svg(case,states[-1],captions[-1],moves[-1],orientation))
 if any(x in formats for x in ('png','gif')):
  sprites=pieces()
  if 'png' in formats:still(case,states[-1],captions[-1],moves[-1],sprites,orientation).save(output/(case['id']+'.png'))
  if 'gif' in formats:
   frames=[still(case,states[0],case.get('initial_caption','Position before the move.'),None,sprites,orientation)];durations=[1100]
   for i,move in enumerate(moves):
    for k in range(1,9):frames.append(motion(case,states[i],states[i+1],move,captions[i],k/8,sprites,orientation));durations.append(30)
    frames.append(still(case,states[i+1],captions[i],move,sprites,orientation));durations.append(1300 if i==len(moves)-1 else 850)
   # One palette across the full animation prevents flashing square/piece colors.
   sample=Image.new('RGB',(WIDTH,HEIGHT*3))
   for j,i in enumerate((0,len(frames)//2,len(frames)-1)):sample.paste(frames[i],(0,HEIGHT*j))
   palette=sample.quantize(colors=248,method=Image.Quantize.MEDIANCUT);del sample
   colors=palette.getpalette()
   blended=[Image.alpha_composite(Image.new('RGBA',(1,1),color),Image.new('RGBA',(1,1),GOLD)).convert('RGB').getpixel((0,0)) for color in (LIGHT,DARK)]
   exact=[tuple(bytes.fromhex(color[1:])) for color in (LIGHT,DARK,PAPER,INK,'#ffffff','#000000')]+blended
   for j,color in enumerate(exact):colors[(248+j)*3:(249+j)*3]=list(color)
   palette.putpalette(colors)
   for i in range(len(frames)):
    source=frames[i];mapped=source.quantize(palette=palette,dither=Image.Dither.NONE)
    # Pillow's approximate RGB lookup can miss an exact palette entry. Preserve
    # native flat squares, highlights, paper, and piece fills explicitly.
    for j,color in enumerate(exact):
     bands=ImageChops.difference(source,Image.new('RGB',source.size,color)).split()
     mask=ImageChops.lighter(ImageChops.lighter(bands[0],bands[1]),bands[2]).point(lambda value:255 if value==0 else 0)
     mapped.paste(248+j,(0,0,WIDTH,HEIGHT),mask)
    frames[i]=mapped
   del source,mapped,mask,bands
   frames[0].save(output/(case['id']+'.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False,disposal=2)
   del frames,palette
 result={'case':case['id'],'formats':formats,'positions':len(states),'all_moves_legal':True,'elapsed_seconds':round(time.monotonic()-started,3),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),'outputs':[{'path':case['id']+'.'+kind,'bytes':(output/(case['id']+'.'+kind)).stat().st_size} for kind in formats]}
 (output/(case['id']+'-render.json')).write_text(json.dumps(result,indent=2)+'\n')
 return result

def comparison(cases,output):
 sprites=pieces();panels=[]
 for original in cases:
  case=dict(original);moves,states,sans=state(case)
  case['title']='Chess.com: '+case['label'];case['subtitle']=('14...Ndxe5' if case['id']=='pawn-win-excellent' else '9...Nxd5')+' · a knight is offered'
  caption=case['captions'][0]
  panels.append(still(case,states[1],caption,moves[0],sprites,case.get('orientation','black')))
 image=Image.new('RGB',(WIDTH*2,HEIGHT+88),PAPER);draw=ImageDraw.Draw(image)
 draw.text((MARGIN,18),'Similar material trades, different labels',font=font(28),fill=INK)
 draw.text((MARGIN,55),'Both conditional continuations finish one pawn ahead. Supplemental examples outside the benchmark.',font=font(17),fill='#496357')
 for i,panel in enumerate(panels):image.paste(panel,(i*WIDTH,88))
 output.mkdir(parents=True,exist_ok=True);path=output/'similar-trades-native.png';image.save(path)
 return {'output':path.name,'bytes':path.stat().st_size,'all_moves_legal':True}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=Path,default=ROOT/'cases.json');p.add_argument('--case');p.add_argument('--comparison',action='store_true');p.add_argument('--formats',default='png,svg');p.add_argument('--output',type=Path,default=ROOT/'outputs');p.add_argument('--resvg',type=Path,default=RESVG);args=p.parse_args();RESVG=args.resvg;cases=json.loads(args.cases.read_text())
 if args.comparison:
  chosen=[next(c for c in cases if c['id']==key) for key in ('pawn-win-excellent','pawn-win-brilliant')];print(json.dumps(comparison(chosen,args.output)))
 else:
  if not args.case:p.error('--case is required unless --comparison is supplied')
  case=next(x for x in cases if x['id']==args.case);formats=args.formats.split(',');assert set(formats)<={'png','gif','svg'};print(json.dumps(render(case,formats,args.output)))
