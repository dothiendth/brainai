#!/bin/bash
sleep 4
if ! pgrep -f zorin_brain.py > /dev/null; then
    nohup /home/lionos/ZorinOptimizer/gui_env/bin/python3 /home/lionos/ZorinOptimizer/zorin_brain.py > /dev/null 2>&1 &
fi
/home/lionos/ZorinOptimizer/gui_env/bin/python3 /home/lionos/ZorinOptimizer/brain_gui.py --minimized > /dev/null 2>&1 &
