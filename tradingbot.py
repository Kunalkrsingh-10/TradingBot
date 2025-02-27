# import json
# import asyncio
# import websockets
# import multiprocessing
# import time
# import pandas as pd
# import os
# import logging

# log_filename = f"data/logs/mtslog_{time.strftime('%d%m%Y')}.log"
# logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# class WebSocketProcess(multiprocessing.Process):
#     def __init__(self, brokerconfig, pipe):
#         super().__init__()
#         self.brokerconfig = brokerconfig
#         self.uri = brokerconfig['uri']
#         self.pipe = pipe
#         self.stop_event = multiprocessing.Event()

#     async def handle_websocket(self):
#         retries = 0
#         while not self.stop_event.is_set():
#             try:
#                 logging.info(f"Connecting to WebSocket: {self.uri}")
#                 async with websockets.connect(self.uri) as websocket:
#                     logging.info("Connected")
#                     await websocket.send(json.dumps({
#                         "Login": {
#                             "UserID": self.brokerconfig['Login']['UserID'],
#                             "Key": self.brokerconfig['Login']['Key'],
#                             "SendOrders": "1"
#                         }
#                     }))
#                     await asyncio.gather(self.receive_data(websocket), self.send_data(websocket))
#             except Exception as e:
#                 retries += 1
#                 logging.error(f"Connection failed. Retry {retries}/3")
#                 if retries >= 3:
#                     logging.critical("Max retries reached. Exiting.")
#                     break
#                 await asyncio.sleep(5)

#     async def receive_data(self, websocket):
#         async for message in websocket:
#             self.pipe.send(message)

#     async def send_data(self, websocket):
#         while not self.stop_event.is_set():
#             if self.pipe.poll():
#                 await websocket.send(json.dumps(self.pipe.recv()))
#             await asyncio.sleep(0.01)

#     def run(self):
#         asyncio.run(self.handle_websocket())

#     def stop(self):
#         self.stop_event.set()

# class AlgoRuleHandler:
#     def __init__(self, db_filename=f"data/algorules/algorule_{time.strftime('%d%m%Y')}.json",
#                  order_filename=f"data/orderbook/order_{time.strftime('%d%m%Y')}.csv",
#                  trade_filename=f"data/tradebook/trade_{time.strftime('%d%m%Y')}.csv"):
#         self.db_filename = db_filename
#         self.order_filename = order_filename
#         self.trade_filename = trade_filename
#         self.algorule_db = self._load_db()
#         self.contract_file_mts = []
#         self.order_list = []
#         self.trade_list = []
#         self.pipe = None
#         self.last_dump = self.last_status = time.time()

#     def _load_db(self):
#         if os.path.exists(self.db_filename):
#             with open(self.db_filename, "r") as f:
#                 logging.info(f"Loaded database from {self.db_filename}")
#                 return json.load(f)
#         logging.info(f"No database at {self.db_filename}. Starting empty.")
#         db = {}
#         self._dump_db(db)
#         return db

#     def _dump_db(self, db=None):
#         with open(self.db_filename, "w") as f:
#             json.dump(db or self.algorule_db, f, indent=4)

#     def masterContract(self, data):
#         self.contract_file_mts.append(data)
#         print(f"Login successful at {time.ctime()}")

#     def ruleStatusDownload(self, data):
#         rule_name = data['RuleStatus']['Rule']['RuleName']
#         if rule_name in self.algorule_db:
#             self.algorule_db[rule_name]['RuleStatus'] = data

#     def dump_agloruledb_json_onTimer(self):
#         if time.time() - self.last_dump > 5:
#             self._dump_db()
#             self.last_dump = time.time()

#     def update_RuleStatus_onTimer(self):
#         if time.time() - self.last_status > 60 and self.algorule_db:
#             for key in self.algorule_db:
#                 self.pipe.send({"RuleStatus": {"RuleName": key}})
#             self.last_status = time.time()

#     def spreadUpdate(self, rule_data):
#         rule_name = rule_data['Spread']['RuleName']
#         if rule_name not in self.algorule_db:
#             self.algorule_db[rule_name] = {'SPREAD': {}, 'RuleStatus': {}, 'Order': [], 'Trade': []}
#             self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

