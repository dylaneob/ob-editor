"""Entry point for the level kit: python3 -I ~/ob-editor/level-kit/lk.py STEP PLAN [args] (steps: levelkit/pipeline.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from levelkit.pipeline import main

if __name__ == "__main__":
    main(sys.argv[1:])
