import myconst
import requests
import time
import logging
import json
import redis
import inspect
import sys
import websocket
import ssl
import asyncio

logger = logging.getLogger('root')
logger.debug('Loading inim module.')

class central:
    def __init__(
            self,
            redis,
            base_url: str      = "https://api.inimcloud.com",
            websocket_url: str = "wss://ws.inimcloud.com/events",
            username: str      = None,
            password: str      = None,
            pin: int           = None,
            token: str         = None,
            token_expiry: int  = None,
            client_id: str     = None,
            client_name: str   = None,
            client_info: str   = None,
            role: int          = None,
            brand: int         = None,
            device_id: str     = None,
            ):

        """Initialize the central class."""
        self.base_url            = base_url
        self.username            = username
        self.password            = password
        self.pin                 = pin
        self.client_id           = client_id
        self.client_name         = client_name
        self.redis               = redis
        self.redis_prefix        = client_id+"."+client_name
        self.device_id           = device_id
        self.websocket_url       = websocket_url

        self.poll_expiry         = None
        self.authenticate_expiry = None
        self.scenario_id         = None
        self.token               = None
        self.auth_info           = None
        self.token_expiry        = None


        logger.debug(f"DeviceID: {self.device_id}")

    def check_token_validity(self):
        """Check if the token is still valid."""
        # Check if the token is still valid.
        if self.redis.exists(self.redis_prefix+".token") and self.redis.exists(self.redis_prefix+".token_expiry") and self.redis.exists(self.redis_prefix+".auth_info"):
            token        = self.redis.get(self.redis_prefix+".token")
            token_expiry = self.redis.get(self.redis_prefix+".token_expiry")
            auth_info    = self.redis.get(self.redis_prefix+".auth_info")
            logger.debug(f"Token: {token}")
            logger.debug(f"Token expiry: {token_expiry}")
            # pretty_auth_info = json.dumps(json.loads(auth_info.decode()), indent=4)
            # logger.debug(f"Auth info: {pretty_auth_info}")
            if token and token_expiry and auth_info:
                self.token = token.decode()
                self.token_expiry = float(token_expiry)
                self.auth_info = json.loads(auth_info.decode())
                if self.token_expiry > time.time():
                    logger.debug(f"Token retrieved from redis:[{self.token}] with expiry: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.token_expiry))} ({self.token_expiry})")
                    return  self.auth_info
                else:
                    logger.debug(f"Token expired: {self.token_expiry}")
                    self.auth_info = self.RegisterClient()
                return self.auth_info
        else:
            logger.debug(f"Token not found in redis")
            self.auth_info = self.RegisterClient()
            return self.auth_info

    def set_new_poll_expiry(self):
        fname=sys._getframe().f_code.co_name
        # Set new expiry.
        redis_key = self.redis_prefix+self.device_id+".poll_expiry"
        self.poll_expiry = time.time()+myconst.MAXPOLL_TIME
        logger.info(f"{fname} Set new poll expiry: {self.poll_expiry}")
        self.redis.set(redis_key,self.poll_expiry)
        return self.poll_expiry

    def set_new_authenticate_expiry(self):
        fname=sys._getframe().f_code.co_name
        # Set new expiry.
        redis_key = self.redis_prefix+self.device_id+".authenticate_expiry"
        self.authenticate_expiry = time.time()+myconst.MAXAUTHENTICATE_TIME
        logger.info(f"{fname} Set new authenticate expiry: {self.authenticate_expiry}")
        self.redis.set(redis_key,self.authenticate_expiry)
        return self.authenticate_expiry

    def RegisterClient(self):
        fname=sys._getframe().f_code.co_name
        """Register a new client with the remote API."""
        # Set the request parameters.
        req={
            "Node": "",
            "Name": "AlienMobilePro",
            "ClientIP": "",
            "Method": "RegisterClient",
            "ClientId": "",
            "Token": "",
            "Params": {
                "Username": self.username,
                "Password": self.password,
                "ClientId": self.client_id,
                "ClientName": self.client_name,
                "ClientInfo": "{\"name\":\"com.inim.alienmobile\",\"version\":\"3.1.0\",\"device\":\"hero2lte\",\"brand\":\"samsung\",\"platform\":\"android\",\"osversion\":\"Oreo v8.0, API Level: 26\"}",
                "Role": "1",
                "Brand": "0",
            }
        }

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request=json.dumps(req).replace(" ", "")

        # Building the request
        params="req="+request
        logger.debug(f"Request: {params}")
        # Make the request.
        response = requests.get(f"{self.base_url}", params=params)
        # Check if the request was successful.
        if response.status_code != 200:
            raise Exception(f"Request failed: {response.text}")
        logger.debug(f"{fname} Response: {response.text}")
        self.auth_info = json.loads(response.text)

        # Check if the request was successful (server side).
        if self.auth_info["Status"] != 0:
            raise Exception(f"Error {self.auth_info["Status"]}: {self.auth_info["ErrMsg"]}")

        self.token = self.auth_info["Data"]["Token"]
        self.token_expiry = time.time() + self.auth_info["Data"]["TTL"]
        logger.debug(f"Token received:[{self.token}] with expiry: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.token_expiry))} ({self.token_expiry})")
        logger.info(f"Client registered successfully.")


        # Store response in redis:
        self.redis.set(self.redis_prefix+".auth_info", response.text)
        self.redis.set(self.redis_prefix+".token", self.token)
        self.redis.set(self.redis_prefix+".token_expiry", self.token_expiry)

        return self.auth_info

    def Authenticate(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        logger.debug(f"Authenticate requested")
        redis_key = self.redis_prefix+self.device_id+".authenticate_expiry"
        if self.redis.exists(redis_key):
            self.authenticate_expiry = float(self.redis.get(redis_key).decode("utf-8"))
            logger.debug(f"{fname} Poll expiry: {self.authenticate_expiry}")
        else:
            # Set new expiry.
            self.authenticate_expiry = self.set_new_authenticate_expiry()
        self.check_token_validity()
        if self.authenticate_expiry > time.time():
            logger.warning(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.authenticate_expiry))} > {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")
            # Check if the token is still valid.
            params = {
                "Node": "",
                "Name": "AlienMobilePro",
                "ClientIP": "",
                "Method": "Authenticate",
                "ClientId": self.client_id  ,
                "Token": self.token,
                "Params": {}
            }

            # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
            # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
            request = json.dumps(params).replace(" ", "")

            # Building the request
            params = "req=" + request
            logger.debug(f"Request: {params}")


            # Make the request.
            response = requests.get(f"{self.base_url}", params=params)
            pretty_response = json.dumps(json.loads(response.text), indent=4)
            logger.debug(f"{fname} response {pretty_response}")
            return response
        else:
            logger.info(f"{fname} Skipping Authenticate not expired yet.")
            return

    def RequestPoll(self):
        fname=sys._getframe().f_code.co_name
        """request Poll."""
        # Check if the token is still valid.
        # Store response in redis:
        redis_key = self.redis_prefix+self.device_id+".poll_expiry"
        logger.debug(f"{fname} Redis key: {redis_key}")
        if self.redis.exists(redis_key):
            self.poll_expiry = float(self.redis.get(redis_key).decode("utf-8"))
            logger.debug(f"{fname} Poll expiry: {self.poll_expiry}")
        else:
            # Set new expiry.
            self.poll_expiry = self.set_new_poll_expiry()

        self.auth_info = self.Authenticate()

        if self.poll_expiry > time.time():
            logger.warning(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.poll_expiry))} > {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")

            logger.info(f"{fname} Polling for new data.")
            logger.debug(f"Auth info: {self.auth_info}")
            params = {"Params":{"DeviceId":self.device_id,"Type":5},"Node":"","Name":"Inim Home","ClientIP":"","Method":"RequestPoll","Token":self.token,"ClientId":self.client_id,"Context":"intrusion"}

            # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
            # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
            request = json.dumps(params).replace(" ", "")

            # Building the request
            params = "req=" + request
            logger.debug(f"{fname} Request: {params}")

            # Make the request.
            response = requests.get(f"{self.base_url}", params=params)
            pretty_response = json.dumps(json.loads(response.text), indent=4)
            logger.debug(f"{fname} response {pretty_response}")
            # Set new expiry.
            self.set_new_poll_expiry()
            return response
        else:
            logger.info(f"{fname} Skipping Poll not expired yet.")
            return

    def GetDevices(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        logger.debug(f"Authenticate requested")
        # Check if the token is still valid.
        self.RequestPoll()
        params = {
            "Node": "",
            "Name": "AlienMobilePro",
            "ClientIP": "",
            "Method": "GetDevices",
            "ClientId": self.client_id,
            "Token": self.token,
            "Params": {}
        }

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"Request: {params}")


        # Make the request.
        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response

    def GetDevicesExtended(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {
            "Params": {
                "DeviceId": self.device_id,
                "Type": 5,
            },
            "Node": "",
            "Name": "Inim Home",
            "ClientIP": "",
            "Method": "GetDevicesExtended",
            "Token": self.token,
            "ClientId": self.client_id,
            "Context": "intrusion",
        }

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response

    def GetDeviceItems(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {"Node":"","Name":"AlienMobilePro","ClientIP":"","Method":"GetDeviceItems","ClientId":self.client_id,"Token":self.token,"Params":{"DeviceId":self.device_id}}

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        pretty_response = json.dumps(json.loads(response.text), indent=4)

        # This is too long for terminal.
        # logger.debug(f"{fname} response {pretty_response}")
        logger.debug(f"{fname} response {response.text}")
        return response.text

    def GetDeviceAreas(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {"Node":"","Name":"AlienMobilePro","ClientIP":"","Method":"GetDeviceAreas","ClientId":self.client_id,"Token":self.token,"Params":{"DeviceId":self.device_id}}

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response.text

    def GetDeviceZones(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {"Node":"","Name":"AlienMobilePro","ClientIP":"","Method":"GetDeviceZones","ClientId":self.client_id,"Token":self.token,"Params":{"DeviceId":self.device_id}}

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response.text

    def ReadStatus(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {"Node":"","Name":"AlienMobilePro","ClientIP":"","Method":"ReadStatus","ClientId":self.client_id,"Token":self.token,"Params":{"DeviceId":self.device_id}}

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response.text

    def ReadItem(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {"Node":"","Name":"AlienMobilePro","ClientIP":"","Method":"ReadItem","ClientId":self.client_id,"Token":self.token,"Params":{"DeviceId":self.device_id, "ItemId":self.item_id, "Type":self.item_type}}

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response.text

    def ReadLogEntries(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {"Node":"","Name":"AlienMobilePro","ClientIP":"","Method":"ReadLogEntries","ClientId":self.client_id,"Token":self.token,"Params":{"DeviceId":self.device_id}}

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response.text

    def ReadUnreadyZones(self):
        fname=sys._getframe().f_code.co_name
        """List all sensors."""
        # Check if the token is still valid.
        self.RequestPoll()
        params = {"Node":"","Name":"AlienMobilePro","ClientIP":"","Method":"ReadUnreadyZones","ClientId":self.client_id,"Token":self.token,"Params":{"DeviceId":self.device_id,"Element":self.scenario_id,"Type":1,"Mode":0}}

        # The request is a json in a GET parameter (I don't really understand why, seems odd but wathever)
        # To continue i cleanup the request dictionary removing the spaces and convert it to a string.
        request = json.dumps(params).replace(" ", "")

        # Building the request
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")

        # Make the request.

        response = requests.get(f"{self.base_url}", params=params)
        # pretty_response = json.dumps(json.loads(response.text), indent=4)
        logger.debug(f"{fname} response {response.text}")
        return response.text

    def WebSocket(self):
        fname=sys._getframe().f_code.co_name
        def on_open(ws):
            print('Opened Connection')
            # ws.send(json.dumps(params))

        def on_close(ws, close_status_code, close_msg):
            print(f'Closed Connection {close_msg} - {close_status_code}')

        def on_message(ws, message):
            print (message)

        def on_error(ws, err):
            print("Got a an error: ", err)

        self.Authenticate()
        self.RequestPoll()

        params = {"Params":{"Brand":"0"},"Node":"","Name":"Inim Home","ClientIP":"","Method":"WebSocketStart","Token":self.token,"ClientId":self.client_id,"Context":"intrusion"}
        request = json.dumps(params).replace(" ", "")
        params = "req=" + request
        logger.debug(f"{fname} Request: {params}")


        full_url=f"{self.websocket_url}?{params}"
        logger.debug(f"{fname} WebSocket: {full_url}")

        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(full_url, on_open = on_open, on_close = on_close, on_message = on_message,on_error=on_error)
        logger.debug(f"{fname} WebSocket: {ws}")
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        ws.keep_running = True

    def __enter__(self):
        self.Authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        time.sleep(0)
        return self