#         self.algorule_db[rule_name]['SPREAD'] = rule_data
#         if (self.algorule_db[rule_name].get('RuleStatus', {}).get('RuleStatus', {}).get('Rule', {}).get('Status') == "Active"):
#             self._check_and_trade(rule_name)

#     def _check_and_trade(self, rule_name):
#         current_spread = float(self.algorule_db[rule_name]['SPREAD']['Spread']['ForwardSpread'])
#         rule = self.algorule_db[rule_name]['RuleStatus']['RuleStatus']
#         f_entry, r_entry = float(rule['TradingProperties']['FEntry']), float(rule['TradingProperties']['REntry'])
#         fnlot, rnlot = int(rule['TradingProperties']['FNlot']), int(rule['TradingProperties']['RNlot'])

#         if current_spread <= f_entry:
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['1']['Exchange'], "ScriptID": rule['Legs']['1']['ScriptID'], "Side": "Buy", "Qty": fnlot, "Price": current_spread}})
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['2']['Exchange'], "ScriptID": rule['Legs']['2']['ScriptID'], "Side": "Sell", "Qty": fnlot, "Price": current_spread}})
#         elif current_spread >= r_entry:
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['2']['Exchange'], "ScriptID": rule['Legs']['2']['ScriptID'], "Side": "Sell", "Qty": rnlot, "Price": current_spread}})
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['1']['Exchange'], "ScriptID": rule['Legs']['1']['ScriptID'], "Side": "Buy", "Qty": rnlot, "Price": current_spread}})

#     def order(self, rule_data):
#         rule_data['Order']['LocalTime'] = time.ctime()
#         self.order_list.append(rule_data)
#         self._dump_to_csv(self.order_list, self.order_filename, 'Order')
#         rule_name = rule_data['Order']['RuleName']
#         if rule_name in self.algorule_db:
#             self.algorule_db[rule_name]['Order'].append(rule_data)
#             self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

#     def trade(self, rule_data):
#         rule_data['Trade']['LocalTime'] = time.ctime()
#         self.trade_list.append(rule_data)
#         self._dump_to_csv(self.trade_list, self.trade_filename, 'Trade')
#         rule_name = rule_data['Trade']['RuleName']
#         if rule_name in self.algorule_db:
#             self.algorule_db[rule_name]['Trade'].append(rule_data)
#             self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

#     def _dump_to_csv(self, data, filename, key):
#         df = pd.DataFrame([item[key] for item in data])
#         if os.path.isfile(filename):
#             df.to_csv(filename, mode='a', header=False, index=False)
#         else:
#             df.to_csv(filename, index=False)

# class EventHandler(multiprocessing.Process):
#     def __init__(self, pipe):
#         super().__init__()
#         self.pipe = pipe
#         self.algoRuleHandler = AlgoRuleHandler()
#         self.algoRuleHandler.pipe = pipe
#         self.stop_event = multiprocessing.Event()

#     def eventHandler(self):
#         while not self.stop_event.is_set():
#             if self.pipe.poll():
#                 message = self.pipe.recv()
#                 parsed = json.loads(message)
#                 {'Spread': self.algoRuleHandler.spreadUpdate,
#                  'Master': self.algoRuleHandler.masterContract,
#                  'RuleStatus': self.algoRuleHandler.ruleStatusDownload,
#                  'Order': self.algoRuleHandler.order,
#                  'Trade': self.algoRuleHandler.trade}.get(next(iter(parsed)), lambda x: None)(parsed)
#             self.algoRuleHandler.dump_agloruledb_json_onTimer()
#             self.algoRuleHandler.update_RuleStatus_onTimer()

#     def run(self):
#         self.eventHandler()

#     def stop(self):
#         self.stop_event.set()

# class FileLoader:
#     def __init__(self, directory="."):
#         self.directory = directory
#         self.keyword = None

#     def list_files(self, keyword, starts_with=None):
#         self.keyword = keyword
#         return [f for f in os.listdir(self.directory) if keyword in f and (starts_with is None or f.startswith(starts_with))]

