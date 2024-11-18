from sqlalchemy import *
from sqlalchemy import exc; 
import psycopg2;  
import datetime; 
import time; 
import urllib.request
from FinClasses import *
import json;
import iterModule as im;
from bs4 import BeautifulSoup
import aiohttp
import asyncio
import async_timeout
import string
import schedule
import nltk
import arrow #e.g., a = arrow.get("date"); b = arrow.date(date); delta = b-a; delta.days
import itertools



engine = create_engine('postgresql+psycopg2://postgres:@localhost:5432/forager')
#Initializes engine in Postgres db; psycopg2 is used in conjunction with sqlalchemy

#print(datetime.datetime.now())

companies = dataTable.companies

#filings_table = dataTable.filings

#index = dataTable.index_files

tickers = dataTable.tickers


def label_refs(label_url):

    # Returns a dict of line-item reference tags and their corrsponding plain-text line-item (label) names
    # Must be combined with the tables dict for use in the presentationSchema function

    labsoup = URL(label_url).xml_soup() # Creates a crawlable soup object

    roles = []

    labels = []

    for tag in labsoup.findChildren():

        if tag.name == "loc":

            # Extracts the line-item reference (key) and appends it to the roles list

            role = tag["xlink:href"].split("#")[1].replace("_", ":").lower()

            roles.append(role)

        if tag.name == "link:loc":

            # Extracts the line-item reference (key) and appends it to the roles list

            role = tag["xlink:href"].split("#")[1].replace("_", ":").lower()

            roles.append(role)

        elif tag.name == "label":

            # Extracts the line item plain-text label name and adds it to the labels list

            label = tag.get_text(strip=True)

            labels.append(label)

        elif tag.name == "link:label":

            # Extracts the line item plain-text label name and adds it to the labels list

            label = tag.get_text(strip=True)

            labels.append(label)

    labelrefs = dict(zip(roles, labels)) # Merges the roles and labels lists into a dict

    # Returns the dict

    return labelrefs

def table_refs(xsd_tables_url):

    # Input variable (url) is the SCH (or schema) url
    # Returns a dict of table reference tags and their corrsponding IDs and plain-text table names
    # Must be merged with the labels dict for use in the presentationSchema function

    tables = {}

    soup = URL(xsd_tables_url).xml_soup()

    roletype = Util.role_type(soup)

    for tag in soup.findAll(roletype):

        # Table references fall under the "link:roletype" or "roletype" attributes

        definition = tag.find("link:definition").get_text().split(" - ")[-1] # Formats the plain-text table name

        tag_id = tag["id"] # Extracts the table ID

        role = tag["roleuri"] # Extracts the role (table reference)

        # Upates the tables dict with the table reference (key), it's tag ID and plain-text table name (namespace)

        tables.update({role:{"id":tag_id, "namespace":definition}})




    return tables


def presentationSchema(presentation_url, labels, tables):

    # Synthesizes line-item labels and table names from the "presentation" document, which tells us line-item ordering and
    # parent table information (e.g., Cash is line-item #1 under the Balance Sheet table)

    peasoup = URL(presentation_url).xml_soup()

    table_schema = {}

    pres_type = Util.pres_type(peasoup)

    loc_type = Util.loc_type(peasoup)

    for tag in peasoup.findAll(pres_type):

        # Each presentationlink contains the parent table name for each line-item

        tableref = tag["xlink:role"] # Extract the table name reference tag

        table_name = tables[tableref]["namespace"] # Lookup of the reference tag in the labe_tables dict

        table_id = tables[tableref]["id"] # Not used, but may be useful later

        table_schema.update({table_name:{}})

        order = 0

        for line_item in tag.findChildren():

            # For each parent table, each line-item contains it's own tag

            if line_item.name == loc_type:

                href = line_item.get("xlink:href").split("#")[1].replace("_", ":").lower() # Lookup of the line-item href's for the formal name
                                                                                   # formatted for lookup in the instance doc

                if "abstract" in href.lower():

                    # Abstract line-items are sub-tables; for the purposes of this script, not used

                    pass

                else:

                    # Line items are listed in order in the document, but sub-tables can often skew the numbers when formatting
                    # So this increments each line item by 1

                    order += 1

                    label = labels.get(href) # The plain-text label name is looked up using it's full href value

                    if label != None or label != {} or label != '':

                        # Updates the table schema with the href_value key (instance tag) for the line item, its order in the table and the table name

                        table_schema[table_name].update({href:label})

                    else:

                        for key in labels.keys():

                            if href in  key:

                                table_schema[table_name].update({href:label})




    # Returns the table schema for the instance document

    return table_schema


