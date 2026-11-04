"""Study-only Tree: audited kernel with explicit capacity constants. No I/O."""
class Tree:
    """Existing cart.py weighted-Gini kernel; fixed forest/minleaf modifications."""
    def __init__(self,X,y,ids,w,names,groups,rng,max_depth=6,minleaf=8,mtry=12):
        self.X,self.y,self.ids,self.w,self.names,self.groups,self.rng=X,y,ids,w,names,groups,rng
        self.max_depth,self.minleaf,self.mtry=max_depth,minleaf,mtry
    def leaf(self,ix):
        positive=self.y[ix]
        return {'kind':'leaf','bootstrap_window_rows':len(ix),'distinct_moves':len(np.unique(self.ids[ix])),
            'distinct_groups':len(np.unique(self.groups[ix])),
            'raw_positive_windows':int(positive.sum()),'raw_negative_windows':int((~positive).sum()),
            'raw_p':float(positive.mean()),'weighted_positive':float(self.w[ix][positive].sum()),
            'weighted_negative':float(self.w[ix][~positive].sum())}
    @staticmethod
    def impurity(p,n):return 2*p*n/(p+n)
    def fit(self,ix,depth=0):
        guard()
        leaf=self.leaf(ix)
        parent=self.impurity(leaf['weighted_positive'],leaf['weighted_negative'])
        if depth>=self.max_depth or leaf['distinct_moves']<2*self.minleaf or parent==0:return leaf
        best=None;bestgain=1e-12
        for feature in self.rng.choice(self.X.shape[1],size=self.mtry,replace=False):
            values=self.X[ix,feature]
            order=np.argsort(np.nan_to_num(values,nan=-np.inf),kind='stable')
            indices=ix[order];v=values[order];n=len(indices)
            if n<2*self.minleaf:continue
            p=np.cumsum(self.w[indices]*self.y[indices]);neg=np.cumsum(self.w[indices]*(~self.y[indices]))
            lp=p[:-1];ln=neg[:-1];rp=p[-1]-lp;rn=neg[-1]-ln
            ids=self.ids[indices]
            _,first=np.unique(ids,return_index=True);_,reverse=np.unique(ids[::-1],return_index=True)
            last=n-1-reverse;marks=np.zeros(n,dtype=int);marks[first]=1;leftcases=np.cumsum(marks)[:-1]
            marks[:]=0;marks[last]=1;rightcases=np.cumsum(marks[::-1])[::-1][1:]
            usable=np.isfinite(v[:-1])&np.isfinite(v[1:])&(v[:-1]<v[1:])&(leftcases>=self.minleaf)&(rightcases>=self.minleaf)
            if not usable.any():continue
            gains=parent-(self.impurity(lp,ln)+self.impurity(rp,rn));gains[~usable]=-np.inf
            j=int(np.argmax(gains));gain=float(gains[j])
            if gain>bestgain:
                bestgain=gain;best=(int(feature),float(v[j]+(v[j+1]-v[j])/2),indices[:j+1],indices[j+1:])
        if best is None:return leaf
        f,threshold,left,right=best
        return {'kind':'split','feature':self.names[f],'feature_index':f,'threshold':threshold,'missing_goes':'left',
            'weighted_gini_gain':bestgain,'support':leaf,'left':self.fit(left,depth+1),'right':self.fit(right,depth+1)}
    def predict(self,model,ix):
        result=np.empty(len(ix))
        for j,row in enumerate(ix):
            node=model
            while node['kind']=='split':
                value=self.X[row,node['feature_index']]
                node=node['left' if np.isnan(value) or value<=node['threshold'] else 'right']
            result[j]=node['raw_p']
        return result