#     def load_and_update_file(self, filepath, update_interval=2):
#         while True:
#             if os.path.exists(filepath):
#                 df = pd.read_csv(filepath)
#                 fields = ['OrderNo' if self.keyword == 'order' else 'TradeID', 'Exchange', 'ScriptID', 'Price', 'Price', 'Qty', 'Side', 'RuleName', 'LocalTime']
#                 print(f"======= {'ORDER' if self.keyword == 'order' else 'TRADE'}BOOK =======\n", df[fields].tail(5))
#             time.sleep(update_interval)

#     def select_file(self, keyword, starts_with):
#         files = self.list_files(keyword, starts_with)
#         if files:
#             print(f"\nFiles ({starts_with}*):")
#             for i, f in enumerate(files, 1):
#                 print(f"{i}. {f}")
#             choice = int(input("Select file: "))
#             return os.path.join(self.directory, files[choice - 1]) if 1 <= choice <= len(files) else None
#         print(f"No files found with '{starts_with}'.")
#         return None

# brokerconfig = {"Login": {"UserID": "DEALER", "Key": "Abc@123"}, "uri": "ws://192.168.173.244:1234"}

# if __name__ == "__main__":
#     parent_conn, child_conn = multiprocessing.Pipe()
#     while True:
#         os.system('cls' if os.name == 'nt' else 'clear')
#         print("======= 2LEG ALGO TRADER =======")
#         print("1. Login to MTS\n2. Create new algo rules\n3. Activate/Deactivate algo\n4. Update algorule\n5. View portfolio\n6. Update RMS\n7. View order/trade history\n8. Set alerts and notifications\n9. View logger\n10. Exit")
#         choice = input("\nChoice: ").strip()

#         if choice == "1":
#             ws_process = WebSocketProcess(brokerconfig, child_conn)
#             ws_process.start()
#             event_handler = EventHandler(parent_conn)
#             event_handler.start()
#             try:
#                 while True: time.sleep(1)
#             except KeyboardInterrupt:
#                 ws_process.stop()
#                 event_handler.stop()
#                 ws_process.join()
#                 event_handler.join()

#         elif choice == "7":
#             loader = FileLoader()
#             while True:
#                 os.system('cls' if os.name == 'nt' else 'clear')
#                 print("1. View orderbook\n2. View tradebook\n3. Exit")
#                 sub_choice = input("\nChoice: ").strip()
#                 if sub_choice in ("1", "2"):
#                     filepath = loader.select_file("order" if sub_choice == "1" else "trade", "order_" if sub_choice == "1" else "trade_")
#                     if filepath: loader.load_and_update_file(filepath)
#                 elif sub_choice == "3": break

#         elif choice == "9":
#             os.system('cls' if os.name == 'nt' else 'clear')
#             print("======= LOG VIEWER =======")
#             time.sleep(5)
#             try: subprocess.run(["tail", "-f", log_filename])
#             except KeyboardInterrupt: print("\nExiting log viewer...")

#         elif choice == "10":
#             print("Goodbye!")
#             break

#         else:
#             print("Invalid choice.")

# import json
# import asyncio
# import websockets
# import multiprocessing
# import time
# import os
# import logging

# log_filename = "data/logs/mtslog.json"  # Fixed log name, you can change this too
# logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# class WebSocketProcess(multiprocessing.Process):
#     def __init__(self, brokerconfig, pipe):
#         super().__init__()
#         self.brokerconfig = brokerconfig
#         self.uri = brokerconfig['uri']
#         self.pipe = pipe
#         self.stop_event = multiprocessing.Event()

#     async def handle_websocket(self):
#         retries = 0
#         while not self.stop_event.is_set():
#             try:
#                 logging.info(f"Connecting to WebSocket: {self.uri}")
#                 async with websockets.connect(self.uri) as websocket:
#                     logging.info("Connected")
#                     await websocket.send(json.dumps({
#                         "Login": {
#                             "UserID": self.brokerconfig['Login']['UserID'],
#                             "Key": self.brokerconfig['Login']['Key'],
#                             "SendOrders": "1"
#                         }
#                     }))
#                     await asyncio.gather(self.receive_data(websocket), self.send_data(websocket))
#             except Exception as e:
#                 retries += 1
#                 logging.error(f"Connection failed. Retry {retries}/3")
#                 if retries >= 3:
#                     logging.critical("Max retries reached. Exiting.")
#                     break
#                 await asyncio.sleep(5)