def extract_instance(instance_url, labels):

    # Synthesises the table names, table line items, dates/periods, and numerical values from the instance document

    soup = URL(instance_url).xml_soup() # Creates crawlable soup object

    periods = {}

    document = []

    line_items = {}

    for tag in soup.findChildren():

        # Sequence first looks up the period context, extracts the tag ID and the period (either a point-in-time date or interval)

        # Tag IDs and interval periods are found under the "xbrli:context" or "context" tag

        # Tag IDS are unique, so they are key-value paired with the period. e.g., {Duration_20180901_20190901_XYZ_abfqr: 20180901_2019091}

        # Tag IDs will be looked up using a line-item's "contextref" attribute to extract the interval or point-in-time date

        # Although the tag IDs themselves often contain the dates used, there is no standard format, and differences can vary widely;
        # However, the interval or period dates in which they reference are tpyically standard. 

        if tag.name == "xbrli:context":

            tag_id = tag["id"] # Extracts tag id key for the period

            period = " ".join(tag.find("xbrli:period").get_text().split("\n")).strip().replace(" ","_").replace("-","") # Extracts/formats the date(s)

            periods.update({tag_id:period}) # Updates the "period" dict for lookup

        elif tag.name == "context":

            # Same as above; filers don't always use the "xbrli:" prefix

            tag_id = tag["id"]

            period = " ".join(tag.find("period").get_text().split("\n")).strip().replace(" ","_").replace("-","")

            periods.update({tag_id:period})

    for tag in soup.findChildren():

        # Iterates through the rest of the document tags


        # Because line items under table names contain numerical values, we only select those tags whose plain-text
        # Can be converted into int() or float(). If conversion is successful, there is a table line-item
        # Otherwise, the try block excepts and moves on to check the next tag

        try:

            n = Util.force_ntype(tag.get_text()) # Forces an int() or float() type for the line-item's plain-text (numerical) value#

            if line_items.get(tag.name) == None:

                line_items.update({tag.name: {periods[tag["contextref"]]: n}})

            else:

                line_items[tag.name].update({periods[tag["contextref"]]:n})


        except:

            pass

    return line_items

   
def synthesize_financial_document(schema, line_items):

    tables = {}

    for table, e in schema.items():

        tables.update({table:{}})

        for href, label in e.items():

            if line_items.get(href) == None:

                pass

            else:

                # Note: if you want to display the verbose line-item name, 
                # use label instead of href on the next code line, as well 
                # as line 297

                tables[table].update({href:{}})

                elements = []

                dates = []

                for date, val in line_items.get(href).items():

                    elements.append({"date":date, "val": val})


                for elem in elements:

                    if len(elem["date"].split("_")) == 1:

                        dates.append(elem["date"])

                    else:

                        split = elem["date"].split("_")

                        a = arrow.get(split[0])

                        b = arrow.get(split[1])

                        delta = b-a

                        n = delta.days

                        if n > 270:

                            dates.append(elem["date"])


                try:

                    maxd = max(dates)

                except:

                    pass

    

                for elem in elements:

                    try:

                        if elem["date"] == maxd:

                            tables[table][href].update(elem)

                    except:

                        pass



    return tables


def retrieve_tables(index_url):

    xbrl = IndexUrl(index_url).get_xbrl_filings()

    if xbrl.get('EX-101.INS') == None:

        return None

    else:

        # Issue with merging the labels and tables dicts, as some values overwrite each other and we're left with
        # for example, Cash and Cash Equivalents only displaying as a child to the Cash Flow Statement

        presentation_url = xbrl.get("EX-101.PRE")

        instance_url = xbrl.get('EX-101.INS')

        xsd_tables_url = xbrl.get('EX-101.SCH')

        labels_url = xbrl.get('EX-101.LAB')

        presentation_url = xbrl.get('EX-101.PRE')

        labels = label_refs(labels_url)

        tables = table_refs(xsd_tables_url)

        schema = presentationSchema(presentation_url, labels, tables) # Synthesize line items and tables into a schema

        line_items = extract_instance(instance_url, labels) # Print the synthesized document with line items, tables, and values

        doc = synthesize_financial_document(schema, line_items)

        # Note: when entering into a db, don't forget json.dumps(doc)
        
        return doc








