from lxml import etree
import io
import re
import cloudscraper
from math import ceil
import pymongo
from tqdm import tqdm


client = pymongo.MongoClient("localhost", 27017)
db = client.automation_zillow
col = db.data
db2 = client.final_zillow
col2 = db2.data

def get_data(item):
    scraper = cloudscraper.create_scraper()
    response = scraper.get(item)
    parser = etree.HTMLParser(encoding="UTF-8")
    doc = etree.parse(io.StringIO(str(response.text)), parser)
    try:
        js = eval([ld for ld in doc.xpath("//script[@type='application/json']/text()") if "apiCache" in ld][0])
        false = False
        true = True
        null = ""
        js2 = eval(js['apiCache'])
        # list(js2.keys())[0]
        val = {}
        try:
            val['address'] = js2[list(js2.keys())[0]]['property']['streetAddress'] + ", " + js2[list(js2.keys())[0]]['property']['city'] + ", " + js2[list(js2.keys())[0]]['property']['state'] + " " + js2[list(js2.keys())[0]]['property']['zipcode']
        except:
            val['address'] = ""
        try:
            val['price'] = js2[list(js2.keys())[0]]['property']['price']
        except:
            val['price'] = ""
        try:
            val['zipcode'] = js2[list(js2.keys())[0]]['property']['zipcode']
        except:
            val['zipcode'] = ""

        try:
            val['image'] = js2[list(js2.keys())[0]]['property']['tvCollectionImageLink']
        except:
            val['image'] = ""
        val['agentName'] = " "
        val['phoneNumber'] = " "
        try:

            val['agentName'] = js2[list(js2.keys())[1]]['contactFormRenderData']['data']['agent_module']['display_name']
            val['phoneNumber'] = js2[list(js2.keys())[1]]['contactFormRenderData']['data']['agent_module']['phone']['areacode'] + js2[list(js2.keys())[1]]['contactFormRenderData']['data']['agent_module']['phone']['prefix'] + js2[list(js2.keys())[1]]['contactFormRenderData']['data']['agent_module']['phone']['number']
        except:
            try:
                name= []
                pn = []
                agents = js2[list(js2.keys())[1]]['contactFormRenderData']['data']['contact_recipients']
                for agent in agents:
                    name.append(agent['display_name'])
                    try:
                        pn.append(agent['phone']['areacode']+agent['phone']['prefix']+agent['phone']['number'])
                    except:
                        pass
                val['agentName'] = ", ".join(name)
                val['phoneNumber'] = ", ".join(pn)
            except:
                pass
        val['url'] = item
        return val
    except:
        return False




def get_address(url, current_page, total):
    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)

    if response.status_code == 200:
        parser = etree.HTMLParser(encoding="utf-8")
        doc = etree.parse(io.StringIO(str(response.text)), parser)
        try:
            if current_page == 1:
                result_count = int("".join(re.findall("\d+", " ".join(doc.xpath("//span[@class='result-count']/text()")))))
            else:
                result_count = total
            divs = doc.xpath("//ul[@class='photo-cards photo-cards_wow photo-cards_short']/li")
            pages = len(divs)
            pagination = ceil(result_count/pages)+1
            print(f"Current Page: {current_page}")
            print(f"Pagination Page: {pagination}")
            stop = False
            if current_page == pagination:
                stop = True
            else:
                # print(pagination)
                # dataa = []
                url = response.url.split("3A%7B", 1)[0] + "3A%7B" + "%22currentPage%22%3A{}".format(current_page+1) + response.url.split("3A%7B", 1)[-1]
                # print(url)
                # print("********************************")
                # print(len(divs))

                for div in tqdm(divs):
                    # val = {}
                    try:
                        # print(div.xpath(".//a[contains(@class,'list-card-link')]/@href")[0])
                        val = get_data(div.xpath(".//a[contains(@class,'list-card-link')]/@href")[0])
                        if val != False:
                            col.insert_one(val)
                    except:
                        pass
                print("Going through the LAC")
                if stop:
                    pass
                else:
                    print("Got Past LAC")
                    print(f"Values retained are | Current Page: {current_page+1}, result_count: {result_count}")
                    get_address(url, current_page+1, result_count)
        except:
            pass
    else:
        pass

def get_final_zillow(zipcode):
    mydoc = col.find({"zipcode": zipcode})
    for x in tqdm(mydoc):
        scraper = cloudscraper.create_scraper()
        response = scraper.get(x['url'])
        parser = etree.HTMLParser(encoding="UTF-8")
        doc = etree.parse(io.StringIO(str(response.text)), parser)
        try:
            js = eval([ld for ld in doc.xpath("//script[@type='application/json']/text()") if "apiCache" in ld][0])
            false = False
            true = True
            null = ""
            js2 = eval(js['apiCache'])
            # list(js2.keys())[0]
            val = {}
            try:
                val['Indicates the lot size, in square feet'] = js2[list(js2.keys())[0]]['property']['lotSize']
            except:
                val['Indicates the lot size, in square feet'] = 0
            try:
                val['zipcode'] = zipcode
            except:
                val['zipcode'] = ""
            try:
                val['Building size'] = js2[list(js2.keys())[0]]['property']['livingArea']
            except:
                val['Building size'] = 0
            try:
                val['Total Market Value'] = js2[list(js2.keys())[0]]['property']['price']
            except:
                val['Total Market Value'] = " "
            try:
                val['address'] = js2[list(js2.keys())[0]]['property']['streetAddress'] + ", " + \
                                 js2[list(js2.keys())[0]]['property']['city'] + ", " + \
                                 js2[list(js2.keys())[0]]['property']['state'] + " " + \
                                 js2[list(js2.keys())[0]]['property']['zipcode']
            except:
                val['address'] = " "
            try:
                val['propLandUse'] = js2[list(js2.keys())[0]]['property']['homeType'].replace("_", " ")
            except:
                val['propLandUse'] = " "
            col2.insert_one(val)

        except:
            pass




if __name__ == "__main__":
    url = "https://www.zillow.com/scottsdale-az-85258/?searchQueryState=%7B%22pagination%22%3A%7B%7D%2C%22mapBounds%22%3A%7B%22west%22%3A-111.95348392114256%2C%22east%22%3A-111.81855807885741%2C%22south%22%3A33.51559616742752%2C%22north%22%3A33.60534316012991%7D%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A94850%2C%22regionType%22%3A7%7D%5D%2C%22isMapVisible%22%3Atrue%2C%22mapZoom%22%3A13%2C%22filterState%22%3A%7B%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%7D%2C%22isListVisible%22%3Atrue%7D"
    get_address(url, 1, 0)
    zipcode = "".join(re.findall("\d+", url.split("/?")[0]))
    print("Getting the Data From Zillow")
    if zipcode.isdigit():
        get_final_zillow(zipcode)