#     async def receive_data(self, websocket):
#         async for message in websocket:
#             self.pipe.send(message)

#     async def send_data(self, websocket):
#         while not self.stop_event.is_set():
#             if self.pipe.poll():
#                 await websocket.send(json.dumps(self.pipe.recv()))
#             await asyncio.sleep(0.01)

#     def run(self):
#         asyncio.run(self.handle_websocket())

#     def stop(self):
#         self.stop_event.set()

# class AlgoRuleHandler:
#     def __init__(self, 
#                  db_filename="data/algorules/algorule_12012025.json", 
#                  order_filename="data/orderbook/orderbook.json",
#                  trade_filename="data/tradebook/tradebook.json"):
#         self.db_filename = db_filename
#         self.order_filename = order_filename
#         self.trade_filename = trade_filename
#         self.algorule_db = self._load_json(db_filename)
#         self.order_list = self._load_json(order_filename, default=[])
#         self.trade_list = self._load_json(trade_filename, default=[])
#         self.contract_file_mts = []
#         self.pipe = None
#         self.last_dump = self.last_status = time.time()

#     def _load_json(self, filename, default=None):
#         if os.path.exists(filename):
#             with open(filename, "r") as f:
#                 logging.info(f"Loaded {filename}")
#                 return json.load(f)
#         logging.info(f"No {filename} found. Starting with default.")
#         data = default if default is not None else {}
#         self._dump_json(filename, data)
#         return data

#     def _dump_json(self, filename, data):
#         with open(filename, "w") as f:
#             json.dump(data, f, indent=4)

#     def masterContract(self, data):
#         self.contract_file_mts.append(data)
#         print(f"Login successful at {time.ctime()}")

#     def ruleStatusDownload(self, data):
#         rule_name = data['RuleStatus']['Rule']['RuleName']
#         if rule_name in self.algorule_db:
#             self.algorule_db[rule_name]['RuleStatus'] = data

#     def dump_agloruledb_json_onTimer(self):
#         if time.time() - self.last_dump > 5:
#             self._dump_json(self.db_filename, self.algorule_db)
#             self._dump_json(self.order_filename, self.order_list)
#             self._dump_json(self.trade_filename, self.trade_list)
#             self.last_dump = time.time()

#     def update_RuleStatus_onTimer(self):
#         if time.time() - self.last_status > 60 and self.algorule_db:
#             for key in self.algorule_db:
#                 self.pipe.send({"RuleStatus": {"RuleName": key}})
#             self.last_status = time.time()

#     def spreadUpdate(self, rule_data):
#         rule_name = rule_data['Spread']['RuleName']
#         if rule_name not in self.algorule_db:
#             self.algorule_db[rule_name] = {'SPREAD': {}, 'RuleStatus': {}, 'Order': [], 'Trade': []}
#             self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

#         self.algorule_db[rule_name]['SPREAD'] = rule_data
#         if (self.algorule_db[rule_name].get('RuleStatus', {}).get('RuleStatus', {}).get('Rule', {}).get('Status') == "Active"):
#             self._check_and_trade(rule_name)

#     def _check_and_trade(self, rule_name):
#         current_spread = float(self.algorule_db[rule_name]['SPREAD']['Spread']['ForwardSpread'])
#         rule = self.algorule_db[rule_name]['RuleStatus']['RuleStatus']
#         f_entry, r_entry = float(rule['TradingProperties']['FEntry']), float(rule['TradingProperties']['REntry'])
#         fnlot, rnlot = int(rule['TradingProperties']['FNlot']), int(rule['TradingProperties']['RNlot'])

