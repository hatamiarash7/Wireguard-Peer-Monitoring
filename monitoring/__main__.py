import signal

from loguru import logger as log

from monitoring import main as monitor

log.debug("[APP] Handle system signals")

signal.signal(signal.SIGINT, monitor._signal_handler)
signal.signal(signal.SIGTERM, monitor._signal_handler)
signal.signal(signal.SIGHUP, monitor._signal_handler)

monitor.main()
