#!/usr/bin/env python3
"""Two study-specific panels from the completed frozen test; no fitting/searches."""
from pathlib import Path
import hashlib,json,sys,os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/mute-research-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'data/test-results.json'
COLORS={'moss':'#668478','light':'#C7CFBA','gold':'#D9B25F','ink':'#172723','pale':'#EDF1EA','muted':'#496357'}

def render(names,filename,heading,footer,retrospective=False):
    source=ROOT/'data/history-recovery-results.json' if retrospective else SOURCE
    d=json.loads(source.read_text())
    if retrospective:
        rows=json.loads((ROOT/'moves.json').read_text());ec={'TP':0,'FN':0,'FP':0,'TN':0}
        for row in rows:
            assert isinstance(row['ec_direct_award'],bool) and isinstance(row['is_brilliant'],bool)
            ec[('TP' if row['ec_direct_award'] else 'FN') if row['is_brilliant'] else ('FP' if row['ec_direct_award'] else 'TN')]+=1
        assert len(rows)==1048 and len(d['rows'])==1048 and d['removed_true']==0 and d['removed_false']==2
        d={'overall':{'refined':d['refined_retrospective_counts'],'ec_direct':ec}}
    else:assert d['total_moves']==200 and d['games']==106
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(15.8,5.5),dpi=110,sharey=True)
    fig.patch.set_facecolor('white')
    fig.suptitle(heading,x=.035,y=.965,ha='left',fontsize=21,color=COLORS['ink'],weight='bold')
    fig.text(.035,.885,'1,048 studied moves · 545 games · 5 accounts' if retrospective else '200 moves · 106 games · 100 observed Brilliant + 100 explicitly non-Brilliant',fontsize=12,color=COLORS['muted'])
    audit=[]
    for ax,kind,title,color in zip(axes,['positive','negative'],['Brilliants recognized','Extra awards on comparison moves'],[COLORS['moss'],COLORS['gold']]):
        for i,(key,label) in enumerate(names):
            m=d['overall'][key];n=m['TP']+m['FN'] if kind=='positive' else m['FP']+m['TN'];value=m['TP'] if kind=='positive' else m['FP'];assert n==(513 if kind=='positive' else 535) if retrospective else n==100
            ax.barh(i,n,color=COLORS['pale'],height=.48,zorder=1)
            ax.barh(i,value,color=color,height=.48,zorder=2,edgecolor=COLORS['ink'] if kind=='negative' else color,linewidth=.7)
            text_x=value+(.6 if retrospective and kind=='negative' else 5 if retrospective else .22 if kind=='negative' else 2);ax.text(text_x,i,f'{value} / {n}',va='center',color=COLORS['ink'],fontsize=13,weight='bold')
            audit.append({'classifier':key,'panel':kind,'count':value,'denominator':n})
        ax.set_title(title,loc='left',pad=24,fontsize=15,color=COLORS['ink'],weight='bold')
        ax.set_xlim(0,(30 if kind=='negative' else 513) if retrospective else (10 if kind=='negative' else 100));ax.set_ylim(len(names)-.35,-.65)
        ticks=([0,10,20,30] if kind=='negative' else [0,100,200,300,400,513]) if retrospective else ([0,2,4,6,8,10] if kind=='negative' else [0,25,50,75,100])
        ax.set_xticks(ticks,labels=[str(x) for x in ticks])
        ax.set_xlabel(('Extra awards out of 535 comparison moves' if kind=='negative' else 'Recognized out of 513 Brilliant moves') if retrospective else ('Extra awards out of 100 comparison moves' if kind=='negative' else 'Recognized out of 100 Brilliant moves'),labelpad=10,color=COLORS['muted'])
        ax.set_yticks(range(len(names)),labels=[label for _,label in names]);ax.tick_params(axis='both',length=0,labelcolor=COLORS['ink'],pad=10)
        ax.grid(axis='x',color='#DBE3DB',linewidth=.7,zorder=0);ax.set_axisbelow(True)
        for spine in ax.spines.values():spine.set_visible(False)
    axes[1].tick_params(labelleft=False)
    fig.text(.98,.835,'Different scales: left 0–513, right 0–30.' if retrospective else 'Panels use different scales: left 0–100, right 0–10.',ha='right',fontsize=10,color=COLORS['muted'])
    fig.text(.035,.065,footer,fontsize=12,color=COLORS['ink'],weight='bold')
    fig.text(.035,.023,'Comparison on studied examples; sampling and validation in Methods.' if retrospective else 'Balanced, challenging sample. These rates do not establish ordinary-game badge frequency or deployment precision.',fontsize=10,color=COLORS['muted'])
    fig.subplots_adjust(left=.18,right=.98,top=.73,bottom=.22,wspace=.28)
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    for ext in ('png','svg'):fig.savefig(out/f'{filename}.{ext}',facecolor='white',dpi=110)
    plt.close(fig)
    (out/f'{filename}-audit.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'plotted_counts':audit,'native_colors':COLORS},indent=2)+'\n')


def render_current():
    source=ROOT/'data/selective-independent-tests.json'
    d=json.loads(source.read_text());assert d['cohorts']['all400']['moves']==400
    fig,axes=plt.subplots(2,2,figsize=(15.8,8.4),dpi=110)
    fig.patch.set_facecolor('white')
    fig.suptitle('How closely do the badges match Chess.com?',x=.035,y=.98,ha='left',fontsize=21,color=COLORS['ink'],weight='bold')
    fig.text(.035,.927,'400 test moves · 215 games · 5 accounts',fontsize=12,color=COLORS['muted'])
    audit=[]
    for row,(cohort,label) in enumerate([('all400','400 test moves'),('new200','Same 200-move comparison')]):
        g=d['cohorts'][cohort]
        for col,(kind,title,color) in enumerate([('positive','Brilliants correctly recognized',COLORS['moss']),('negative','Undeserved Brilliant badges',COLORS['gold'])]):
            ax=axes[row,col];n=g['positive'] if kind=='positive' else g['negative'];limit=n if col==0 else 10
            for i,(key,name) in enumerate([('selective','Mute Selective'),('ec_direct','En Croissant')]):
                count=g['counts'][key]['TP' if kind=='positive' else 'FP']
                ax.barh(i,limit,color=COLORS['pale'],height=.45)
                ax.barh(i,count,color=color,height=.45,edgecolor=COLORS['ink']if col else color,linewidth=.7)
                ax.text(count+limit*.02,i,f'{count} / {n}',va='center',fontsize=12,color=COLORS['ink'],weight='bold')
                audit.append({'sample':cohort,'classifier':key,'panel':kind,'count':count,'denominator':n})
            ax.set_title(label+' · '+title,loc='left',fontsize=12,pad=15,color=COLORS['ink'],weight='bold')
            ax.set_ylim(1.6,-.6);ax.set_xlim(0,limit);ax.set_yticks([0,1],labels=['Mute Selective','En Croissant']if col==0 else ['',''])
            ax.set_xlabel(f'Out of {n} '+('Chess.com Brilliants'if col==0 else 'non-Brilliant moves'),color=COLORS['muted'],labelpad=7)
            ax.tick_params(length=0,labelcolor=COLORS['ink'],pad=8);ax.grid(axis='x',color='#DBE3DB',linewidth=.7);ax.set_axisbelow(True)
            for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.035,.067,'Across 400 test moves: 112 Brilliants recognized; 3 undeserved badges. Model and threshold unchanged.',fontsize=12,color=COLORS['ink'],weight='bold')
    fig.text(.035,.025,'These games were not used to train the model. Balanced selected samples; sampling and validation in Methods.',fontsize=10,color=COLORS['muted'])
    fig.subplots_adjust(left=.15,right=.98,top=.845,bottom=.17,hspace=.68,wspace=.30)
    for ext in ['png','svg']:fig.savefig(ROOT/'figures'/f'history-recovery-replay.{ext}',facecolor='white',dpi=110)
    svg=ROOT/'figures/history-recovery-replay.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)
    (ROOT/'figures/history-recovery-replay-audit.json').write_text(json.dumps({'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'plotted_counts':audit,'scope':'Two independent fixed-model tests; no training-fit, History Rule, native or panel results pooled.'},indent=2)+'\n')

if __name__=='__main__':render_current()