#         if current_spread <= f_entry:
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['1']['Exchange'], "ScriptID": rule['Legs']['1']['ScriptID'], "Side": "Buy", "Qty": fnlot, "Price": current_spread}})
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['2']['Exchange'], "ScriptID": rule['Legs']['2']['ScriptID'], "Side": "Sell", "Qty": fnlot, "Price": current_spread}})
#         elif current_spread >= r_entry:
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['2']['Exchange'], "ScriptID": rule['Legs']['2']['ScriptID'], "Side": "Sell", "Qty": rnlot, "Price": current_spread}})
#             self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['1']['Exchange'], "ScriptID": rule['Legs']['1']['ScriptID'], "Side": "Buy", "Qty": rnlot, "Price": current_spread}})

#     def order(self, rule_data):
#         rule_data['Order']['LocalTime'] = time.ctime()
#         self.order_list.append(rule_data)
#         rule_name = rule_data['Order']['RuleName']
#         if rule_name in self.algorule_db:
#             self.algorule_db[rule_name]['Order'].append(rule_data)
#             self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

#     def trade(self, rule_data):
#         rule_data['Trade']['LocalTime'] = time.ctime()
#         self.trade_list.append(rule_data)
#         rule_name = rule_data['Trade']['RuleName']
#         if rule_name in self.algorule_db:
#             self.algorule_db[rule_name]['Trade'].append(rule_data)
#             self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

# class EventHandler(multiprocessing.Process):
#     def __init__(self, pipe):
#         super().__init__()
#         self.pipe = pipe
#         self.algoRuleHandler = AlgoRuleHandler()
#         self.algoRuleHandler.pipe = pipe
#         self.stop_event = multiprocessing.Event()

#     def eventHandler(self):
#         while not self.stop_event.is_set():
#             if self.pipe.poll():
#                 message = self.pipe.recv()
#                 parsed = json.loads(message)
#                 {'Spread': self.algoRuleHandler.spreadUpdate,
#                  'Master': self.algoRuleHandler.masterContract,
#                  'RuleStatus': self.algoRuleHandler.ruleStatusDownload,
#                  'Order': self.algoRuleHandler.order,
#                  'Trade': self.algoRuleHandler.trade}.get(next(iter(parsed)), lambda x: None)(parsed)
#             self.algoRuleHandler.dump_agloruledb_json_onTimer()
#             self.algoRuleHandler.update_RuleStatus_onTimer()

#     def run(self):
#         self.eventHandler()

#     def stop(self):
#         self.stop_event.set()

# class FileLoader:
#     def __init__(self, directory="."):
#         self.directory = directory
#         self.keyword = None

#     def list_files(self, keyword, starts_with=None):
#         self.keyword = keyword
#         return [f for f in os.listdir(self.directory) if keyword in f and (starts_with is None or f.startswith(starts_with))]

#     def load_and_update_file(self, filepath, update_interval=2):
#         while True:
#             if os.path.exists(filepath):
#                 with open(filepath, 'r') as f:
#                     data = json.load(f)
#                 fields = ['OrderNo' if self.keyword == 'order' else 'TradeID', 'Exchange', 'ScriptID', 'Price', 'Qty', 'Side', 'RuleName', 'LocalTime']
#                 print(f"======= {'ORDER' if self.keyword == 'order' else 'TRADE'}BOOK =======\n", 
#                       "\n".join([str({k: item['Order' if self.keyword == 'order' else 'Trade'][k] for k in fields}) for item in data[-5:]]))
#             time.sleep(update_interval)

#     def select_file(self, keyword, starts_with):
#         files = self.list_files(keyword, starts_with)
#         if files:
#             print(f"\nFiles ({starts_with}*):")
#             for i, f in enumerate(files, 1):
#                 print(f"{i}. {f}")
#             choice = int(input("Select file: "))
#             return os.path.join(self.directory, files[choice - 1]) if 1 <= choice <= len(files) else None
#         print(f"No files found with '{starts_with}'.")
#         return None

# brokerconfig = {"Login": {"UserID": "DEALER", "Key": "Abc@123"}, "uri": "ws://192.168.173.244:1234"}

