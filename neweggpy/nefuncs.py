from __future__ import division
from ast import literal_eval as le
from datetime import datetime
from json import loads
from lxml.html import fromstring
from math import ceil
from pandas import DataFrame
from time import sleep
import os
import requests
import sqlite3
import traceback
import sys

dtn = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def IterPages(rootobj):
    t = rootobj.cssselect('#pagesNum > option:nth-child(1)')[0].text
    return int(ceil(int(t[2:])/20))


def BoolToInt(boolobj):
    if boolobj == True:
        return 1
    else:
        assert boolobj == False
        return 0


def getPIDS(urlList, pg1root):
    ProductList = []
    for k, url in enumerate(urlList):
        if k is 0:  # Reuse the root object for the first page
            for el in pg1root.cssselect('a.item-cell'):
                ProductList.append(el.attrib['href'])
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'}
            r = requests.get(url, headers=headers).content
            for el in fromstring(r).cssselect('a.item-cell'):
                ProductList.append(el.attrib['href'])
    pids = [i.replace('https://m.newegg.com/products/', '') for i in ProductList]
    return pids


def getData(pidList):
    apiurl = 'http://www.ows.newegg.com/Products.egg'
    OutData = []
    for pid in pidList:
        print pid
        sleep(1)
        try:
            url = '%s/%s' % (apiurl, pid)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Android; Mobile; rv:14.0) Gecko/14.0 Firefox/14.0'}
            r = requests.get(url,headers=headers).content
            js = loads(r)
            basic = js['Basic']
            additional = js['Additional']
            g = {}
            g['Title'] = basic['Title']
            final_price = basic['FinalPrice'].replace(',', '')
            if final_price.count('Checkout') == 1:
                g['FinalPrice'] = float('NaN')
            elif final_price == 'See price in cart':
                g['FinalPrice'] = float(basic['MappingFinalPrice'].replace(',', '').replace('$', ''))
            else:
                g['FinalPrice'] = float(final_price.replace('$', ''))
            if (basic['OriginalPrice'] != ''):
                g['OriginalPrice'] = float(basic['OriginalPrice'].replace(',', '').replace('$', ''))
            else:
                g['OriginalPrice'] = 0.0
            g['Instock'] = BoolToInt(basic['Instock'])
            g['Rating'] = basic['ReviewSummary']['Rating']
            try:
                g['TotalReviews'] = le(basic['ReviewSummary']['TotalReviews'])[0]
            except:
                g['TotalReviews'] = 0
            g['IsHot'] = BoolToInt(basic['IsHot'])
            ShippingPrice = basic['ShippingText'].split(' ')[0]
            if ShippingPrice.count('FREE') == 1:
                g['ShippingPrice'] = 0.0
            elif ShippingPrice.count('Special') == 1:
                g['ShippingPrice'] = 2.99   # "Special shipping => $2.99 Egg Saver Shipping"
            else:
                g['ShippingPrice'] = float(ShippingPrice.replace('$', ''))
            g['IsShipByNewegg'] = BoolToInt(additional['ShippingInfo']['IsShipByNewegg'])

            if len(basic['PromotionText']) > 0:
                g['Promotion'] = basic['PromotionText']
            else:
                g['Promotion'] = 'NaN'
            MIR = additional['MailInRebates']
            if MIR is None:
                g['MailInRebateInfo'] = 'NaN'
            else:
                g['MailInRebateInfo'] = additional['MailInRebates'][0]
            g['PID'] = pid
            g['Brand'] = basic['ItemBrand']['Description']
            g['Date'] = dtn
            OutData.append(g)
        except Exception, e:
            print 'FAILED: %s %s' % (pid, e)
            traceback.print_exc()
            pass
    dframe = DataFrame(OutData)
    dframe['FinalPriceShipped'] = dframe['FinalPrice'] + dframe['ShippingPrice']

    return dframe


def insertData(tbl, dframe):
    thisdir = os.path.abspath(os.path.dirname(__file__))
    dbpath = os.path.join(thisdir, '../db/newegg.db')
    
    # CONNECT TO SQLITE DATABASE
    db = sqlite3.connect(dbpath)
    curs = db.cursor()

    # CREATE TABLE IF NEEDED
    tblstr = 'CREATE TABLE IF NOT EXISTS %s (brand TEXT, date TEXT, ' % tbl + \
             'finalprice REAL, instock INTEGER, ishot INTEGER, ' + \
             'isshipbynewegg INTEGER, rebate TEXT, originalprice REAL, pid TEXT, ' + \
             'promotion TEXT, rating INTEGER, shippingprice REAL, title TEXT, ' + \
             'totalreviews INTEGER, finalpriceshipped REAL)'
    curs.execute(tblstr)

    # INSERT ALL THE DATA AT ONCE
    curs.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' % tbl,
                      [tuple(i[1]) for i in dframe.iterrows()])
    db.commit()
    curs.close()
    db.close()
