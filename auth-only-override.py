"""
Temporary override to run 100% AUTH, 0% MONITORING for critical hot path testing.
Import this before running the test.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.defaults import TrafficMix

# Monkey-patch TrafficMix to force 100% AUTH
original_init = TrafficMix.__init__

def auth_only_init(self, preauth=1.0, postauth=0.0):
    original_init(self, preauth=preauth, postauth=postauth)

TrafficMix.__init__ = auth_only_init

print("🎯 AUTH-ONLY MODE: 100% AUTH, 0% MONITORING")