# if __name__ == "__main__":
#     parent_conn, child_conn = multiprocessing.Pipe()
#     while True:
#         os.system('cls' if os.name == 'nt' else 'clear')
#         print("======= 2LEG ALGO TRADER =======\n1. Login to MTS\n2. Create new algo rules\n3. Activate/Deactivate algo\n4. Update algorule\n5. View portfolio\n6. Update RMS\n7. View order/trade history\n8. Set alerts and notifications\n9. View logger\n10. Exit")
#         choice = input("\nChoice: ").strip()

#         if choice == "1":
#             ws_process = WebSocketProcess(brokerconfig, child_conn)
#             ws_process.start()
#             event_handler = EventHandler(parent_conn)
#             event_handler.start()
#             try:
#                 while True: time.sleep(1)
#             except KeyboardInterrupt:
#                 ws_process.stop()
#                 event_handler.stop()
#                 ws_process.join()
#                 event_handler.join()

#         elif choice == "7":
#             loader = FileLoader()
#             while True:
#                 os.system('cls' if os.name == 'nt' else 'clear')
#                 print("1. View orderbook\n2. View tradebook\n3. Exit")
#                 sub_choice = input("\nChoice: ").strip()
#                 if sub_choice in ("1", "2"):
#                     filepath = loader.select_file("order" if sub_choice == "1" else "trade", "orderbook" if sub_choice == "1" else "tradebook")
#                     if filepath: loader.load_and_update_file(filepath)
#                 elif sub_choice == "3": break

#         elif choice == "9":
#             os.system('cls' if os.name == 'nt' else 'clear')
#             print("======= LOG VIEWER =======")
#             time.sleep(5)
#             try: subprocess.run(["tail", "-f", log_filename])
#             except KeyboardInterrupt: print("\nExiting log viewer...")

#         elif choice == "10":
#             print("Goodbye!")
#             break

#         else:
#             print("Invalid choice.")  


import json
import asyncio
import websockets
import multiprocessing
import time
import os
import logging

# Define the log file path and ensure directory exists
log_filename = "data/logs/mtslog.json"
os.makedirs(os.path.dirname(log_filename), exist_ok=True)
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WebSocketProcess(multiprocessing.Process):
    def __init__(self, brokerconfig, pipe):
        super().__init__()
        self.brokerconfig = brokerconfig
        self.uri = brokerconfig['uri']
        self.pipe = pipe
        self.stop_event = multiprocessing.Event()

    async def handle_websocket(self):
        retries = 0
        while not self.stop_event.is_set():
            try:
                logging.info(f"Connecting to WebSocket: {self.uri}")
                async with websockets.connect(self.uri) as websocket:
                    logging.info("Connected")
                    await websocket.send(json.dumps({
                        "Login": {
                            "UserID": self.brokerconfig['Login']['UserID'],
                            "Key": self.brokerconfig['Login']['Key'],
                            "SendOrders": "1"
                        }
                    }))
                    await asyncio.gather(self.receive_data(websocket), self.send_data(websocket))
            except Exception as e:
                retries += 1
                logging.error(f"Connection failed. Retry {retries}/3")
                if retries >= 3:
                    logging.critical("Max retries reached. Exiting.")
                    break
                await asyncio.sleep(5)

    async def receive_data(self, websocket):
        async for message in websocket:
            self.pipe.send(message)

    async def send_data(self, websocket):
        while not self.stop_event.is_set():
            if self.pipe.poll():
                await websocket.send(json.dumps(self.pipe.recv()))
            await asyncio.sleep(0.01)

    def run(self):
        asyncio.run(self.handle_websocket())

    def stop(self):
        self.stop_event.set()

