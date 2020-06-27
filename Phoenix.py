from lxml import etree
from math import ceil
from tqdm import tqdm
import cloudscraper
import requests
import pymongo
import json
import re
import io


client = pymongo.MongoClient("YOUR_MONGODB_LINK_HERE")
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
    existing = bldsize * 0
    buildable = val['buildable'] * 150
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
    total_sr = (tsf * val['salesComp']) - (tsf * val['salesComp'] * 0.03)
    total_debt_service = total_of_acquition_refurbishment + interest_charge + equity + arrangement_fee
    profit = total_sr - total_debt_service
    # print(profit)
    val["profit"] = round(float(profit), 2)
    val["brokerFees"] = (tsf * val['salesComp'] * 0.03)
    return val


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
        try:
            val['price'] = js2[list(js2.keys())[0]]['property']['price']
        except:
            val['price'] = 0
        try:
            val['zipcode'] = js2[list(js2.keys())[0]]['property']['zipcode']
        except:
            val['zipcode'] = ""

        try:
            val['salesComp'] = 253 # get_sales_comps(js2[list(js2.keys())[0]]['property']['zipcode'])
        except:
            val['salesComp'] = 0
        try:
            val['lotsize'] = js2[list(js2.keys())[0]]['property']['lotSize']
        except:
            val['lotsize'] = 0

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
        return val, js2[list(js2.keys())[0]]['property']['streetAddress'], js2[list(js2.keys())[0]]['property']['city'] + ", " + js2[list(js2.keys())[0]]['property']['state']
    except:
        return False


def get_zoning_data(val, addr, addr2):
    zoning_value = {
        "RE-35": 30,
        "R1-18": 25,
        "R1-10": 50,
        "R1-8": 50,
        "R1-6": 50,
        "R-2": 50,
        "R-3": 50,
        "R-3A": 50,
        "R-4": 50,
        "R-5": 50,
    }
    headers = {"apikey": "aa5a8218087e1dfcf7a262d1ab615e5f", "accept": "application/json"}
    response = requests.get(
        f"https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/expandedprofile?address1={addr}&address2={addr2}",
        headers=headers)
    js = json.loads(response.text)
    try:
        val['zoning'] = js['property'][0]['lot']['siteZoningIdent']
    except:
        val['zoning'] = " "

    try:
        val['buildingSize'] = js['property'][0]['building']['size']['bldgSize']
    except:
        val['buildingSize'] = 0
    try:
        val['level'] = js['property'][0]['building']['summary']['levels']
    except:
        val['level'] = 0

    try:
        val['buildable'] = (val['lotsize'] * (zoning_value[val['zoning']]/100)) - val['buildingSize']
    except:
        val['buildable'] = 0

    val['on_off'] = "On"
    val['status'] = "For Sale"
    val['profit'] = 0
    val['disable'] = "F"
    val['brokerFees'] = 0
    val['agentEmail'] = " "
    val['far'] = 0
    val['agentCompany'] = " "
    return val


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
                        val, addr, addr2 = get_data(div.xpath(".//a[contains(@class,'list-card-link')]/@href")[0])
                        val = get_zoning_data(val, addr, addr2)
                        val = get_financial_model(val)
                        # print(val)
                        if val != False:
                            if val['profit'] > 0:
                                col.insert_one(val)
                    except Exception as e:
                        print(e)
                if stop:
                    pass
                else:
                    get_address(url, current_page+1, result_count)
        except:
            pass
    else:
        pass


if __name__ == "__main__":
    url = "https://www.zillow.com/phoenix-az-85033/?searchQueryState=%7B%22pagination%22%3A%7B%7D%2C%22mapBounds%22%3A%7B%22west%22%3A-112.24306496057129%2C%22east%22%3A-112.17560203942871%2C%22south%22%3A33.469551848206464%2C%22north%22%3A33.514460890590044%7D%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A94749%2C%22regionType%22%3A7%7D%5D%2C%22isMapVisible%22%3Atrue%2C%22mapZoom%22%3A14%2C%22filterState%22%3A%7B%22con%22%3A%7B%22value%22%3Afalse%7D%2C%22apa%22%3A%7B%22value%22%3Afalse%7D%2C%22sort%22%3A%7B%22value%22%3A%22globalrelevanceex%22%7D%2C%22land%22%3A%7B%22value%22%3Afalse%7D%2C%22tow%22%3A%7B%22value%22%3Afalse%7D%2C%22manu%22%3A%7B%22value%22%3Afalse%7D%7D%2C%22isListVisible%22%3Atrue%7D"
    get_address(url, 1, 0)
