#!/usr/bin/env python3
"""Two study-specific panels from the completed frozen test; no fitting/searches."""
from pathlib import Path
import hashlib,json,sys,os
sys.path.insert(0,'/private/tmp/mute-research-plot')
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/mute-research-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'../future-validation-v5/engine-core/fresh-results.json'
COLORS={'moss':'#668478','light':'#C7CFBA','gold':'#D9B25F','ink':'#172723','pale':'#EDF1EA','muted':'#496357'}

def main():
    d=json.loads(SOURCE.read_text());assert d['total_moves']==200 and d['games']==106
    names=[('forest','Mute selective model'),('S','Mute history rule'),('ec_direct','En Croissant')]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(15.8,5.5),dpi=110,sharey=True)
    fig.patch.set_facecolor('white')
    fig.suptitle('Matching Chess.com’s Brilliant badges',x=.035,y=.965,ha='left',fontsize=21,color=COLORS['ink'],weight='bold')
    fig.text(.035,.885,'200 moves · 106 games · 100 observed Brilliant + 100 explicitly non-Brilliant',fontsize=12,color=COLORS['muted'])
    audit=[]
    for ax,kind,title,color in zip(axes,['positive','negative'],['Brilliants recognized','Extra awards on comparison moves'],[COLORS['moss'],COLORS['gold']]):
        for i,(key,label) in enumerate(names):
            m=d['overall'][key];n=m['TP']+m['FN'] if kind=='positive' else m['FP']+m['TN'];value=m['TP'] if kind=='positive' else m['FP'];assert n==100
            ax.barh(i,n,color=COLORS['pale'],height=.48,zorder=1)
            ax.barh(i,value,color=color,height=.48,zorder=2,edgecolor=COLORS['ink'] if kind=='negative' else color,linewidth=.7)
            text_x=value+(.22 if kind=='negative' else 2);ax.text(text_x,i,f'{value} / {n}',va='center',color=COLORS['ink'],fontsize=13,weight='bold')
            audit.append({'classifier':key,'panel':kind,'count':value,'denominator':n})
        ax.set_title(title,loc='left',pad=24,fontsize=15,color=COLORS['ink'],weight='bold')
        ax.set_xlim(0,10 if kind=='negative' else 100);ax.set_ylim(2.65,-.65)
        ticks=[0,2,4,6,8,10] if kind=='negative' else [0,25,50,75,100]
        ax.set_xticks(ticks,labels=[str(x) for x in ticks])
        ax.set_xlabel('Extra awards out of 100 comparison moves' if kind=='negative' else 'Recognized out of 100 Brilliant moves',labelpad=10,color=COLORS['muted'])
        ax.set_yticks(range(3),labels=[label for _,label in names]);ax.tick_params(axis='both',length=0,labelcolor=COLORS['ink'],pad=10)
        ax.grid(axis='x',color='#DBE3DB',linewidth=.7,zorder=0);ax.set_axisbelow(True)
        for spine in ax.spines.values():spine.set_visible(False)
    axes[1].tick_params(labelleft=False)
    fig.text(.98,.835,'Panels use different scales: left 0–100, right 0–10.',ha='right',fontsize=10,color=COLORS['muted'])
    fig.text(.035,.065,'55% recognized · 1 extra award / 100 controls · 98.2% sample badge precision · 77% overall agreement',fontsize=12,color=COLORS['ink'],weight='bold')
    fig.text(.035,.023,'Balanced, challenging sample. These rates do not establish ordinary-game badge frequency or deployment precision.',fontsize=10,color=COLORS['muted'])
    fig.subplots_adjust(left=.18,right=.98,top=.73,bottom=.22,wspace=.28)
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    for ext in ('png','svg'):fig.savefig(out/f'fresh-test-results.{ext}',facecolor='white',dpi=110)
    plt.close(fig)
    (out/'fresh-test-results-audit.json').write_text(json.dumps({'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'plotted_counts':audit,'native_colors':COLORS},indent=2)+'\n')

if __name__=='__main__':main()
