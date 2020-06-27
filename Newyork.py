from lxml import etree
from math import ceil
from tqdm import tqdm
import cloudscraper
import requests
import pymongo
import json
import re
import io


client = pymongo.MongoClient("localhost", 27017) #("mongodb://yashsoni:MongoDB@stackshare-shard-00-00-0fjja.mongodb.net:27017,stackshare-shard-00-01-0fjja.mongodb.net:27017,stackshare-shard-00-02-0fjja.mongodb.net:27017/<dbname>?ssl=true&replicaSet=stackshare-shard-0&authSource=admin&retryWrites=true&w=majority")
db = client.automation_zillow
col = db.data


def get_sales_comps(zipcode):
    scraper = cloudscraper.create_scraper()
    response = scraper.get(f"https://www.redfin.com/zipcode/{zipcode}/housing-market")
    print(response.status_code)
    parser = etree.HTMLParser(encoding="utf-8")
    doc = etree.parse(io.StringIO(str(response.text)), parser)
    sc = 0
    if "K" in "".join(doc.xpath("///div[@class='detail saleSqft']/div/div[@class='value']/span/text()")).replace("$",""):
        sc = float("".join(doc.xpath("///div[@class='detail saleSqft']/div/div[@class='value']/span/text()")).replace("$","").replace("K",""))*1000
    else:
        sc = "".join(doc.xpath("///div[@class='detail saleSqft']/div/div[@class='value']/span/text()")).replace("$","")
    print(sc)
    return int(sc)


def get_financial_model(val):
    try:
        if val['on_off'] == "On":
            price = val['price']
            # print
        else:
            price = 0
    except Exception as e:
        pass  # print(e)
    bldsize = val['buildingSize']
    buil = val['buildable']
    existing = bldsize * 170
    buildable = val['buildable'] * 250
    tsf = bldsize + buil  # bldsize + lotsize*far - bldsize
    total_of_existing_and_building = existing + buildable
    try:
        acquition = price * 0.8
    except:
        acquition = 0  # print(new['address'][i])
    refurbishment = (existing + buildable) * 0.8
    total_of_acquition_refurbishment = acquition + refurbishment
    arrangement_fee = total_of_acquition_refurbishment * 0.01
    interest_charge = total_of_acquition_refurbishment * 0.05
    equity = (price + total_of_existing_and_building) - total_of_acquition_refurbishment
    total_source_of_funds = (price + total_of_existing_and_building + total_of_acquition_refurbishment) - total_of_acquition_refurbishment
    total_financing_and_closing_cost = arrangement_fee + total_of_existing_and_building + interest_charge
    total_project_cost = arrangement_fee + total_of_existing_and_building + interest_charge + price
    total_cost_of_property = price + total_of_existing_and_building
    equity_required = (price + total_of_existing_and_building) - total_of_acquition_refurbishment
    total_sr = (tsf * val['salesComp']) - (tsf * val['salesComp'] * 0.04)
    total_debt_service = total_of_acquition_refurbishment + interest_charge + equity + arrangement_fee
    profit = total_sr - total_debt_service
    # print(profit)
    val["profit"] = round(float(profit), 2)
    val["brokerFees"] = round((tsf * val['salesComp'] * 0.04), 2)
    return val


def get_far(addr, city):
    boro = {
        "Bronx": 2,
        "New York": 1,
        "Brooklyn": 3,
        "Queens": 4,
        "Staten Island": 5
    }
    addr = addr.replace(" ", "%20")
    url = f"http://www.oasisnyc.net/service.svc/lot/geocode?address={addr}&borough={boro[city]}&layerstoselect=169,165,166,164,113,70,62,61,126,127,69,76,205,75,71&_dc=1583170240153"
    resp = requests.get(url)
    js = json.loads(resp.text)
    return js[0][0]['ResidFAR']


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
            val['address'] = " "
        # print(val)
        try:
            val['price'] = js2[list(js2.keys())[0]]['property']['price']
        except:
            val['price'] = 0
        # print(val)
        try:
            val['zipcode'] = js2[list(js2.keys())[0]]['property']['zipcode']
        except:
            val['zipcode'] = ""
        # print(val)
        try:
            val['salesComp'] = 691 # get_sales_comps(js2[list(js2.keys())[0]]['property']['zipcode'])
        except:
            val['salesComp'] = 0
        # print(val)
        try:
            val['lotsize'] = js2[list(js2.keys())[0]]['property']['lotSize']
        except:
            val['lotsize'] = 0
        # print(val)
        try:
            val['buildingSize'] = js2[list(js2.keys())[0]]['property']['livingArea']
        except:
            val['buildingSize'] = 0
        # print(val)
        try:
            val['image'] = js2[list(js2.keys())[0]]['property']['tvCollectionImageLink']
        except:
            val['image'] = ""
        # print(val)
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
        # print(val)
        val['url'] = item
        try:
            val['far'] = get_far(js2[list(js2.keys())[0]]['property']['streetAddress'], js2[list(js2.keys())[0]]['property']['city'])
        except Exception as e:
            print(e)
            val['far'] = 0
        # print(val)
        try:
            val['buildable'] = round(val['lotsize']*val['far'] - val['buildingSize'], 2)
        except:
            val['buildable'] = 0
        # print(val)
        val['on_off'] = "On"
        val['status'] = "For Sale"
        val['profit'] = 0
        val['disable'] = "F"
        val['brokerFees'] = 0
        val['agentEmail'] = " "
        val['zoning'] = " "
        val['level'] = 0
        val['agentCompany'] = " "
        # print(val)
        return val, js2[list(js2.keys())[0]]['property']['city']
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
            print(pages)
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
                    try:
                        assert div.xpath(".//a[contains(@class,'list-card-link')]/@href")[0]
                        try:
                            val, city = get_data(div.xpath(".//a[contains(@class,'list-card-link')]/@href")[0])
                        except Exception as e:
                            print(f"Error in get_data function. Error was {e}")
                            val = {}
                        try:
                            val = get_financial_model(val)
                        except:
                            print(f"Error in get_financial function. Error was {e}")
                            val = False
                        if val != False:
                            if val['profit'] > 0:
                                col.insert_one(val)
                    except:
                        pass

                if stop:
                    pass
                else:
                    get_address(url, current_page+1, result_count)
        except:
            pass
    else:
        pass


if __name__ == "__main__":
    url = "https://www.zillow.com/manhattan-new-york-ny-10030/?searchQueryState=%7B%22pagination%22%3A%7B%7D%2C%22mapBounds%22%3A%7B%22west%22%3A-73.97618346057129%2C%22east%22%3A-73.90872053942871%2C%22south%22%3A40.79803210472891%2C%22north%22%3A40.83878511229598%7D%2C%22mapZoom%22%3A14%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A61644%2C%22regionType%22%3A7%7D%5D%2C%22isMapVisible%22%3Atrue%2C%22filterState%22%3A%7B%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%2C%22land%22%3A%7B%22value%22%3Afalse%7D%7D%2C%22isListVisible%22%3Atrue%7D"
    get_address(url, 1, 0)
    # get_data("https://www.zillow.com/homedetails/20-W-131st-St-New-York-NY-10037/97511846_zpid/")