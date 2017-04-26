import lxml.html
import requests
from neweggpy.nefuncs import IterPages,BoolToInt,getPIDS,getData,insertData

baseurl = 'https://m.newegg.com/productlist?description=nVjkbn88TPpxbYCO44j7AJ7lKvYiECglej4lhl3FXQM%253d&storeid=3&categoryid=-1&nodeid=6740&storetype=2&subcategoryid=32&brandid=-1&nvalue=100006740&showseealldeals=False&itemcount=0&issubcategory=true&level=3' 

headers = {'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'}
pg1 = requests.get(baseurl, headers=headers).content

root1 = lxml.html.fromstring(pg1)
page_count = IterPages(root1)
URLs = ['%s&Page=%s' % (baseurl, pgnum) for pgnum in range(1, page_count + 1)]

# FETCH AND PARSE THE DATA
pids = getPIDS(URLs, root1)
df = getData(pids)

# PUT DATA IN DATABASE
insertData('laptop', df)