class AlgoRuleHandler:
    def __init__(self, 
                 db_filename="data/algorule/algorule_12012025.json", 
                 order_filename="data/orderbook/orderbook.json",
                 trade_filename="data/tradebook/tradebook.json"):
        self.db_filename = db_filename
        self.order_filename = order_filename
        self.trade_filename = trade_filename
        self.algorule_db = self._load_json(db_filename)
        self.order_list = self._load_json(order_filename, default=[])
        self.trade_list = self._load_json(trade_filename, default=[])
        self.contract_file_mts = []
        self.pipe = None
        self.last_dump = self.last_status = time.time()

    def _load_json(self, filename, default=None):
        os.makedirs(os.path.dirname(filename), exist_ok=True)  # Ensure directory exists
        if os.path.exists(filename):
            with open(filename, "r") as f:
                logging.info(f"Loaded {filename}")
                return json.load(f)
        logging.info(f"No {filename} found. Starting with default.")
        data = default if default is not None else {}
        self._dump_json(filename, data)
        return data

    def _dump_json(self, filename, data):
        os.makedirs(os.path.dirname(filename), exist_ok=True)  # Ensure directory exists
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def masterContract(self, data):
        self.contract_file_mts.append(data)
        print(f"Login successful at {time.ctime()}")

    def ruleStatusDownload(self, data):
        rule_name = data['RuleStatus']['Rule']['RuleName']
        if rule_name in self.algorule_db:
            self.algorule_db[rule_name]['RuleStatus'] = data

    def dump_agloruledb_json_onTimer(self):
        if time.time() - self.last_dump > 5:
            self._dump_json(self.db_filename, self.algorule_db)
            self._dump_json(self.order_filename, self.order_list)
            self._dump_json(self.trade_filename, self.trade_list)
            self.last_dump = time.time()

    def update_RuleStatus_onTimer(self):
        if time.time() - self.last_status > 60 and self.algorule_db:
            for key in self.algorule_db:
                self.pipe.send({"RuleStatus": {"RuleName": key}})
            self.last_status = time.time()

    def spreadUpdate(self, rule_data):
        rule_name = rule_data['Spread']['RuleName']
        if rule_name not in self.algorule_db:
            self.algorule_db[rule_name] = {'SPREAD': {}, 'RuleStatus': {}, 'Order': [], 'Trade': []}
            self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

        self.algorule_db[rule_name]['SPREAD'] = rule_data
        if (self.algorule_db[rule_name].get('RuleStatus', {}).get('RuleStatus', {}).get('Rule', {}).get('Status') == "Active"):
            self._check_and_trade(rule_name)

    def _check_and_trade(self, rule_name):
        current_spread = float(self.algorule_db[rule_name]['SPREAD']['Spread']['ForwardSpread'])
        rule = self.algorule_db[rule_name]['RuleStatus']['RuleStatus']
        f_entry, r_entry = float(rule['TradingProperties']['FEntry']), float(rule['TradingProperties']['REntry'])
        fnlot, rnlot = int(rule['TradingProperties']['FNlot']), int(rule['TradingProperties']['RNlot'])

        if current_spread <= f_entry:
            self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['1']['Exchange'], "ScriptID": rule['Legs']['1']['ScriptID'], "Side": "Buy", "Qty": fnlot, "Price": current_spread}})
            self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['2']['Exchange'], "ScriptID": rule['Legs']['2']['ScriptID'], "Side": "Sell", "Qty": fnlot, "Price": current_spread}})
        elif current_spread >= r_entry:
            self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['2']['Exchange'], "ScriptID": rule['Legs']['2']['ScriptID'], "Side": "Sell", "Qty": rnlot, "Price": current_spread}})
            self.order({"Order": {"RuleName": rule_name, "Exchange": rule['Legs']['1']['Exchange'], "ScriptID": rule['Legs']['1']['ScriptID'], "Side": "Buy", "Qty": rnlot, "Price": current_spread}})

    def order(self, rule_data):
        rule_data['Order']['LocalTime'] = time.ctime()
        self.order_list.append(rule_data)
        rule_name = rule_data['Order']['RuleName']
        if rule_name in self.algorule_db:
            self.algorule_db[rule_name]['Order'].append(rule_data)
            self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

    def trade(self, rule_data):
        rule_data['Trade']['LocalTime'] = time.ctime()
        self.trade_list.append(rule_data)
        rule_name = rule_data['Trade']['RuleName']
        if rule_name in self.algorule_db:
            self.algorule_db[rule_name]['Trade'].append(rule_data)
            self.pipe.send({"RuleStatus": {"RuleName": rule_name}})

