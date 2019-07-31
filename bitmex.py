from bitmex_ws import Bitmex_WS
from exchange import Exchange
from time import sleep
import datetime
from dateutil import parser
import traceback


class Bitmex(Exchange):
    """BitMEX exchange model"""

    MAX_BARS_PER_REQUEST = 750
    BASE_URL = "https://www.bitmex.com/api/v1"
    BARS_URL = "/trade/bucketed?binSize="
    # WS_URL = "wss://testnet.bitmex.com/realtime"
    WS_URL = "wss://www.bitmex.com/realtime"

    TIMESTAMP_FORMAT = '%Y-%m-%d%H:%M:%S.%f'

    def __init__(self, logger):
        super()
        self.logger = logger
        self.name = "BitMEX"
        self.symbols = ["XBTUSD", "ETHUSD"]
        self.channels = ["trade"]  # , "orderBookL2"
        self.api_key = None
        self.api_secret = None
        self.bars = {i: [] for i in self.symbols}

        # connect to websocket
        self.ws = Bitmex_WS(
            self.logger, self.symbols, self.channels, self.WS_URL,
            self.api_key, self.api_secret)
        if self.ws.ws.sock.connected:
            self.logger.debug("Connected to BitMEX websocket")
        else:
            self.logger.debug("Failed to to connect to BitMEX websocket")

        # parse new ticks in first second of each minute
        self.parse_ticks()

    def parse_ticks(self):
        sleep(self.seconds_til_next_minute())
        count = 0
        while self.ws.ws.sock.connected:
            all_ticks = []
            target_minute = datetime.datetime.utcnow().minute - 1
            if datetime.datetime.utcnow().second <= 1:
                if count >= 1:
                    all_ticks = self.ws.get_ticks()
                    # search from end of tick list to find newest ticks first
                    ticks_target_minute = []
                    tcount = 0
                    for i in reversed(all_ticks):
                        try:
                            ts = i['timestamp']
                            if type(ts) is not datetime.datetime:
                                ts = parser.parse(ts)
                        except Exception:
                            self.logger.debug(traceback.format_exc())
                        # scrape prev minutes ticks
                        if ts.minute == target_minute:
                            ticks_target_minute.append(i)
                            ticks_target_minute[tcount]['timestamp'] = ts
                            tcount += 1
                        # store the previous-to-target bar's last
                        # traded price to use as the open price for target bar
                        if ts.minute == target_minute - 1:
                            ticks_target_minute.append(i)
                            ticks_target_minute[tcount]['timestamp'] = ts
                            break
                    ticks_target_minute.reverse()
                    # build bars for each symbol
                    for symbol in self.symbols:
                        ticks = []
                        for i in ticks_target_minute:
                            if i['symbol'] == symbol:
                                ticks.append(i)
                        bar = self.build_OHLCV(ticks, symbol)
                        self.bars[symbol].append(bar)
                        self.logger.debug(bar)
                count += 1
                sleep(self.seconds_til_next_minute())
            sleep(0.05)

    def get_bars(self):
        return self.bars

    def get_bars_in_period(self):
        pass

    def get_first_timestamp(self, instrument: str):
        pass