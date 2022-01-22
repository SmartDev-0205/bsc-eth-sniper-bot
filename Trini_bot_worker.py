import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal


class Worker(QObject):
    is_running = False

    finished = pyqtSignal()
    progress = pyqtSignal(dict)
    progress_msg = pyqtSignal(str)
    progress_price = pyqtSignal(float)
    progress_balance = pyqtSignal()
    progress_token_balance = pyqtSignal()

    def __init__(
            self,
            wallet,
            w3_wss,
            target_token,
            presale_address,
            presale_id,
            buy_only,
            sell_only,
            eth,
            speed,
            sell_speed,
            gas_limit,
            slippage,
            stop_loss_check,
            sell_price_limit_flag,
            sell_price_limit_p_flag,
            sell_price_limit,
            sell_price_limit_p,
            buy_price_limit_flag,
            buy_price_limit_p_flag,
            buy_price_limit,
            buy_price_limit_p,
            stop_loss,
            token_decimal,
            split,
            delay,
            liquidity_flag,
            liquidity_amount,
            sniper_flag,
            contribute_flag,
            trini_level
    ):
        super().__init__()

        self.token_found = False
        self.wallet = wallet
        self.w3 = wallet.web3
        self.w3_wss = w3_wss
        self.target_token = target_token
        self.presale_address = presale_address.lower()
        self.presale_id = presale_id

        # print(self.sale_address)
        self.buy_only = buy_only
        self.sell_only = sell_only
        self.eth = eth


        self.stop_loss_check = stop_loss_check

        self.buy_amount = 0
        self.buy_amount_p = 0
        self.sell_amount = 0
        self.sell_amount_p = 100
        self.speed = speed
        self.sell_speed = sell_speed
        self.gas_limit = gas_limit
        self.slippage = slippage
        self.sell_price_limit_flag = sell_price_limit_flag


        self.sell_price_limit_p_flag = sell_price_limit_p_flag
        self.sell_price_limit = sell_price_limit

        self.sell_price_limit_p = sell_price_limit_p
        self.buy_price_limit_flag = buy_price_limit_flag
        self.buy_price_limit_p_flag = buy_price_limit_p_flag
        self.buy_price_limit = buy_price_limit
        self.buy_price_limit_p = buy_price_limit_p
        self.stop_loss = stop_loss
        self.split = split
        self.delay = delay
        self.liquidity_flag = liquidity_flag
        self.liquidity_amount = liquidity_amount
        self.sniper_flag = sniper_flag
        self.contribute_flag = contribute_flag
        self.trini_level = trini_level
        self.sell_amount = 0
        self.liquidity_transaction = None
        self.current_price = 0

        self.token_balance = 0
        self.buy_flag = False
        self.buy_price = 0

        self.sell_flag = False
        self.sell_price = 0

        self.liquidity_add_methods = ['0xf305d719', '0xe8e33700', '0x384e03db', '0x4515cef3', '0x267dd102', '0xe8078d94','0xfe8121de']

        self.market_buy_flag = False
        self.market_sell_flag = False

        self.token_decimal = token_decimal

        self.lock_filter = False
        self.sign_tx = []
        self.wallet.set_gas_limit(self.gas_limit)
        self.dxsale_address = "0xbaCEbAd5993a19c7188Db1cC8D0F748C9Af1689A"
        self.presale_owner = ""
        try:
            self.presale_owner = self.wallet.get_presale_owner(presale_address=self.dxsale_address,presale_id=int(self.presale_id))
        except:
            pass
        print(f"Presale Owner : {self.presale_owner}")
    def set_amounts(self, ba, sap):
        self.buy_amount = ba
        self.sell_amount_p = sap
        self.token_balance = self.wallet.balance()
        num = 0
        while num < self.split:
            self.sign_tx.append(self.wallet.buy(int(self.buy_amount/self.split), slippage=float(self.slippage / 100),
                                       speed=int(self.speed), timeout=2100, nonce=num))
            num += 1

        # ------------------------------Search MemPool----------------------------------------------------------------------

    def mempool(self):
        self.progress_msg.emit('Waiting liquidity to be added')
        event_filter = self.wallet.web3.eth.filter("pending")
        while not self.token_found and self.is_running:
            try:
                threading.Thread(target=self.get_event, args=(event_filter,)).start()
            except Exception as err:
                pass

    def get_event(self, event_filter):
        new_entries = event_filter.get_new_entries()
        for event in new_entries[::-1]:
            try:
                threading.Thread(target=self.handle_event, args=(event,)).start()
            except Exception as e:
                pass

    def handle_event(self, event):
        try:
            transaction = self.wallet.web3.eth.getTransaction(event)
            address_to = transaction.to
            address_from = transaction["from"]
            if self.presale_owner.lower() == address_from.lower() and self.dxsale_address.lower() == address_to.lower():
                self.detect_event(event)
            elif transaction.input[:10].lower() == "0x267dd102" and address_to.lower() == self.dxsale_address.lower():
                self.detect_event(event)
            elif transaction.input[:10].lower() in self.liquidity_add_methods and self.target_token[
                                                                                  2:].lower() in transaction.input.lower():
                self.detect_event(event)
        except Exception as e:
            pass

    def detect_event(self, event):
        threading.Thread(target=self.market_buy).start()
        self.token_found = True
        self.progress_msg.emit("Liquidity Added : {}".format(event.hex())).start()
        self.progress_msg.emit('Start Buy')

    # -------------------------------Buy functions----------------------------------------------------------------------
    def wait_buy(self):
        start_price = self.wallet.price(10 ** self.token_decimal)
        self.progress_msg.emit(
            f'Start Price:{round((start_price) /(10**18), 12)}BNB')
        while self.is_running and not self.market_buy_flag and not self.market_buy_flag:
            try:
                current_price = self.wallet.price(10 ** self.token_decimal)
                # self.progress_price.emit(current_price/(10**18))
                self.progress_msg.emit(
                    f'Current Price:{round((current_price / start_price) * 100, 5)}%')
                if (current_price <= self.buy_price_limit*(10**self.token_decimal) and self.buy_price_limit_flag) or (current_price <= start_price*self.buy_price_limit_p/100 and self.buy_price_limit_p_flag):
                    self.market_buy()
                    break
            except Exception as e:
                self.progress_msg("This token is not be launched yet.")
                pass
                # self.progress_price.emit(0)
                # print(e)
            time.sleep(1)

    def market_buy(self):
        # self.progress_msg.emit('Start Buy')
        # if self.liquidity_flag:
        #     liquidty_amount_default = self.decode_tx(self.liquidity_transaction)
        #     if self.liquidity_amount > liquidty_amount_default:
        #         self.progress_msg.emit(f'This liquidity amount is too low to buy!,Liquidity amount : {liquidty_amount_default}')
        #         return
        #     else:
        #         self.progress_msg.emit(
        #             f'This liquidity amount : {liquidty_amount_default}')
        num = 0
        while num < self.split:
            try:
                threading.Thread(target=self.buy_thread, args=(num, )).start()
            except Exception as e:
                self.progress_msg.emit('Buy Error')
                print('Buy error:', e)
            num += 1
        # self.progress_msg.emit("Waiting Until Buy Confirm")
        balance = self.wallet.balance()
        currenct_balanc = 0
        while balance < currenct_balanc:
            currenct_balanc = self.wallet.balance()

        self.buy_confirm()

    def buy_thread(self, num):
        self.market_buy_flag = True
        try:
            time.sleep(self.delay)
            result = self.wallet.send_buy_transaction(self.sign_tx[num])
            self.progress_msg.emit(f'Buy transaction: {result.hex()}')
        except Exception as e:
            self.progress_msg.emit(f'Buy error: {e}')
            self.progress_msg.emit(f'Retry ...')
            self.market_buy_flag = False
            print(f'Buy error: {e}')

    def buy_confirm(self):
        retry = 1
        # wait max 5 mins
        while retry < 300:
            current_balance = self.wallet.balance()
            if current_balance > self.token_balance:
                self.progress_balance.emit()
                self.progress_token_balance.emit()
                self.progress_msg.emit("Buy transaction confirmed")
                self.buy_price = self.wallet.price(10 ** self.token_decimal)
                self.progress.emit({'buy_price': self.buy_price})
                # approve
                self.token_balance = self.wallet.balance()
                self.buy_flag = True
                self.market_buy_flag = False

                if not self.buy_only:
                    threading.Thread(target=self.wait_sell()).start()
                    break
                else:
                    break
            retry += 1
            time.sleep(1)
        if retry >= 300:
            self.progress_msg.emit("Buy transaction failed")
            self.buy_flag = False
            self.market_buy_flag = False

    # -------------------------------Sell functions---------------------------------------------------------------------
    def wait_sell(self):
        self.progress_msg.emit("Waiting Sell Moment....")
        self.buy_price = self.wallet.price(10**self.token_decimal)
        while self.is_running and not self.market_sell_flag:
            self.current_price = self.wallet.price(10**self.token_decimal)
            # self.progress_price.emit(self.current_price)
            self.progress_msg.emit(
                f'Checking the condition, current price:{round((self.current_price / self.buy_price)*100, 5)}%')
            # sell when price reached to limit

            if (self.sell_price_limit_flag and self.current_price >= self.sell_price_limit*(10**self.token_decimal)) or (self.sell_price_limit_p_flag and self.current_price >= self.buy_price * self.sell_price_limit_p / 100):
                self.market_sell()
                break
            # sell when price downed to percentage
            if self.stop_loss_check:
                if self.current_price <= self.buy_price * self.stop_loss / 100:
                    self.market_sell()
                    break
            time.sleep(0.5)

    def market_sell(self):
        retry = 1
        self.sell_amount = self.token_balance * self.sell_amount_p / 101

        if self.sell_amount > self.token_balance:
            self.progress_msg.emit('Sell Amount is bigger than balance, set to max..')
            self.sell_amount = self.token_balance
        if self.sell_amount < 10 ** (-10) or self.token_balance < 10 ** (-10):
            self.progress_msg.emit('Insufficient Funds')
            self.market_sell_flag = False
            return
        self.progress_msg.emit('Start Sell')
        if self.is_running and not self.market_sell_flag:
            num = 0
            self.market_sell_flag = True
            self.progress_msg.emit('Wait until transaction completed...')
            while num < self.split:
                try:

                    sell_thread = threading.Thread(target=self.sell_thread, args=(num, ))
                    sell_thread.start()
                except Exception as e:
                    self.progress_msg.emit('Sell Error')
                    print('Sell error:', e)
                num += 1

            self.sell_confirm()

    def sell_thread(self, num):
        try:
            result = self.wallet.sell(int(self.sell_amount/self.split), slippage=float(self.slippage / 100),
                                      speed=self.sell_speed, nonce=num)
            self.progress_msg.emit(f'Sell transaction: {result.hex()}')
        except Exception as e:
            self.progress_msg.emit(f'Sell error: {e}')
            self.progress_msg.emit(f'Retry ...')
            print(f'Sell error: {e}')
            self.market_sell_flag = False

    def sell_confirm(self):
        retry = 1
        # wait max 5 mins
        while retry < 300:
            current_balance = self.wallet.balance()
            if current_balance < self.token_balance:
                self.sell_flag = True
                self.sell_price = self.wallet.price(10 ** self.token_decimal)
                self.progress_msg.emit("Sell transaction confirmed")
                self.progress.emit({'sell_price': self.sell_price})
                self.progress_balance.emit()
                self.progress_token_balance.emit()
                break
            retry += 1
            time.sleep(1)
        if retry >= 300:
            self.sell_flag = False
            self.progress_msg.emit("Sell transaction failed")
        self.market_sell_flag = False

    def contribute(self):
        self.progress_msg.emit('Waiting Presale Start')
        event_filter = self.wallet.web3.eth.filter("pending")
        while not self.token_found and self.is_running:
            try:
                new_entries = event_filter.get_new_entries()
            except Exception as err:
                continue
            for event in new_entries[::-1]:
                if not self.is_running:
                    break
                try:
                    transaction = self.wallet.web3_wss.eth.getTransaction(event)
                    address_to = transaction.to.lower()
                except Exception as e:
                    continue
                if address_to == self.presale_address:
                    self.token_found = True
                    # result = self.wallet.contribute(presale=self.presale_address, amount=self.buy_amount)
                    self.progress_msg.emit("Presale Start : {}".format(event.hex()))
                    threading.Thread(target=self.contribute_start)
                    break
            # if self.market_buy_flag:
            #     self.progress_msg.emit('stop liquidity scanning...')
            #     break

    def contribute_start(self):
        self.progress_msg.emit("Contribute Start!")
        while True:
            try:
                result = self.wallet.contribute(presale=self.presale_address, amount=int(self.buy_amount), speed=self.speed)
                self.progress_msg.emit("Contribution Sent!")
                self.progress_msg.emit(f'Transaction:{result.hex()}')
                self.progress_msg.emit('Please verify your contribution was made on DxSale')
                threading.Thread(target=self.wait_presale_end)
                break
            except Exception as e:
                pass

    def wait_presale_end(self):
        balance = 0
        while balance == 0:
            try:
                balance = self.wallet.balance()
            except Exception as err:
                print(err)
            time.sleep(1)
        try:
            self.buy_price = self.wallet.price(10**self.token_decimal)
        except Exception as err:
            print(err)
        self.progress_balance.emit()
        self.progress_token_balance.emit()
        self.progress_msg.emit("Buy transaction confirmed")
        self.progress.emit({'buy_price': self.buy_price})
        # approve
        self.token_balance = self.wallet.balance()
        self.buy_flag = True
        self.market_buy_flag = False
        # if not self.buy_only:
        #     threading.Thread(target=self.wait_sell()).start()
    # -------------------------------Worker Start-----------------------------------------------------------------------
    def run(self):
        if self.is_running:
            self.progress_msg.emit(f"Token Address : {self.target_token}, Presale Address : {self.presale_address}")
            self.progress_msg.emit(f"Buy Amount : {self.buy_amount/(10**18)}, Sell Amount Percent : {self.sell_amount_p}%, "
                                   f"Sell Price : {self.sell_price_limit_p}%, Buy Speed : {self.speed}, Sell Speed : {self.sell_speed}")
            self.token_decimal = self.wallet.decimals()
            if self.sell_only:
                threading.Thread(target=self.wait_sell).start()
            elif not self.token_found and self.sniper_flag:
                threading.Thread(target=self.mempool).start()
            elif not self.sniper_flag and not self.contribute_flag and self.buy_only:
                threading.Thread(target=self.wait_buy).start()
            elif self.contribute_flag and self.trini_level > 2:
                threading.Thread(target=self.contribute_start).start()
            # elif not self.sniper_flag:
            #     while True:
            #         self.progress_price.emit()
            #         if not self.is_running:
            #             break

    # ------------------------------Worker Stop-------------------------------------------------------------------------
    def stop(self):
        self.progress_msg.emit('Stop Bot')
        self.is_running = False

    def start(self):
        self.wallet.set_gas_limit(self.gas_limit)
        self.progress_msg.emit('Start Bot')
        self.is_running = True

    def get_exp_value(self, val):
        return val / pow(10, 18)

    def decode_tx(self, tx_input):
        tx_block_size = 64
        self.tx_method = hex(int(tx_input[:10], 16))
        tx_method_add_liquidity_1 = "0xf305d719"
        tx_method_add_liquidity_2 = "0xe8e33700"

        tx_input = tx_input[10:]

        if self.tx_method == tx_method_add_liquidity_1:
            self.tx_token = hex(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_amount_token_desired = self.get_exp_value(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_amount_token_min = self.get_exp_value(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_amount_token_eth_min = self.get_exp_value(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_to = hex(int('0x' + tx_input[:tx_block_size], 16))
            return self.tx_amount_token_eth_min
        elif self.tx_method == tx_method_add_liquidity_2:
            self.tx_token_a = hex(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_token_b = hex(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_amount_token_a_desired = self.get_exp_value(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_amount_token_b_desired = self.get_exp_value(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_amount_token_a_min = self.get_exp_value(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_amount_token_b_min = self.get_exp_value(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_to = hex(int('0x' + tx_input[:tx_block_size], 16))
            tx_input = tx_input[tx_block_size:]
            self.tx_deadline = hex(int('0x' + tx_input[:tx_block_size], 16))
            return self.tx_amount_token_a_desired
        return 0
