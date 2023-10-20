import sys
from logging import getLevelName, INFO

from .lib import BtLamp

if (len(sys.argv) < 3):
    print("Use: python bt_lamp command lamp-name [level] [log-level]")
    print("   command: setup, on, off, cold, warm, dual")
    print("   lamp-name: name of the lamp")
    print("   level: brightness level, number from 1 to 10. Apply with command cold, warm or dual")
    print("   log-level: Logging level. Need INFO or DEBUG. Default value INFO")
else:    
    command = sys.argv[1]
    name = sys.argv[2]
    if len(sys.argv) > 3:
        level = int(sys.argv[3])
    else:
        level = None

    if len(sys.argv) > 4:
        log_level = getLevelName(sys.argv[4])
    else:
        log_level = INFO

    lamp = BtLamp(name, log_level)
    if command == "setup":
        lamp.setup()
    elif command == "on":
        lamp.on()
    elif command == "off":
        lamp.off()
    elif command == "cold":
        lamp.cold(level)
    elif command == "warm":
        lamp.warm(level)
    elif command == "dual":
        lamp.dual(level)

    print("Command {0} executed on {1} with arg {2}".format(command, name, level))