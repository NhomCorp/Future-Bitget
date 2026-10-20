# synthetic sanity: long ladder 3 layers equal, step 1%, TP 0.5%, price 100->98->99.5
import numpy as np, sim
p=np.array([100,100,99,98,98.5,99.0,99.5,99.6]); T=len(p)
O=p[None,:].copy();H=O.copy();L=O.copy();C=O.copy(); ts=np.arange(T,dtype=np.int64)*60000+1
z=np.zeros((1,T)); atr=np.ones((1,T))
par=np.array([3,3,0,1.0,1.0,1.0,0.5,0,2,0,30,1,0,10**6,4],dtype=np.float64)
st,rec,cyc,ct,cd=sim.run(ts,O,H,L,C,atr,C.copy(),z,z,z,z,np.array([0]),np.array([1]),par,100.0,0.0002,0.0006,np.array([0.005]),1)
# manual: each layer 100 USDT: q1=1@100,q2=100/99@99,q3=100/98.01? levels 100,99,98.01 -> filled 100,99 (98>98.01? low 98<=98.01 yes)
q=[1,100/99,100/98.01]; px=[100,99,98.01]; Q=sum(q); A=sum(a*b for a,b in zip(q,px))/Q; tp=A*1.005
fee=0.0002*(300)+0.0002*tp*Q; pn=(tp-A)*Q-fee
print("sim final",st[0],"cycles",cyc,"manual",100+pn, "A",A,"tp",tp)
