#!/bin/bash
# Schedule Daily AGI Possible at 8am PST (16:00 UTC)
# PST = UTC-8. So 8am PST = 16:00 UTC

SCRIPT_DIR="$HOME/agi-possible-agent"
PYTHON="/usr/bin/python3"
LOG="$SCRIPT_DIR/logs/agent.log"

mkdir -p "$SCRIPT_DIR/logs"

# Remove old entry if exists
crontab -l 2>/dev/null | grep -v "agi-possible-agent" | crontab -

# Add: 8am PST = 16:00 UTC every day
(crontab -l 2>/dev/null; echo "0 16 * * * cd $SCRIPT_DIR && $PYTHON $SCRIPT_DIR/agent.py >> $LOG 2>&1") | crontab -

echo "Daily AGI Possible scheduled for 8:00 AM PST (16:00 UTC) daily"
echo "  Log: $LOG"
crontab -l | grep agi-possible
