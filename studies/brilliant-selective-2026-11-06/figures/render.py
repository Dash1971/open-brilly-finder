# SPDX-License-Identifier: AGPL-3.0-only
"""Render the fixed Witty comparison; counts come from the completed result."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1]
d=json.loads((P/'data/fresh-results.json').read_text())['counts']['primary']
keys=['production','pr285','selective'];labels=['Older Mute Selective','Older forest + complete confirmation','Updated Mute Selective']
colors=['#9ba9a3','#688779','#8fc7ad'];fig,axes=plt.subplots(1,2,figsize=(14,4.9),gridspec_kw={'wspace':.35})
for ax,field,limit,title,denom in [(axes[0],'TP',1234,'Chess.com Brilliants recognized',1234),(axes[1],'FP',70,'Extra Brilliant awards',30423)]:
 for i,(key,color) in enumerate(zip(keys,colors)):
  n=d[key][field];ax.barh(i,n,color=color,height=.56);ax.text(n+limit*.018,i,f'{n:,} / {denom:,}',va='center',fontsize=11,color='#19352c')
 ax.set_yticks(range(3),labels if field=='TP' else ['']*3);ax.invert_yaxis();ax.set_xlim(0,limit*1.19);ax.set_title(title,loc='left',fontsize=15,pad=15,color='#19352c');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
 ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0,labelsize=10);ax.set_xlabel('Count (different scales)',color='#46554f')
fig.suptitle('More Brilliants, fewer extra badges',x=.04,ha='left',fontsize=21,color='#19352c',weight='bold')
fig.text(.04,.025,'Same 1,000 Witty_Alien games · Fixed model · 62.7% recognition · 95.3% of updated badges match Chess.com',fontsize=11,color='#46554f')
fig.subplots_adjust(left=.24,right=.98,bottom=.2,top=.8)
for suffix in ['png','svg']:fig.savefig(P/f'figures/fresh-results.{suffix}',dpi=140,facecolor='white',metadata={'Creator':'Open Brilly Finder'})
