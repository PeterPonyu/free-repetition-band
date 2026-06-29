#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
os.environ.setdefault('NUMEXPR_NUM_THREADS','2')
ROOT=Path('/home/zeyufu/Desktop/dl-research')
EXP=ROOT/'experiments/repeated_data'
OUT=ROOT/'experiments/results/repeated_data_ultragoal_seed_audit'
if str(EXP) in sys.path: sys.path.remove(str(EXP))
sys.path.insert(0,str(EXP))
from train_repeat import Config, run  # noqa:E402
try:
 import torch # noqa:E402
 torch.set_num_threads(2); torch.set_num_interop_threads(1)
except Exception: pass

def tag_u(U:int)->str: return f"{U/1e6:g}M".replace('.','p')
def done(p:Path)->bool:
 if not p.exists(): return False
 last=''
 for line in p.open():
  if line.strip(): last=line
 try: return '_summary' in json.loads(last)
 except Exception: return False

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--entropy', choices=['low','med'], required=True)
 ap.add_argument('--unique-tokens', type=int, required=True)
 ap.add_argument('--seed', type=int, required=True)
 args=ap.parse_args()
 E=max(1, round(20_000_000/args.unique_tokens))
 name=f"small_{args.entropy}_U{tag_u(args.unique_tokens)}_E{E}_s{args.seed}"
 OUT.mkdir(parents=True, exist_ok=True)
 path=OUT/f"{name}.jsonl"
 if done(path):
  print(json.dumps({'status':'skip','path':str(path)}), flush=True); return 0
 if path.exists(): path.unlink()
 cfg=Config(capacity='small', entropy_level=args.entropy, generator='markov', unique_tokens=args.unique_tokens,
            n_epochs=E, total_budget=20_000_000, seed=args.seed)
 s,_=run(cfg, out_path=str(path))
 print(json.dumps({'status':'done','name':name,'path':str(path),'entropy':args.entropy,
                   'unique_tokens':args.unique_tokens,'n_epochs':E,'seed':args.seed,
                   'final_val_loss':s['final_val_loss'],'final_canary_gap':s['final_canary_gap'],
                   'elapsed_sec':s['elapsed_sec']}), flush=True)
 return 0
if __name__=='__main__': raise SystemExit(main())
