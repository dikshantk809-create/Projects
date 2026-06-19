"""Generate the system-architecture diagram and workflow flowchart (PNG)."""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from . import config

NAVY="#203a43"; TEAL="#2c5364"; GREEN="#11998e"; RED="#c31432"; GREY="#444a5a"

def _box(ax,x,y,w,h,text,fc,tc="white",fs=11):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.06",
                 fc=fc,ec="white",lw=1.5))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",color=tc,fontsize=fs,fontweight="bold")

def _arrow(ax,x1,y1,x2,y2,color=GREY):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=16,lw=1.6,color=color))

def architecture():
    fig,ax=plt.subplots(figsize=(11,7.6)); ax.set_xlim(0,12); ax.set_ylim(0,11); ax.axis("off")
    ax.text(6,10.5,"TruthLens AI  -  System Architecture",ha="center",fontsize=17,fontweight="bold",color=NAVY)
    _box(ax,3.5,9.0,5,0.9,"User  -  Streamlit Web UI (app.py)",TEAL,fs=12)
    _box(ax,3.0,7.4,6,0.95,"Agent Orchestrator\n(agentic control loop + verdict fusion)",NAVY,fs=11)
    _box(ax,0.4,5.4,3.5,1.1,"ClassifierAgent\npredict P(fake)",GREEN,fs=10.5)
    _box(ax,4.25,5.4,3.5,1.1,"ExplainerAgent\nsignals + LLM",GREEN,fs=10.5)
    _box(ax,8.1,5.4,3.5,1.1,"FactCheckAgent\nRAG retrieval",GREEN,fs=10.5)
    _box(ax,0.4,3.3,3.5,1.1,"ML Model\nTF-IDF + LogReg\n(scikit-learn)",GREY,fs=10)
    _box(ax,4.25,3.3,3.5,1.1,"Credibility Signals\n+ Local LLM (Ollama)\n-> template fallback",GREY,fs=9.5)
    _box(ax,8.1,3.3,3.5,1.1,"RAG Retriever\nFAISS / TF-IDF\nembeddings",GREY,fs=10)
    _box(ax,1.5,1.2,9,1.0,"Data Layer  -  train.csv  -  test.csv  -  knowledge_base.csv  -  model.joblib  -  metrics.json",NAVY,fs=10)
    _arrow(ax,6,9.0,6,8.35)
    for cx in (2.15,6.0,9.85): _arrow(ax,6,7.4,cx,6.5)
    _arrow(ax,2.15,5.4,2.15,4.4); _arrow(ax,6.0,5.4,6.0,4.4); _arrow(ax,9.85,5.4,9.85,4.4)
    for cx in (2.15,6.0,9.85): _arrow(ax,cx,3.3,6,2.2)
    ax.add_patch(FancyArrowPatch((9.0,7.87),(8.5,9.0),arrowstyle="-|>",mutation_scale=16,lw=1.6,color=RED,connectionstyle="arc3,rad=0.3"))
    ax.text(9.8,8.5,"verdict +\ntrace",ha="center",color=RED,fontsize=9,fontweight="bold")
    fig.tight_layout(); fig.savefig(config.IMAGES_DIR/"architecture.png",dpi=140,bbox_inches="tight"); plt.close(fig)

def workflow():
    fig,ax=plt.subplots(figsize=(8.2,11)); ax.set_xlim(0,10); ax.set_ylim(0,15.5); ax.axis("off")
    ax.text(5,15.0,"TruthLens AI  -  Analysis Workflow",ha="center",fontsize=16,fontweight="bold",color=NAVY)
    steps=[("Input: news article / headline",TEAL),
           ("Preprocess & clean text\n(strip URLs/HTML, normalise, tokenise)",GREY),
           ("ClassifierAgent  ->  TF-IDF + LogReg  ->  P(fake)",GREEN),
           ("ExplainerAgent  ->  credibility signals\n+ influential terms + LLM/template",GREEN),
           ("FactCheckAgent  ->  RAG retrieve\ntop-k verified statements",GREEN),
           ("Fuse scores  (0.70 x model  +  0.30 x signal-risk)",NAVY),
           ("Verdict + confidence band\n(High / Medium / Low)",RED),
           ("Display: verdict - agent trace - evidence",TEAL)]
    y=13.3; h=1.15; w=8; x=1; centers=[]
    for txt,fc in steps:
        _box(ax,x,y,w,h,txt,fc,fs=10.5); centers.append(y); y-=1.62
    for i in range(len(centers)-1):
        _arrow(ax,5,centers[i],5,centers[i+1]+h)
    fig.tight_layout(); fig.savefig(config.IMAGES_DIR/"workflow.png",dpi=140,bbox_inches="tight"); plt.close(fig)

def main():
    architecture(); workflow(); print("diagrams written to",config.IMAGES_DIR)

if __name__=="__main__":
    main()
