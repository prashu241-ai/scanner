from kiteconnect import KiteConnect

API_KEY    = "3wbhan16xjugru90"
API_SECRET = "5zxg87zeoe9hennhfhnu7wp0la5p73tr"

kite = KiteConnect(api_key=API_KEY)
print("Login URL:", kite.login_url())

request_token = input("Paste request_token from redirect URL: ")
data = kite.generate_session(request_token, api_secret=API_SECRET)
print("ACCESS TOKEN:", data["access_token"])
