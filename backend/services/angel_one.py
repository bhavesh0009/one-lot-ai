import os
import logging
import time
from SmartApi import SmartConnect
import pyotp
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AngelOneService:
    def __init__(self):
        self.api_key = os.getenv("ANGEL_ONE_API_KEY")
        self.client_code = os.getenv("ANGEL_ONE_CLIENT_CODE")
        self.password = os.getenv("ANGEL_ONE_PASSWORD")
        self.totp_secret = os.getenv("ANGEL_ONE_TOTP_SECRET")
        
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.session = None
        self._login()
        
    def _login(self):
        try:
            totp = pyotp.TOTP(self.totp_secret).now()
            data = self.smart_api.generateSession(self.client_code, self.password, totp)
            
            if data['status']:
                self.session = data['data']
                self.auth_token = data['data']['jwtToken']
                self.feed_token = self.smart_api.getfeedToken()
                logger.info("Angel One Login Successful")
            else:
                logger.error(f"Angel One Login Failed: {data['message']}")
                raise Exception(data['message'])
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            raise

    def get_ltp(self, symbol: str, token: str, exchange: str = "NSE"):
        """
        Fetch Last Traded Price.
        """
        try:
            # ltpData expects exchange (NSE, NFO) and tradingsymbol (e.g. RELIANCE-EQ) as PER DOCS
            # BUT request param is named 'symboltoken'.
            
            # Using the method provided by library options
            # data = self.smart_api.ltpData(exchange, symbol, token)
            
            # Correction: ltpData usage
            param = {
                "exchange": exchange,
                "tradingsymbol": symbol,
                "symboltoken": token
            }
            response = self.smart_api.ltpData(exchange, symbol, token)
            
            if response['status']:
                 return response['data']['ltp']
            else:
                 logger.error(f"Failed to fetch LTP: {response['message']}")
                 return None
                 
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}")
            return None

    def _retry_call(self, func, *args, max_retries=1, delay=2, **kwargs):
        """Retry wrapper for API calls that may timeout."""
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries + 1} attempts failed: {e}")
        return None

    def get_market_data_batch(self, tokens: list, exchange: str = "NFO"):
        """
        Fetch market data for multiple tokens with intelligent batching and retry logic.

        Angel One API has rate limiting on /market/v1/quote endpoint.
        This method:
        - Splits tokens into small batches (5 tokens) to avoid quota exhaustion
        - Implements exponential backoff retry for AB1004 errors (rate limit)
        - Adds delays between batches to respect API rate limits

        Args:
            tokens: list of token strings e.g. ["131523", "131524"]
            exchange: "NSE" or "NFO"
        Returns:
            dict keyed by token -> {ltp, oi, volume, ...} or partial dict on partial failure
        """
        if not tokens:
            return {}

        # Split into small batches to avoid rate limit
        # Angel One rate limits after ~20-25 consecutive requests
        batch_size = 5  # Small batch to reduce API quota consumption per request
        batches = [tokens[i:i + batch_size] for i in range(0, len(tokens), batch_size)]

        exchange_key = "NFO" if exchange == "NFO" else "NSE"
        result = {}
        total_batches = len(batches)

        for batch_num, batch in enumerate(batches, 1):
            exchange_tokens = {exchange_key: batch}

            # Implement exponential backoff retry for this batch
            max_retries = 3
            base_delay = 1  # Start with 1 second

            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Batch {batch_num}/{total_batches}: Fetching {len(batch)} tokens (attempt {attempt + 1}/{max_retries + 1})")

                    response = self.smart_api.getMarketData("FULL", exchange_tokens)

                    if response and response.get('status') and response.get('data'):
                        fetched = response['data'].get('fetched', [])
                        unfetched = response['data'].get('unfetched', [])

                        if unfetched:
                            logger.warning(f"Batch {batch_num}: Unfetched {len(unfetched)} tokens: {unfetched}")

                        # Build dict keyed by token
                        for item in fetched:
                            result[item['symbolToken']] = {
                                'ltp': item.get('ltp', 0),
                                'open': item.get('open', 0),
                                'high': item.get('high', 0),
                                'low': item.get('low', 0),
                                'close': item.get('close', 0),
                                'volume': item.get('tradeVolume', 0),
                                'oi': item.get('opnInterest', 0),
                                'oi_change_pct': item.get('oiUpper', 0),
                                'last_trade_qty': item.get('lastTradeQty', 0),
                                'total_buy_qty': item.get('totBuyQuan', 0),
                                'total_sell_qty': item.get('totSellQuan', 0),
                            }

                        logger.info(f"Batch {batch_num}: ✓ Success ({len(fetched)} tokens fetched)")
                        break  # Success, move to next batch

                    elif response and response.get('errorcode') == 'AB1004':
                        # Rate limit error - retry with exponential backoff
                        if attempt < max_retries:
                            wait_time = base_delay * (2 ** attempt)
                            logger.warning(f"Batch {batch_num}: Rate limited (AB1004). Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Batch {batch_num}: Failed after {max_retries + 1} attempts with AB1004")
                    else:
                        # Other error
                        logger.error(f"Batch {batch_num}: Failed with error {response.get('errorcode')}: {response.get('message')}")
                        break

                except Exception as e:
                    if attempt < max_retries:
                        wait_time = base_delay * (2 ** attempt)
                        logger.warning(f"Batch {batch_num}: Exception: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Batch {batch_num}: Exception after {max_retries + 1} attempts: {e}")
                        break

            # Add delay between batches to respect rate limits
            if batch_num < total_batches:
                time.sleep(0.3)  # Small delay between batches

        logger.info(f"Batch market data complete: {len(result)}/{len(tokens)} tokens fetched successfully")
        return result

    def get_option_greeks(self, name: str, expiry: str):
        """
        Fetch Option Greeks (IV, Delta, Gamma, Theta, Vega) for all strikes.
        
        Args:
            name: underlying symbol e.g. "RELIANCE"
            expiry: expiry string e.g. "24FEB2026"
        Returns:
            dict keyed by (strike, type) -> {iv, delta, gamma, theta, vega}
        """
        try:
            params = {
                "name": name,
                "expirydate": expiry
            }
            response = self._retry_call(self.smart_api.optionGreek, params)
            
            if response and response.get('status') and response.get('data'):
                greeks_map = {}
                for item in response['data']:
                    # API returns strikePrice as string in RUPEES e.g. "1500.000000"
                    try:
                        strike_rupees = float(item.get('strikePrice', 0))
                    except (ValueError, TypeError):
                        continue
                    opt_type = item.get('optionType', '')
                    key = (strike_rupees, opt_type)
                    greeks_map[key] = {
                        'iv': float(item.get('impliedVolatility', 0)),
                        'delta': float(item.get('delta', 0)),
                        'gamma': float(item.get('gamma', 0)),
                        'theta': float(item.get('theta', 0)),
                        'vega': float(item.get('vega', 0)),
                    }
                return greeks_map
            else:
                logger.warning(f"Option Greeks API returned no data: {response}")
                return {}
                
        except Exception as e:
            logger.error(f"Error fetching option Greeks: {e}")
            return {}

    def get_candle_data(self, token: str, exchange: str, interval: str, from_date: str, to_date: str):
         """
         Fetch historical data.
         """
         try:
             params = {
                 "exchange": exchange,
                 "symboltoken": token,
                 "interval": interval,
                 "fromdate": from_date,
                 "todate": to_date
             }
             response = self.smart_api.getCandleData(params)
             if response['status'] and response['data']:
                 return response['data']
             return []
         except Exception as e:
             logger.error(f"Error fetching candle data: {e}")
             return []

# Singleton
# Singleton
try:
    angel_service = AngelOneService()
except Exception as e:
    logger.error(f"AngelOneService init failed: {e}")
    angel_service = None
