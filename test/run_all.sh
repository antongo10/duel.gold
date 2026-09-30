#!/bin/bash
cd /home/claude/duel-gold/test
run(){ timeout 1500 python3 test_$1.py > logs/$1.final.log 2>&1; echo "EXIT $?" >> logs/$1.final.log; }
run platform & run social & run brain & wait
run strategy & run builder & wait
run reflex
echo ALLDONE > logs/final.done
