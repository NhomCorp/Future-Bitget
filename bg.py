import os, time, hmac, hashlib, base64, json, urllib.request, sys
K=os.environ["BITGET_API_KEY"]; S=os.environ["BITGET_API_SECRET"]; P=os.environ["BITGET_PASSPHRASE"]
def get(path, query=""):
    ts=str(int(time.time()*1000)); rp=path+("?"+query if query else "")
    sig=base64.b64encode(hmac.new(S.encode(), (ts+"GET"+rp).encode(), hashlib.sha256).digest()).decode()
    req=urllib.request.Request("https://api.bitget.com"+rp, headers={"ACCESS-KEY":K,"ACCESS-SIGN":sig,"ACCESS-TIMESTAMP":ts,"ACCESS-PASSPHRASE":P,"Content-Type":"application/json","locale":"en-US"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return json.load(r)
    except urllib.error.HTTPError as e: return {"http":e.code,"body":e.read().decode()[:300]}
acc=get("/api/v2/mix/account/accounts","productType=USDT-FUTURES")
pos=get("/api/v2/mix/position/all-position","productType=USDT-FUTURES&marginCoin=USDT")
out={"account":acc,"positions":pos}
json.dump(out, sys.stdout, indent=1)