file = "/Users/loremipsum/Desktop/10Ks.txt"

with open(file, "r") as f:

    for line in f.readlines()[:101]:

        index_url = line.strip()

        doc = retrieve_tables(index_url)

        if doc == None:

            pass

        else:

            print(index_url, "\n", doc, "\n\n\n\n\n\n\n")





"""
urls = ["https://www.sec.gov/Archives/edgar/data/1001385/0001437749-18-004857-index.htm",
        "https://www.sec.gov/Archives/edgar/data/1001902/0001193125-18-045618-index.htm",
        "https://www.sec.gov/Archives/edgar/data/1003410/0000783280-18-000012-index.htm",
        "https://www.sec.gov/Archives/edgar/data/100517/0001193125-18-054235-index.htm",   
        "https://www.sec.gov/Archives/edgar/data/1006424/0001437749-18-004799-index.htm",
        "https://www.sec.gov/Archives/edgar/data/1009829/0001157523-18-000578-index.htm", 
        "https://www.sec.gov/Archives/edgar/data/1010612/0001193125-18-067150-index.htm", 
        "https://www.sec.gov/Archives/edgar/data/1012019/0001437749-18-003630-index.htm", 
        "https://www.sec.gov/Archives/edgar/data/101295/0001171843-18-002183-index.htm", 
        "https://www.sec.gov/Archives/edgar/data/1013238/0001193125-18-094094-index.htm"] 


for url in urls[:1]:

    doc = retrieve_tables(url)

    for k, v in doc.items():

        print(k)

        for k, v in v.items():

            print("\t", k, "\n", "\t\t", v)




    xbrl = IndexUrl(url).get_xbrl_filings()

    instance_url = xbrl.get("EX-101.INS")

    soup = URL(instance_url).xml_soup()

    labels_url = xbrl.get("EX-101.LAB")

    tables_url = xbrl.get("EX-101.SCH")

    presentation_url = xbrl.get("EX-101.PRE")

    instance_url = xbrl.get("EX-101.INS")

    labels = label_refs(labels_url)

    tables = table_refs(tables_url)

    schema = presentationSchema(presentation_url, labels, tables)

    instance = extract_instance(instance_url, labels)

    print(instance, "\n\n")

"""









































"""
######################################################
# This is a scheduler script
######################################################

def job():
    while True:
        if Util.marketisopen():
            print("Market is open!")
        else:
            print("Market is closed.")
            break


#schedule.every().day.at("13:45").do(job)

schedule.every(1).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(60) # wait 5 seconds
"""


"""
######################################################
# This is for running against IEX Cloud Asynchronously 
######################################################

# Async coroutine for running prices logs in a parallel
async def download_coroutine(engine, tickers, session, symbol):
    with async_timeout.timeout(10):
        url = "https://cloud.iexapis.com/stable/stock/%s/quote?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % symbol

        async with session.get(url) as response:
            html = await response.read()
            data = json.loads(html)

            exchange = data["primaryExchange"]
            price = data["latestPrice"]
            cap = data["marketCap"]
            peratio = data["peRatio"]
            

            u = update(tickers).where(tickers.c.ticker == symbol)

            u1 = u.values(latestprice=price)
            u2 = u.values(exchange=exchange)
            u3 = u.values(marketcap=cap)
            u4 = u.values(peratio=peratio)
            engine.execute(u1)
            engine.execute(u2)
            engine.execute(u3)
            engine.execute(u4)
            print(symbol, price)
            return await response.release()
 
async def main(loop):

    symbols = [row.ticker for row in engine.execute(select([tickers])).fetchall()]
 
    async with aiohttp.ClientSession(loop=loop) as session:
        for symbol in symbols:
        	asyncio.ensure_future(download_coroutine(engine, tickers, session, symbol))
       		await asyncio.sleep(1/50)
 
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
"""