class EventHandler(multiprocessing.Process):
    def __init__(self, pipe):
        super().__init__()
        self.pipe = pipe
        self.algoRuleHandler = AlgoRuleHandler()
        self.algoRuleHandler.pipe = pipe
        self.stop_event = multiprocessing.Event()

    def eventHandler(self):
        while not self.stop_event.is_set():
            if self.pipe.poll():
                message = self.pipe.recv()
                parsed = json.loads(message)
                {'Spread': self.algoRuleHandler.spreadUpdate,
                 'Master': self.algoRuleHandler.masterContract,
                 'RuleStatus': self.algoRuleHandler.ruleStatusDownload,
                 'Order': self.algoRuleHandler.order,
                 'Trade': self.algoRuleHandler.trade}.get(next(iter(parsed)), lambda x: None)(parsed)
            self.algoRuleHandler.dump_agloruledb_json_onTimer()
            self.algoRuleHandler.update_RuleStatus_onTimer()

    def run(self):
        self.eventHandler()

    def stop(self):
        self.stop_event.set()

class FileLoader:
    def __init__(self, directory="."):
        self.directory = directory
        self.keyword = None

    def list_files(self, keyword, starts_with=None):
        self.keyword = keyword
        return [f for f in os.listdir(self.directory) if keyword in f and (starts_with is None or f.startswith(starts_with))]

    def load_and_update_file(self, filepath, update_interval=2):
        while True:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                fields = ['OrderNo' if self.keyword == 'order' else 'TradeID', 'Exchange', 'ScriptID', 'Price', 'Qty', 'Side', 'RuleName', 'LocalTime']
                print(f"======= {'ORDER' if self.keyword == 'order' else 'TRADE'}BOOK =======\n", 
                      "\n".join([str({k: item['Order' if self.keyword == 'order' else 'Trade'][k] for k in fields}) for item in data[-5:]]))
            time.sleep(update_interval)

    def select_file(self, keyword, starts_with):
        files = self.list_files(keyword, starts_with)
        if files:
            print(f"\nFiles ({starts_with}*):")
            for i, f in enumerate(files, 1):
                print(f"{i}. {f}")
            choice = int(input("Select file: "))
            return os.path.join(self.directory, files[choice - 1]) if 1 <= choice <= len(files) else None
        print(f"No files found with '{starts_with}'.")
        return None

brokerconfig = {"Login": {"UserID": "DEALER", "Key": "Abc@123"}, "uri": "ws://192.168.173.244:1234"}

if __name__ == "__main__":
    parent_conn, child_conn = multiprocessing.Pipe()
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("======= 2LEG ALGO TRADER =======\n1. Login to MTS\n2. Create new algo rules\n3. Activate/Deactivate algo\n4. Update algorule\n5. View portfolio\n6. Update RMS\n7. View order/trade history\n8. Set alerts and notifications\n9. View logger\n10. Exit")
        choice = input("\nChoice: ").strip()

        if choice == "1":
            ws_process = WebSocketProcess(brokerconfig, child_conn)
            ws_process.start()
            event_handler = EventHandler(parent_conn)
            event_handler.start()
            try:
                while True: time.sleep(1)
            except KeyboardInterrupt:
                ws_process.stop()
                event_handler.stop()
                ws_process.join()
                event_handler.join()

        elif choice == "7":
            loader = FileLoader()
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                print("1. View orderbook\n2. View tradebook\n3. Exit")
                sub_choice = input("\nChoice: ").strip()
                if sub_choice in ("1", "2"):
                    filepath = loader.select_file("order" if sub_choice == "1" else "trade", "orderbook" if sub_choice == "1" else "tradebook")
                    if filepath: loader.load_and_update_file(filepath)
                elif sub_choice == "3": break

        elif choice == "9":
            os.system('cls' if os.name == 'nt' else 'clear')
            print("======= LOG VIEWER =======")
            time.sleep(5)
            try: subprocess.run(["tail", "-f", log_filename])
            except KeyboardInterrupt: print("\nExiting log viewer...")

        elif choice == "10":
            print("Goodbye!")
            break

        else:
            print("Invalid choice.")