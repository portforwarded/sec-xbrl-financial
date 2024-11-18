from bs4 import BeautifulSoup
import urllib.request
import iterModule as im
from sqlalchemy import *
import json
import datetime
import timeout_decorator
from sqlalchemy.dialects.postgresql import TSVECTOR
import psycopg2
import string


"""
The classes in this module primarily deal with ways to manipulate central index keys, 
ticker symbols, and index urls. Obviously, one of those inputs will dictate which class
it belongs to. There are some other general classes included (one that lets you 
call every symbol available to query, for example). For general, non-class-based
functions, see the "helper" module. 
"""


################################################################################################################
#BEGIN INDEXURL CLASS

# This class includes methods that are intended to be used on index urls 

################################################################################################################


class IndexUrl(object):
	#This class extracts information from index urls only
	#1. Central Index Key of the company associated with the url
	#2. Filing ID associated with the url
	#3. Date of the filing
	#4. Form # associated with the filing
	#5. Name of the company associated with the url
	#6. All metadata for the filing (1–5)
	#7 All filings and metadata associated with url, returned in dictionary format

	def __init__(self, url):
		# Initialize class

		self.url = url


	def get_cik(self):
		# Returns the Central Index Key associated with the index url

		try:
			return self.url.split("/")[6]

		except Exception:

			print("Check url for format: " + self.url)


	def get_filing_id(self):
		# Returns the id of the index url (filing)

		return self.url.split("/")[-1].split("-i")[0].strip()


	
	def get_date(self):
		# Returns date associated with the index url (filing)

		try:
			soup = URL(self.url).html_soup()

			return soup.find("div", {"class":"formGrouping"}).find_all("div")[1].get_text().split()[0]

		except Exception:

			print("Date not found or None. Check " + self.url + " for more information.")



	def get_form(self):
		# Returns the form number associated with the index url (filing)

		try:
			soup = URL(self.url).html_soup()

			return soup.find("div", {"id":"formName"}).get_text().split(" - ")[0].strip().split("Form")[1].strip()

		except Exception:

			print("Form not found or None. Check " + self.url + " for more information.")


	def get_name(self):
		# Returns name of the company or indivual's name associated with the index url

		owner = "https://www.sec.gov/cgi-bin/browse-edgar?CIK=%s&owner=exclude&action=getcompany&Find=Search" % self.url.split("/")[6]
		soup = URL(self.url).html_soup()
		name = soup.find("span", {"class":"companyName"}).get_text().split("CIK")[0].upper().replace("(FILER)","").strip()
		return name

	def get_industry(self):
		# Returns a dictionary object with {Standard Industrial Code: Description}

		try:
			owner = "https://www.sec.gov/cgi-bin/browse-edgar?CIK=%s&action=getcompany" % self.url.split("/")[6]
			soup = URL(owner).html_soup()
			for tag in soup.find("div", {"class":"companyInfo"}).find("p", {"class":"identInfo"}).find_all("a"):
				if "SIC=" in str(tag):
					sic = tag.get_text(strip=True)
					return {"SIC":sic, "industry": im.sics[sic]}
				else:
					return None
		except Exception:
			print("Check url for format: " + self.url)

	def get_loc_state(self):
		owner = "https://www.sec.gov/cgi-bin/browse-edgar?CIK=%s&owner=exclude&action=getcompany&Find=Search" % self.url.split("/")[6]
		pass


	def get_meta(self):
		#Returns a dictionary of the name, central index key, accession # (filing id), form #, and date of the filing

		name = self.get_name()
		cik = self.get_cik()
		filing_id = self.get_filing_id()
		soup = URL(self.url).html_soup()
		form = soup.find("div", {"id":"formName"}).get_text().split(" - ")[0].strip().split("Form")[1].strip()
		date = soup.find("div", {"class":"formGrouping"}).find_all("div")[1].get_text().split()[0]
		return {"name":name, "CIK":cik, "accession":filing_id, "form":form, "date":date}

	def get_filings(self):
		#Returns a list of filings in dictionaries (a list of dictionaries),
		# excluding XBRL filings

		#Note: Some information is redundant, but it's necessary for conversion to the API. 
		soup = URL(self.url).html_soup()
		url = self.url
		cik = self.get_cik()
		filing_id = self.get_filing_id()
		form = soup.find("div", {"id":"formName"}).get_text().split(" - ")[0].strip().split("Form")[1].strip()
		date = soup.find("div", {"class":"formGrouping"}).find_all("div")[1].get_text().split()[0]

		filings = []

		# Pulls first listed document; usually the Primary (but sometimes an exhibit filing)
		for tag in soup.find("table", {"summary":"Document Format Files"}).find_all("tr")[1:2]:
			    base = "https://www.sec.gov"
			    entry = tag.find_all("td")
			    row_num = entry[0].get_text()
			    link = base + entry[2].find("a").get("href")
			    sub_form = entry[3].get_text(strip=True)
			    if link[-1] == "/":
			    	 filings.append({"form":form, "accession":filing_id, "description":im.form_desc[form], "type":"primary", "date":date, "url":link + filing_id + ".txt"})    
			    elif ".jpg" in link or ".png" in link or ".gif" in link or ".xfd" in link:
			    	pass
			    else:
			    	try:
			    	 	filings.append({"form":sub_form, "accession":filing_id, "description":im.form_desc[sub_form], "type":"primary", "date":date, "url":link})
			    	except Exception:
			    		try:
			    			filings.append({"form":sub_form, "accession":filing_id, "description":im.exhibit_codes[sub_form.split(".")[0]], "type":"exhibit", "date":date, "url":link})
			    		except Exception:
			    			try:
			    				filings.append({"form":form, "accession":filing_id, "description":im.form_desc[form], "type":"primary", "date":date, "url":link})
			    			except Exception:
			    				pass


		# Pulls the 2nd+ listed documents; usually Exhibits, (but sometimes a Primary filing)
		for tag in soup.find("table", {"summary":"Document Format Files"}).find_all("tr")[2:-1]:
		    base = "https://www.sec.gov"
		    entries = tag.find_all("td")
		    row_num = entries[0].get_text()
		    link = base + entries[2].find("a").get("href")
		    sub_form = entries[3].get_text()
		    if link[-1] == "/":
		    	 pass
		    elif ".jpg" in link or ".png" in link or ".gif" in link or ".xfd" in link:
		    	pass

		    else:
		    	try:
		    		filings.append({"form":sub_form, "accession":filing_id, "description":im.exhibit_codes[sub_form], "type":"exhibit", "date":date, "url":link})
		    	except Exception:
		    		try:
		    			filings.append({"form":sub_form, "accession":filing_id, "description":im.exhibit_codes[sub_form.split(".")[0]], "type":"exhibit", "date":date, "url":link})
		    		except Exception:
		    			try:
		    				filings.append({"form":sub_form, "accession":filing_id, "description":im.form_desc[sub_form], "type":"primary", "date":date, "url":link})
		    			except Exception:
		    				pass

		return filings


	def get_xbrl_filings(self):
			#Returns a list of all xbrl filings in dictionary (a list of dictionaries)

			soup = URL(self.url).html_soup()
			url = self.url
			cik = self.get_cik()
			filing_id = self.get_filing_id()
			form = soup.find("div", {"id":"formName"}).get_text().split(" - ")[0].strip().split("Form")[1].strip()
			date = soup.find("div", {"class":"formGrouping"}).find_all("div")[1].get_text().split()[0]

			filings = {}
			try:
				for tag in soup.find("table", {"summary":"Data Files"}).find_all("tr")[1:]:
				# XML files are located in the "Data Files" section (excepted if doesn't exist)
					try:
						# Parses out the link and descirption
						nbase = "https://www.sec.gov"
						entry = tag.find_all("td")
						row = entry[0].get_text()
						description = entry[1].get_text()
						link = nbase + entry[2].find("a").get("href")
						sub_form = entry[3].get_text()
						if description == '' or description == None:
							description = "XBRL"
						filings.update({sub_form:link})
					except Exception:
						pass
			except Exception:
				pass
			return filings


	def current(self):
		#Used on Current Report 8-K and 8-K/A index files only

		keywords = ''
		soup = URL(self.url).html_soup() # returns a soup html object

		# Locates the item information in the index url
		for tag in soup.find_all("div", {"class":"formGrouping"})[2:]:
	   		keywords += tag.find("div",{"class":"info"}).get_text("|")
		return keywords



################################################################################################################
#BEGIN URL CLASS (USED FOR GENERIC URLS)

# This class includes methods that are intended to be used on generic urls (typicall, individual filings)

################################################################################################################



class URL(object):

	# object is standard, individual filing url
	# methods are often form-specific. For example, 
	# get_ownership is only valid for forms 3 and 3/A;
	# update_change_ownership is only valid for forms 4, 4/A, 5, and 5/A
	# Be sure to use the right method, depending on the form or filing_type, 
	# otherwise you'll throw an exception or return None. 
	# html_soup and xml_soup run on all .htm(l) and .xml types

	def __init__(self, url):
		# Initialize class

		self.url = url

	def html_soup(self):
		# Creates soup object (readable html) from the url

		if "ix?doc=" in self.url:
			url = "".join(self.url.split("/ix?doc="))
			# Returns "soup" html object for parsing

			html = urllib.request.urlopen(url, timeout=60).read() # Reads url object into string
			soup = BeautifulSoup(html, "html.parser") # Creates a parsable object with BeautifulSoup

		else:

			html = urllib.request.urlopen(self.url, timeout=60).read() # Reads url object into string
			soup = BeautifulSoup(html, "html.parser") # Creates a parsable object with BeautifulSoup

		return soup #Returns object


	def xml_soup(self):
		# Returns "soup" xml object for parsing
		xml = urllib.request.urlopen(self.url, timeout=60).read() # Reads url object into string
		soup = BeautifulSoup(xml, "lxml") # Creates a parsable object with BeautifulSoup
		return soup #Returns object


	@timeout_decorator.timeout(2)
	def extract_text(self):
		"""
		Consider using @timeout_decorator.timeout(#) for first passes.

		for url in urls:
			if __name__ == '__main__':
				extract_text(url)
		"""

		if "ix?doc=" in self.url:
			soup = URL(self.url).html_soup() # Creates HTML object for crawling
			external_span = soup.find('body')

			# Remove unwanted XBRL tags from plain text
			unwanted = external_span.find('ix:header')
			unwanted.extract()

			return " ".join(external_span.get_text("\r\n").split()) # Returns plain text
		else:
			soup = URL(self.url).html_soup() # Creates HTML object for crawling
			return " ".join(soup.get_text("\r\n").split()) # Returns plain text


	def load_json(self):
		req = urllib.request.urlopen(self.url).read()
		data = json.loads(req)
		return data


	def ix_files(self):
		# Used with master.idx urls only
		# Function opens index file url (daily or quarterly) and returns
		# Dictionary with each filing
		# Includes CIK, Name, Form, Date, and Index Url
		files = []
		data = urllib.request.urlopen(self.url)
		for line in data.readlines():
			# Each line containts the cik, name, form, date and url of a filing
			try:
				base = "https://www.sec.gov/Archives/"
				if ".txt" in str(line):
					# Only entries with .txt are valid
					# Separates the values in to a single-entry dictionary

					line = line.decode()
					line = str(line).strip().split("|")
					cik = line[0]
					name = " ".join(line[1].split()).replace("/","").replace("\\","").upper()
					form = line[2]
					date = line[3]
					index_url = base + line[4].replace(".txt","-index.htm")

					# Appends the single-entry dictionary (filing) into a list of filings
					files.append({"cik":int(cik), "name":name, "form":form, "date":date, "url":index_url})

			except Exception:
				pass
		return files # Returns a list of the filings


	def ix_feed(self):
		# When the RSS url is accessed, function generates
		# a feed with the most recent filings in the format:
		#  {"name":name, "form":form, "date":date, "url":url}

		soup = URL(self.url).xml_soup()
		filings = []
		for tag in soup.find_all("entry"):

			# For each entry in the feed, locates the cik, url, and date

			filing = {}
			link = tag.find("link")["href"].split("/")
			link = "/".join(link[:7] + link[-1:])
			cik = IndexUrl(link).get_cik()
			filing.update({"cik":int(cik)})
			date = tag.find("summary").get_text().split("</b>")[1].split("<b>")[0].strip()

			for title in tag.find("title"):
				# Locates the name and form, updates the filing dict

				name = title.split(" - ")[1].split(" (")[0].replace("/", "").replace("\\", "").upper()
				filing.update({"name":name, "form":title.split(" - ")[0].strip()})

			# Updates the filing dict wih the remaining values for url and date
			filing.update({"date":date})
			filing.update({"url":link})

			# Appends the filing dict to the list of filings
			filings.append(filing)

		return filings # Returns a list of filings



	def get_ownership(self):
		"""
		Form 3, 3/As only.
		"""
		url = "/".join(self.url.split("/")[:8] + self.url.split("/")[-1:])
		try:
			entry = {}
			info = {}
			activity = []
			soup = URL(url).xml_soup()

			for tag in soup.find_all("issuer"):
				issuercik = int(tag.find("issuercik").get_text(strip=True))
				symbol = tag.find("issuertradingsymbol").get_text(strip=True)
				info.update({"issuercik":issuercik, "ticker":symbol})

			ownercik = soup.find("rptownercik").get_text(strip=True) #Reporting person's central index_key
			name = soup.find("rptownername").get_text(strip=True)#Reporting persons name
			info.update({"reportingownercik":int(ownercik), "reportingownername":name.title()})
			#If reporting person is a director
			if soup.find("isdirector") and soup.find("isdirector").get_text(strip=True) == 'true':
				director = 1
				info.update({"reportingisdirector":director})
			elif soup.find("isdirector") and soup.find("isdirector").get_text(strip=True) == 'false':
				director = 0
				info.update({"reportingisdirector":director})
			elif soup.find("isdirector"):
				director = soup.find("isdirector").get_text(strip=True)
				info.update({"reportingisdirector":director})
			else:
				director = 0
				info.update({"reportingisdirector":director})

			#If reporting person is an officer
			if soup.find("isofficer") and soup.find("isofficer").get_text(strip=True) == 'true':
				director = 1
				info.update({"reportingisofficer":director})
			elif soup.find("isofficer") and soup.find("isofficer").get_text(strip=True) == 'false':
				director = 0
				info.update({"reportingisofficer":director})
			elif soup.find("isofficer"):
				director = soup.find("isofficer").get_text(strip=True)
				info.update({"reportingisofficer":director})
			else:
				director = 0
				info.update({"reportingisofficer":director})


			#If reporting person is a 10% or more owner
			if soup.find("istenpercentowner") and soup.find("istenpercentowner").get_text(strip=True) == 'true':
				director = 1
				info.update({"reportingistenpctowner":director})
			elif soup.find("istenpercentowner") and soup.find("istenpercentowner").get_text(strip=True) == 'false':
				director = 0
				info.update({"reportingistenpctowner":director})
			elif soup.find("istenpercentowner"):
				director = soup.find("istenpercentowner").get_text(strip=True)
				info.update({"reportingistenpctowner":director})
			else:
				director = 0
				info.update({"reportingistenpctowner":director})

		except Exception:
			pass
		if info == {}:
			pass
		else:
			return info

	def update_change_ownership(self):
		"""
		Generally, use the following:

		p = select([table]).distinct(table.c.filing_url)\
		.where(and_(table.c.financial_data == None, or_(table.c.form == "4", 
		table.c.form == '4/A', table.c.form == '5', table.c.form == '5/A')))

		for row in engine.execute(p).fetchall():
			if fm.update_change_ownership(row.filing_url) == {}:
				pass
			else:
				filer = fm.update_change_ownership(row.filing_url)
				u = update(table).where(table.c.filing_url == row.filing_url)
				u = u.values(financial_data=json.dumps(filer), filing_type='XML')
				engine.execute(u)
				print(row.filing_url)

		Don't forget about soup.findChildren() when running tests. :)

		"""
		url = "/".join(self.url.split("/")[:8] + self.url.split("/")[-1:])
		try:
			entry = {}
			info = {}
			activity = []
			soup = URL(url).xml_soup()
			for tag in soup.find_all("issuer"):
				issuercik = int(tag.find("issuercik").get_text(strip=True))
				symbol = tag.find("issuertradingsymbol").get_text(strip=True)
				info.update({"issuercik":issuercik, "ticker":symbol})

			ownercik = soup.find("rptownercik").get_text(strip=True) #Reporting person's central index_key
			name = soup.find("rptownername").get_text(strip=True)#Reporting persons name
			info.update({"reportingownercik":int(ownercik), "reportingownername":name.title()})

			#If reporting person is a director
			if soup.find("isdirector") and soup.find("isdirector").get_text(strip=True) == 'true':
				director = 1
				info.update({"reportingisdirector":director})
			elif soup.find("isdirector") and soup.find("isdirector").get_text(strip=True) == 'false':
				director = 0
				info.update({"reportingisdirector":director})
			elif soup.find("isdirector"):
				director = soup.find("isdirector").get_text(strip=True)
				info.update({"reportingisdirector":director})
			else:
				director = 0
				info.update({"reportingisdirector":director})

			#If reporting person is an officer
			if soup.find("isofficer") and soup.find("isofficer").get_text(strip=True) == 'true':
				director = 1
				info.update({"reportingisofficer":director})
			elif soup.find("isofficer") and soup.find("isofficer").get_text(strip=True) == 'false':
				director = 0
				info.update({"reportingisofficer":director})
			elif soup.find("isofficer"):
				director = soup.find("isofficer").get_text(strip=True)
				info.update({"reportingisofficer":director})
			else:
				director = 0
				info.update({"reportingisofficer":director})


			#If reporting person is a 10% or more owner
			if soup.find("istenpercentowner") and soup.find("istenpercentowner").get_text(strip=True) == 'true':
				director = 1
				info.update({"reportingistenpctowner":director})
			elif soup.find("istenpercentowner") and soup.find("istenpercentowner").get_text(strip=True) == 'false':
				director = 0
				info.update({"reportingistenpctowner":director})
			elif soup.find("istenpercentowner"):
				director = soup.find("istenpercentowner").get_text(strip=True)
				info.update({"reportingistenpctowner":director})
			else:
				director = 0
				info.update({"reportingistenpctowner":director})



			"""
			BREAK: Issuer and reporting information above ("info"); reporting activity below ("activity")


			#NON-DERIVATIVE TRANSACTION
			"""	
			try:
				for tag in soup.find_all("nonderivativetransaction"):

					#Title of security
					if not tag.find("securitytitle"):
						security = 'n/a'
					elif tag.find("securitytitle"):
						if tag.find("securitytitle").get_text(strip=True) == '':
							security = 'n/a'
						else:
							security = tag.find("securitytitle").get_text(strip=True)
					
					#Transaction code
					if not tag.find("transactioncode"):
						code = 'n/a'
					elif tag.find("transactioncode"):
						if tag.find("transactioncode").get_text(strip=True) == '':
							code = 'n/a'
						else:
							code = tag.find("transactioncode").get_text(strip=True)

					#Number of shares/securities
					if not tag.find("transactionshares"):
						shares = 0.0
					elif tag.find("transactionshares"):
						if tag.find("transactionshares").get_text(strip=True) == '':
							shares = 0.0
						else:
							shares = tag.find("transactionshares").get_text(strip=True)
				
					#Securities Acquired or Disposed
					if not tag.find("transactionacquireddisposedcode"):
						acqdisp = 'n/a'
					elif tag.find("transactionacquireddisposedcode"):
						if tag.find("transactionacquireddisposedcode").get_text(strip=True) == '':
							acqdisp = 'n/a'
						elif tag.find("transactionacquireddisposedcode").get_text(strip=True) == "A":
							acqdisp = "Acquired"
						elif tag.find("transactionacquireddisposedcode").get_text(strip=True) and tag.find("transactionacquireddisposedcode").get_text(strip=True) == "D":
							acqdisp = "Disposed"

					#Securities price at time of transaction
					if not tag.find("transactionpricepershare"):
						pps = 0.0
					elif tag.find("transactionpricepershare"):
						if tag.find("transactionpricepershare").get_text(strip=True) == '':
							pps = 0.0
						else:
							pps = tag.find("transactionpricepershare").get_text(strip=True)

					#Ending shares of reporting owner
					if not tag.find("sharesownedfollowingtransaction"):
						end_shares = 0.0
					elif tag.find("sharesownedfollowingtransaction"):
						if tag.find("sharesownedfollowingtransaction").get_text(strip=True) == '':
							end_shares = 0.0
						else:
							end_shares = tag.find("sharesownedfollowingtransaction").get_text(strip=True)

					#Matches transaction code in database
					for k, v in im.transaction_codes.items():
						if k == code:
							activity.append({"security":security.lower().replace('"',""), "type":v, "amount":shares, "transaction":acqdisp, "price":pps, "end":end_shares})
			except Exception:
				pass


			#DERIVATIVE TRANSACTION

			try:
				for tag in soup.find_all("derivativetransaction"):

					#Title of security
					if not tag.find("securitytitle"):
						security = 'n/a'
					elif tag.find("securitytitle"):
						if tag.find("securitytitle").get_text(strip=True) == '':
							security = 'n/a'
						else:
							security = tag.find("securitytitle").get_text(strip=True)
					
					#Transaction code
					if not tag.find("transactioncode"):
						code = 'n/a'
					elif tag.find("transactioncode"):
						if tag.find("transactioncode").get_text(strip=True) == '':
							code = 'n/a'
						else:
							code = tag.find("transactioncode").get_text(strip=True)
					#Number of shares/securities
					if not tag.find("transactionshares"):
						shares = 0.0
					elif tag.find("transactionshares"):
						if tag.find("transactionshares").get_text(strip=True) == '':
							shares = 0.0
						else:
							shares = tag.find("transactionshares").get_text(strip=True)
				
					#Securities Acquired or Disposed
					if not tag.find("transactionacquireddisposedcode"):
						acqdisp = 'n/a'
					elif tag.find("transactionacquireddisposedcode"):
						if tag.find("transactionacquireddisposedcode").get_text(strip=True) == '':
							acqdisp = 'n/a'
						elif tag.find("transactionacquireddisposedcode").get_text(strip=True) == "A":
							acqdisp = "Acquired"
						elif tag.find("transactionacquireddisposedcode").get_text(strip=True) and tag.find("transactionacquireddisposedcode").get_text(strip=True) == "D":
							acqdisp = "Disposed"

					#Securities price at time of transaction
					if not tag.find("transactionpricepershare"):
						pps = 0.0
					elif tag.find("transactionpricepershare"):
						if tag.find("transactionpricepershare").get_text(strip=True) == '':
							pps = 0.0
						else:
							pps = tag.find("transactionpricepershare").get_text(strip=True)

					#Ending shares of reporting owner
					if not tag.find("sharesownedfollowingtransaction"):
						end_shares = 0.0
					elif tag.find("sharesownedfollowingtransaction"):
						if tag.find("sharesownedfollowingtransaction").get_text(strip=True) == '':
							end_shares = 0.0
						else:
							end_shares = tag.find("sharesownedfollowingtransaction").get_text(strip=True)

					#Matches transaction code in database
					for k, v in im.transaction_codes.items():
						if k == code:
							activity.append({"security":security.lower().replace('"',""), "type":v, "amount":shares, "transaction":acqdisp, "price":pps, "end":end_shares})
			except Exception:
				pass
		except Exception:
			pass
		if info == {} or activity == []:
			pass
		else:
			entry.update({"info":info})
			entry.update({"activity":activity})
		if entry == {}:
			pass
		else:
			return entry

	def verbose(self):
		vb_desc = {}

		# Sets a "base" url for tags with only suffix urls
		base = "/".join(self.url.split("/")[:-1]).replace("/ix?doc=","") + "/" 


		soup = URL(self.url).html_soup() # converts to soup object

		for tag in soup.find_all("a", href=True):
			#Locates href values in html
			link = tag["href"].split("#")[0]

			text = " ".join(tag.get_text("\n").split())

			if Util.linkIsBad(link):
				# If the link is bad (meaning irrelevant), skips 
				pass
			elif Util.tagIsBad(text):
				# If the tag is bad, skips 
				pass
			else:
				if Util.isSuffix(link):
					# If the link is a suffix, appends the prefix (base) url
					vb_desc.update({base + link:text})
				else:
					vb_desc.update({link:text})
		if vb_desc == {}:
			return None
		else:
			return vb_desc



################################################################################################################
#BEGIN CIK CLASS

# This class includes methods that are intended to be used on central index keys

################################################################################################################



class CIK(object):

	#object must be central index key in integer format

	def __init__(self, cik):
		# Initialize class
		self.cik = cik

	def get_name(self):
		# Retrieves the name of the filer based on the central_index_key
		try:
			url = "https://www.sec.gov/cgi-bin/browse-edgar?CIK=%d&owner=exclude&action=getcompany&Find=Search" % self.cik
			soup = URL(url).html_soup()
			name = soup.find("span", {"class":"companyName"}).get_text().split("CIK")[0].strip().upper()
			return name
		except TypeError:
			pass


	def get_ticker(self):
		# Retrieves the central index key of the company, using the ticker

	    ciksticks = {}
	    for v in URL(Symbols.tickercik_url).load_json().values():
	        ciksticks.update({v["cik_str"]:v["ticker"]})
	    try:
	        return ciksticks[self.cik]
	    except KeyError:
	        return None


	def get_industry(self):
		# Returns a dictionary of the Standard Industrial Code number and its description
		try:
			code = im.ciksics[self.cik]
			industry = im.sics[code]
			return {"SIC":code, "industry":industry}
		except KeyError:
			try:
				owner = "https://www.sec.gov/cgi-bin/browse-edgar?CIK=%d&action=getcompany" % self.cik
				soup = URL(owner).html_soup()
				for tag in soup.find("div", {"class":"companyInfo"}).find("p", {"class":"identInfo"}).find_all("a"):
					if "SIC=" in str(tag):
						sic = tag.get_text(strip=True)
						return {"SIC":sic, "industry": im.sics[sic]}
			except Exception:
				pass

	def get_state(self):
		# Returns the two-letter state abbreviation using the cik
		try:
			owner = "https://www.sec.gov/cgi-bin/browse-edgar?CIK=%d&action=getcompany" % self.cik
			soup = URL(owner).html_soup()
			for tag in soup.find("div", {"class":"companyInfo"}).find("p", {"class":"identInfo"}).find_all("a"):
				if "State=" in str(tag):
					state = tag.get_text(strip=True)
					return state
		except Exception:
			pass



	def get_index_files(self):
		filings = []
		# Returns a full list of index files based on the CIK entered as a variable

		base = "https://www.sec.gov/Archives/edgar/data/%d/" % self.cik
		cik_url = "https://www.sec.gov/Archives/edgar/data/%d/index.json" % self.cik

		#Locate the filing ids in the directory
		data = json.loads(urllib.request.urlopen(cik_url).read())["directory"]["item"]
		for filing in data:
			# Gather the filing_id inormation, appends single-entry json objects to list
			try:
				date = filing['last-modified'].split()[0]
				filing_id = filing["name"][:-8] + "-" + filing["name"][-8:-6] + "-" + filing["name"][-6:]
				url = base + filing_id + "-index.htm"
				form = IndexUrl(url).get_form()

				# Appends
				filings.append({"cik":self.cik, "url":url, "form":form, "date":date})
			except Exception as e:
				print(e)
		return filings # Returns filings


################################################################################################################
#BEGIN TICKER CLASS

# This class includes methods that are intended to be used on ticker symbols 

################################################################################################################


class Ticker(object):
	# object must be a stock ticker

	# This class extracts information using ticker symbols
	#1. Name of the company associated with the ticker
	#2. Central Index Key associated with the ticker
	#3. Latest news associated with the ticker
	#4. Latest market quote (price) associated with the ticker
	#5. Latest 3-month historical quote (price) associated with the ticker
	#6. Latest 6-month historical quote (price) associated with the ticker

	def __init__(self, ticker):
		# Initialize class
		self.ticker = ticker


	def get_name(self):
		# Retrieves the central index key of the company, using the ticker

		tiknames = {}

		try:

			# Quick lookup of cik
			
			for v in URL(Symbols.tickercik_url).load_json().values():

				tiknames.update({v["ticker"]:v["title"]})

			return tiknames[self.ticker].replace("\\","").replace("/","").upper()

		except KeyError:

			# Quick lookup of cik using modified ticker without special characters

			try:

				ticker = Util.clean_ticker(self.ticker)

				return tiknames[ticker].replace("\\","").replace("/","").upper()

			except KeyError:

				# Quick lookup of cik using modified ticker by splitting on special characters and taking 0 position

				try:

					ticker = Util.base_ticker(self.ticker)

					return tiknames[ticker].replace("\\","").replace("/","").upper()

				except KeyError:
			
					pass


	def get_cik(self):

		# Retrieves the central index key of the company, using the ticker

		ciktik = {}

		try:

			# Quick lookup of cik
			
			for v in URL(Symbols.tickercik_url).load_json().values():

				ciktik.update({v["ticker"]:v["cik_str"]})

			return ciktik[self.ticker]

		except KeyError:

			# Quick lookup of cik using modified ticker without special characters

			try:

				ticker = Util.clean_ticker(self.ticker)

				return ciktik[ticker]

			except KeyError:

				# Quick lookup of cik using modified ticker by splitting on special characters and taking 0 position

				try:

					ticker = Util.base_ticker(self.ticker)

					return ciktik[ticker]

				except KeyError:
					pass



	def get_news(self):
		# Retrieves latest news for a ticker
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/news?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			news = json.loads(data)
			return news
		except Exception:
			print("Check ticker: " + self.ticker + ".")


	"""
	See available methods
	/stock/twtr/chart
	/stock/twtr/chart/max
	/stock/twtr/chart/5y
	/stock/twtr/chart/2y
	/stock/twtr/chart/1y
	/stock/twtr/chart/ytd
	/stock/twtr/chart/6m
	/stock/twtr/chart/3m
	/stock/twtr/chart/1m
	/stock/twtr/chart/5d
	/stock/twtr/chart/date/20190220

	NOTE: use json.dumps()
	"""

	def get_price(self):
		# Free
		# Returns the latest price quote for a given stock (least expensive)
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/tops?token=pk_27e0d5c29afa4c9aa062d50a1575e609&symbols=%s" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)[0]["lastSalePrice"]
			return current_quote
		except Exception:
			try:
				url = "https://cloud.iexapis.com/stable/tops?token=pk_27e0d5c29afa4c9aa062d50a1575e609&symbols=%s" % self.ticker.replace("*","").strip()
				data = urllib.request.urlopen(url).read()
				current_quote = json.loads(data)[0]["lastSalePrice"]
				return current_quote
			except Exception:
				print("Check ticker: " + self.ticker + ".")

	def close_quote(self):
		# Returns the closing quote that can be added to the historical data. 
		d = Util.sdate

		d = "20191126" # FOR TESTING PURPOSES -- DELETE

		url = "https://cloud.iexapis.com/stable/stock/%s/chart/date/%s?chartByDay=true&token=pk_27e0d5c29afa4c9aa062d50a1575e609" % (self.ticker, d)
		data = URL(url).load_json()
		return data[0]

	def current_quote(self):
		# Returns the full quote 
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/quote?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			try:
				url = "https://cloud.iexapis.com/stable/stock/%s/quote?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker.replace("*","").strip()
				data = urllib.request.urlopen(url).read()
				current_quote = json.loads(data)
				return current_quote
			except Exception:
				print("Check ticker: " + self.ticker + ".")

	def one_day_quote(self):
		# Returns the latest 1-day intraday price quote for a given stock 
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/1d?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			try:
				url = "https://cloud.iexapis.com/stable/stock/%s/chart/1d?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker.replace("*","").strip()
				data = urllib.request.urlopen(url).read()
				current_quote = json.loads(data)
				return current_quote
			except Exception:
				print("Check ticker: " + self.ticker + ".")


	def five_day_quote(self):
		# Returns the latest 5-day intraday price quote for a given stock 
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/5d?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")

	def one_month_quote(self):
		# Returns the latest one-month intraday price quote for a given stock 
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/1m?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")


	def three_month_quote(self):
		# Returns the latest three-month intraday price quote for a given stock
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/3m?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")

	def six_month_quote(self):
		# Returns the latest six-month intraday price quote for a given stock
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/6m?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")

	def ytd_quote(self):
		# Returns the latest year-to-date intraday price quote for a given stock
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/ytd?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")

	def one_year_quote(self):
		# Returns the latest 12-month intraday price quote for a given stock 
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/1y?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")

	def two_year_quote(self):
		# Returns the latest two-year intraday price quote for a given stock
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/2y?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")

	def five_year_quote(self):
		# Returns the latest five-year intraday price quote for a given stock
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/5y?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			current_quote = json.loads(data)
			return current_quote
		except Exception:
			print("Check ticker: " + self.ticker + ".")


	def full_historicals(self):
		# Returns the full historical prices of a given stock (most expensive; this is why we cache in db)
		# for inserting or updating JSON into the database, don't forget to use json.dumps()
		try:
			url = "https://cloud.iexapis.com/stable/stock/%s/chart/max?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker
			data = urllib.request.urlopen(url).read()
			full_historicals = json.loads(data)
			return full_historicals
		except Exception:
			try:
				url = "https://cloud.iexapis.com/stable/stock/%s/chart/max?token=pk_27e0d5c29afa4c9aa062d50a1575e609" % self.ticker.replace("*","").strip()
				data = urllib.request.urlopen(url).read()
				full_historicals = json.loads(data)
				return full_historicals
			except Exception:
				print("Check ticker: " + self.ticker + ".")


################################################################################################################
#BEGIN SYMBOLS CLASS

"""
A simple class that stores urls for stocks, funds, and options (pricing quotes)
Generally, to use this class you'll import the desired URL and run a different class-based operation on it.
For example, 

url = Symbols.stocks_url

data = URL(url).load_json()

for loop...

"""


################################################################################################################



class Symbols:

	tickercik_url = "https://www.sec.gov/files/company_tickers.json"

	stocks_url = "https://cloud.iexapis.com/stable/ref-data/iex/symbols?token=pk_27e0d5c29afa4c9aa062d50a1575e609"

	funds_url = "https://cloud.iexapis.com/stable/ref-data/mutual-funds/symbols?token=pk_27e0d5c29afa4c9aa062d50a1575e609"

	options_url = "https://cloud.iexapi s.com/stable/ref-data/options/symbols?token=pk_27e0d5c29afa4c9aa062d50a1575e609"


	def get_all_tickers(tickercik_url):

		ciksticks = {}

		for v in URL(tickercik_url).load_json().values():

			ciksticks.update({v["cik_str"]:v["ticker"]})


		return ciksticks

	get_all_tickers = get_all_tickers(tickercik_url)



################################################################################################################
#BEGIN INDEX CLASS
################################################################################################################



class Feed:

	def get_current_idx_url(month):

		#Generates a url for daily filings in the format: https://www.sec.gov/Archives/edgar/daily-index/{YYYY}/QTR{N}/master.{YYYYMMDD}.idx

		if datetime.datetime.now().month < 3:
			return "https://www.sec.gov/Archives/edgar/daily-index/%d/QTR1/master.%s.idx" % (datetime.datetime.now().year, str(datetime.datetime.now().date()).replace("-",""))
		elif datetime.datetime.now().month > 3 and datetime.datetime.now().month < 7:
			return "https://www.sec.gov/Archives/edgar/daily-index/%d/QTR2/master.%s.idx" % (datetime.datetime.now().year, str(datetime.datetime.now().date()).replace("-",""))
		elif datetime.datetime.now().month > 6 and datetime.datetime.now().month < 10:
			return "https://www.sec.gov/Archives/edgar/daily-index/%d/QTR3/master.%s.idx" % (datetime.datetime.now().year, str(datetime.datetime.now().date()).replace("-",""))
		elif datetime.datetime.now().month > 9 and datetime.datetime.now().month < 13:
			return "https://www.sec.gov/Archives/edgar/daily-index/%d/QTR4/master.%s.idx" % (datetime.datetime.now().year, str(datetime.datetime.now().date()).replace("-",""))

	daily = get_current_idx_url(datetime.datetime.now().month)
	# Returns the current day's "daily" file (usually available by 22:05 ET)

	rss40 = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=include&start=0&count=40&output=atom"
	# RSS feed url, output 40 latest filings

	rss100 = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=include&start=0&count=100&output=atom"
	# RSS feed url, output 100 latest filings


################################################################################################################
#BEGIN Util CLASS

################################################################################################################


class Util:

	# These are helper functions and variables

	# Current date in str format
	sdate = str(datetime.datetime.now().date()).replace("-","")

	def marketisopen():

	    # Market is open between 9:30a and 4:30p ET
	    # This function currently built to operate on PT

	    m = datetime.datetime.now().minute


	    h = datetime.datetime.now().hour

	    w = datetime.datetime.now().weekday()

	    if  w <= 5 and h < 6 and m < 30:
	        return False

	    elif w <= 5 and h == 6 and m >= 30:
	        return True

	    elif w <= 5 and 7 <= h <= 12:
	        return True

	    elif w <= 5 and h == 13 and m < 30:
	        return True

	    elif w <= 5 and h == 13 and m >= 30:
	        return False

	    elif w <= 5 and h >= 14:
	        return False
	    else:
	    	return False


	def force_ntype(n):
	    # Converts str # into int() or float()
	    # Forces n-type
	    # ONLY used with string-formatted numbers
	    if "." in n:
	    	return float(n)
	    else:
	    	return int(n)


	def makealpha(string):

	    # Removes non-alpha characters from string
	    
	    return "".join(c for c in string if c.isalpha())


	def makedigit(string):

		return "".join(c for c in string if c.isdigit())


	def pres_type(soupobject):

		# XBRL-specific function that determines the type of universal XBRL presentation tag
		# Ether "link:presentationlink" or "presentationlink"

		if soupobject.find("presentationlink"):
			return "presentationlink"
		else:
			return "link:presentationlink"


	def loc_type(soupobject):

		if soupobject.find("link:loc"):

			return "link:loc"

		else:

			return "loc"


	def role_type(soupobject):

		if soupobject.find("link:roletype"):

			return "link:roletype"

		else:

			return "roletype"



	def context_type(soupobject):

		# XBRL-specific function that determines the type of universal XBRL presentation tag
		# Ether "link:presentationlink" or "presentationlink"

		if soupobject.find("xbrli:context"):
			return {"context":"xbrli:context", "period":"xbrli:period", "instant":"xbrli:instant", "start":"xbrli:startdate", "end":"xbrli:enddate"}

		else:
			return {"context":"context", "period":"period", "instant":"instant", "start":"startdate", "end":"enddate"}
		


	def full_index(year, sq, eq):
		#Generates url list for index files to be queried from sec.gov
		#Enter year from which to create index through to 2019
		#nq is for the number of quarters desired (1-4)
		cust_index = []
		idx_bases = ["https://www.sec.gov/Archives/edgar/full-index/" + str(year) + "/" for year in range(year, datetime.datetime.now().year + 1)]
		quarters = ["QTR1/master.idx", "QTR2/master.idx", "QTR3/master.idx", "QTR4/master.idx"]
		for idx_base in idx_bases:
			for quarter in quarters[sq-1:eq]:
				cust_idx = idx_base + quarter
				cust_index.append(cust_idx)
		return cust_index


	def monthly_xbrl():

		xbrl_files = []

		base = "https://www.sec.gov/Archives/edgar/monthly/"

		soup = URL(base).html_soup()

		for tag in soup.findAll("a", href=True):

		    if ".xml" in tag["href"]:

		        url = base + tag["href"]

		        xbrl_files.append(url)

		return xbrl_files


	def get_instances(url):

		# Used specifically on Monthly xbrl urls

	    instances = []

	    soup = URL(url).xml_soup()

	    for tag in soup.findAll("edgar:xbrlfile"):

	        if tag.get("edgar:description") == "XBRL INSTANCE FILE":
	            instances.append(tag["edgar:url"])

	    return instances

	def clean_ticker(ticker):

		# Removes special characters/punctuation from ticker

		punc = set(string.punctuation) # a list of characters to be removed

		cleanticker = ''.join(ch for ch in ticker if ch not in punc) #Removes special characters

		return cleanticker

	def base_ticker(ticker):

		try:
			# Finds the base ticker by splitting on special characters and taking 0 position

			# e.g., AAA-B yields ['AAA', 'B'], then returns 'AAA'

			punc = set(string.punctuation)

			base_ticker = [ticker.replace(ch, "-") for ch in ticker if ch in punc]

			base_ticker = base_ticker[0].split("-")[0]

			return base_ticker

		except IndexError:
			pass


	def convert_unix_time(timestamp):

		#Converts UNIX timestamp to datetime

		readable = datetime.datetime.fromtimestamp(timestamp).isoformat()
		return readable[:10]


	def gen_ixfile(central_index_key, filing_id):
		# Takes the central index key and filing id, returns the index filing

		url = "https://www.sec.gov/Archives/edgar/data/%d/%s-index.htm" % (central_index_key, filing_id)
		return url

	def contatains_digit(string):
		return any(char.isdigit() for char in string)

	# isFloat, isInt, isSuffix, and linkIsBad are primarily 
	# used in the tagIsBad function

	def isFloat(st):
		# Returns True if string is a float value
	    try:
	        float(st.replace("*",""))
	        return True
	    except ValueError:
	        return False

	def isInt(st):
		# Returns True if string is an integer value
	    try:
	        int(st.replace("*","").replace("-",""))
	        return True
	    except ValueError:
	        return False

	def isSuffix(string):
		# Returns True if string (url) is a suffix url
		if ".htm" in st and "www" not in st:
			# if contains htm suffix but no www prefix,
			# returns True
			return True
		else:
			return False

	def linkIsBad(link):
		# If the link contains neither a prefix nor a suffix url, returns True
		# These are typically internal document links containing '#'
		if "www" not in link and ".htm" not in link:
			return True

	def tagIsBad(tag):
		"""
		If the plain text href value is blank, None, a form #,
		or 1 word (includes single integers and floats), 
		or date, tagIsBad returns True (the plain text tag IS BAD). 
		This is an incredibly simple yet effective rule.
		"""
		try:
			if im.is_form[tag.upper()]:
				return True
				#If lookup = a form number
		except TypeError:
			pass
		except KeyError:
			if tag == '' or tag == None:
				#If the tag is empty or None
				return True
			elif len(tag.split()) < 2:
				# If the tag is only 1 word
				return True
			elif len(tag.split("/")) == 3:
				# Likely a date format
				#Breaks tag into 3 components
				#If any are a month, tag is likely a date
				try:
					if im.is_month[tag[0].title()]:
						return True
					elif im.is_month[tag[1].title()]:
						return True
					elif im.is_month[tag[2].title()]:
						return True
				except KeyError:
					pass
			elif len(tag.split("-")) == 3:
				# Likely a date format
				tag = tag.split("-")
				#Breaks tag into 3 components
				#If any are a month, tag is likely a date
				try:
					if im.is_month[tag[0].title()]:
						return True
					elif im.is_month[tag[1].title()]:
						return True
					elif im.is_month[tag[2].title()]:
						return True
				except KeyError:
					pass
			elif len(tag.split(",")) == 3:
				tag = tag.replace(",","").split()
				#Breaks tag into 3 components
				#If any are a month, tag is likely a date
				try:
					if im.is_month[tag[0].title()]:
						return True
					elif im.is_month[tag[1].title()]:
						return True
					elif im.is_month[tag[2].title()]:
						return True
				except KeyError:
					pass
			elif len(tag.split()) == 2:
				#If tag is two words, ensures both of the words
				# aren't single digits, floats, or letters.
				# Exhibit 12 is a bad tag (12 is an integer)
				# Appendix B is a bad tag (B is single-length)
				# Appen. (B).12 would pass; but this would be an anomaly
				tag = tag.split()
				tag[0] = tag[0].replace("(","").replace(")","")
				tag[1] = tag[1].replace("(","").replace(")","")
				if isInt(tag[0]) or isFloat(tag[1]):
					#Ensures two-length tag doesn't contain a number
					return True
				elif len(tag[0]) == 1 or len(tag[1]) == 1:
					#Ensures two-length tag doesn't contain 
					#an indivual single-length character
					return True
			else:
				return False

################################################################################################################
#BEGIN DATATABLE CLASS
################################################################################################################



class dataTable:
	# Class containing Postgres database tables
	# POSTGRES: To add a foreign key constraint, use:
	# ALTER TABLE fk_table ADD CONSTRAINT constraint_name FOREIGN KEY (fk_column) REFERENCES pk_table (col);
	# To add primary key:
	# ALTER TABLE table ADD PRIMARY KEY (col);

	# companies table
	companies = Table('companies', MetaData(),
				Column('company_name', String(300), index=True),
				Column('central_index_key', Integer(), primary_key=True, unique=True),#PrimaryKey
				Column('industrial_code', Integer()),
				Column('industry', String(300)),
				Column('loc_state', String(2)),
				Column('filings_api', Text()),
				extend_existing=True)


	# Temporary companies table (for testing)
	tempcos = Table('tempcos', MetaData(),
			  Column('company_name', String(300), index=True),
			  Column('central_index_key', Integer(), primary_key=True, unique=True),#PrimaryKey
			  Column('industrial_code', Integer()),
			  Column('industry', String(300)),
			  Column('loc_state', String(2)),
			  Column('filings_api', Text()),
			  extend_existing=True)



	"""
	# Filings table
	NOTE: A paired UNIQUE constraint should be created on (central_index_key, filing_url) in Postgres before populating
	i.e., ALTER TABLE filings ADD CONSTRAINT unique_cik_url UNIQUE (central_index_key, filing_url);
	This prevents duplicate url entries for each central_index_key
	"""
	filings = Table('filings', MetaData(),
			  Column('central_index_key', Integer(), ForeignKey('companies.central_index_key'), nullable=False, index=True),#ForeignKey
			  Column('filing_id', String(100), index=True),#use SEC Accession number for filing
			  Column('filing_url', String(300), index=True),#Url where the form is located
			  Column('date', Date(), default=datetime.date),
			  Column('form', String(30), index=True),#Form number: e.g., 8-K, 10-K, etc.
			  Column('filing_type', String(100)),#Categorized as either Primary or Exhibit
			  Column('filing_text', Text()),#Full document text without HTML
			  Column('financial_data', Text()),#Applicable to annual reports and quarterly reports
			  Column('verbose_form_description', Text()), #This is the full title of the document given by the company
			  Column('search_filing_text', TSVECTOR), #tsvector for Generalized Inverted Index
			  Column('form_description', String(1000)), #Generic description of form
			  Column('category', String(132)),
			  Column('archived', String(1), index=True),
			  extend_existing=True)#"Hot" words that can be used to more precisely categorize the filing
	

	tempfilings = Table('tempfilings', MetaData(),
			  Column('central_index_key', Integer(), ForeignKey('tempcos.central_index_key'), nullable=False, index=True),#ForeignKey
			  Column('filing_id', String(100), index=True),#use SEC Accession number for filing
			  Column('filing_url', String(300), index=True),#Url where the form is located
			  Column('date', Date(), default=datetime.date),
			  Column('form', String(30), index=True),#Form number: e.g., 8-K, 10-K, etc.
			  Column('filing_type', String(100)),#Categorized as either Primary or Exhibit
			  Column('filing_text', Text()),#Full document text without HTML
			  Column('financial_data', Text()),#Applicable to annual reports and quarterly reports
			  Column('verbose_form_description', Text()), #This is the full title of the document given by the company
			  Column('search_filing_text', TSVECTOR), #tsvector for Generalized Inverted Index
			  Column('form_description', String(1000)), #Generic description of form
			  Column('category', String(132)),
			  Column('archived', String(1), index=True),
			  extend_existing=True)#"Hot" words that can be used to more precisely categorize the filing




	"""
	#Financials table
	To load historical prices from IEX using the ticker_feed column:
	feed = json.load(historicals=json.loads(ExtractTickerInfo(ticker).full_historicals()))

	To dump (update) historical prices in the historicals column:
	values(historicals=json.dumps(ExtractTickerInfo(ticker).full_historicals()))
	"""
	financials = Table('financials', MetaData(),
			 	 Column('central_index_key', Integer(), ForeignKey('companies.central_index_key'), nullable=False, index=True),
				 Column('annuals_api', Text()),
				 extend_existing=True)



	"""
	NOTES ON POSTGRES:
	The finsub, finpresentation, and financialnumbers tables are temporary tables used to help create the 
	financial tables for a given year (those tables are created using Postgres, and follows the query format below)

	First import the text files directly into Postgres (finsub, finpres, and finnum)

	Then:

	CREATE TABLE financialsYYYY AS
	 SELECT tmp_financialnumbers.filing_id,
	    tmp_finsubmission.central_index_key,
	    tmp_finsubmission.form,
	    tmp_finpresentation.tag,
	    tmp_financialnumbers.uom,
	    tmp_financialnumbers.uom_value,
	    tmp_finpresentation.stmnt,
	    tmp_financialnumbers.ddate,
	    tmp_financialnumbers.qrtrs,
	    tmp_finpresentation.report,
	    tmp_finpresentation.line,
	    tmp_finpresentation.plabel
	   FROM tmp_finsubmission
	     JOIN tmp_finpresentation ON tmp_finsubmission.filing_id = tmp_finpresentation.filing_id
	     JOIN tmp_financialnumbers ON tmp_finpresentation.filing_id = tmp_financialnumbers.filing_id
	  WHERE tmp_financialnumbers.tag = tmp_finpresentation.tag 
	  AND tmp_financialnumbers.filing_id = tmp_finpresentation.filing_id
	  AND tmp_financialnumbers.dimh = '0x00000000' AND tmp_financialnumbers.ddate < CURRENT_DATE;

	Once these two steps are complete, run 

	financialsModule.pop_financials(engine, metadata)

	"""


	
	"""
	Finsub table (financial submission)

	We only use the filing_id, central_index_key, and the form # in this table; it was simply created to assist in importing the data
	Without a mountain of pre-processing.
	The data is copied with Postgres and is not processed using Python
	WITH (FORMAT CSV, DELIMITER E'\t', HEADER, QUOTE E'\b');
	"""
	finsub = Table('tmp_finsubmission', MetaData(),
			 Column('filing_id', String(40), primary_key=True, index=True),#Same as filing_id but without the central_index_key
			 Column('central_index_key', Integer(), ForeignKey('companies.central_index_key'), nullable=False, index=True),#ForeignKey
			 Column('name', String(300)), # Name
			 Column('sic', Integer()),
			 Column('countryba',String(4)),
			 Column('stprba', String(4)),
			 Column('cityba', String(60)),
			 Column('zipba', String(20)),
			 Column('bas1', String(80)),
			 Column('bas2', String(80)),
			 Column('baph', String(24)),
			 Column('countryma', String(4)),
			 Column('stprma', String(4)),
			 Column('cityma', String(60)),
			 Column('zipma',String(20)),
			 Column('mas1', String(80)),
			 Column('mas2', String(80)),
			 Column('countryinc', String(4)),
			 Column('stprinc', String(4)),
			 Column('ein', Integer()),
			 Column('former', String(300)),
			 Column('changed', String(16)),
			 Column('afs', String(10)),
			 Column('wksi', Boolean()),
			 Column('fye', String(8)),
			 Column('form', String(20)), # Form
			 Column('period', Date()),
			 Column('fy', Integer()),
			 Column('fp', String(4)),
			 Column('filed',Date()),
			 Column('accepted', String(40)),
			 Column('prevrpt',Boolean()),
			 Column('detail', Boolean()),
			 Column('instance', String(64)),
			 Column('nckiks', Integer()),
			 Column('aciks', String(240)),
			 Column('pubfloatusd', Float()),
			 Column('floatdate', Date()),
			 Column('floataxis', String(510)),
			 Column('floatmems', Integer()))



	"""
	Finpre table (financial presentation table)

	WITH (FORMAT CSV, DELIMITER E'\t', HEADER, QUOTE E'\b');
	The data is copied with Postgres and is not processed using Python
	"""
	finpre = Table('tmp_finpresentation', MetaData(),
			 Column('filing_id', String(40), ForeignKey('finsubmission.filing_id'), nullable=False, index=True),
			 Column('report', Integer()), # File that corresponds to the table
			 Column('line', Integer()), # Line # where the value appears
			 Column('stmnt', String(30)), # Type of Statement
			 Column('inpth', Boolean()), # Whether data is parenthetical
			 Column('tag', String(512)), # The tag 
			 Column('version', String(40)), # The accounting version
			 Column('prole', String(100)), # The "role" of the tag
			 Column('plabel', Text()), # The preferred label used by the company
			 Column('negating', Boolean())) # Generally irrelevalent



	"""
	Financial numbers table

	Columns in the table are either self-explanatory, explained in a previous table, or are irrelevant. See not about table creation
	with postgres above the "finsub" table
	WITH (FORMAT CSV, DELIMITER E'\t', HEADER, QUOTE E'\b');
	# The data is copied with Postgres and is not processed using Python
	"""
	financial_numbers = Table('tmp_financialnumbers', MetaData(),
						Column('filing_id', String(40), ForeignKey('finsubmission.filing_id'), nullable=False, index=True), # Filing id
						Column('tag', String(512)), 
						Column('version', String(40)),
						Column('ddate', Date()),
						Column('qrtrs', Integer()),
						Column('uom', String(40)),
						Column('dimh', String(64)), # Only concerned with 0x000000 identifiers
						Column('iprx', Integer()),
						Column('uom_value', Float()),
						Column('footnote', Text()),
						Column('footlen', Integer()),
						Column('dimn', Integer()), # irrelevant
						Column('coreg', String(512)), # irrelevant
						Column('durp', Float()),# irrelevant
						Column('datp', Float()),# irrelevant
						Column('dcml', Float()))# irrelevant



	"""
	Tickers table

	To load historical prices from IEX using the ticker_feed column:
	feed = json.load(urllib.request.urlopen(row.ticker_feed))

	To dump (update) historical prices in the historicals column:
	values(historicals=json.dumps(feed))

	Also needs a unique ticker, cik pair. 
	ALTER TABLE tickers ADD CONSTRAINT unique_cik_ticker UNIQUE (central_index_key, ticker);

	"""
	tickers = Table('tickers', MetaData(),
			  Column('central_index_key', Integer(), ForeignKey('companies.central_index_key'), nullable=False, index=True),
			  Column('ticker', String(20), index=True, unique=True),#If applicable
			  Column('historicals', Text()),
			  Column('latestprice', Float()),
			  Column('marketcap', Float()),
			  Column('peratio', Float()),
			  Column('eps', Float()),
			  Column('exchange', String(100)),
			  Column('netincome', Float()),
			  Column('denom', String(5)),
			  Column('dsymb', String(5)),
			  Column('news', Text()),
			  extend_existing=True)


	# Funds table
	funds = Table('funds', MetaData(),
			Column('central_index_key', Integer(), ForeignKey('companies.central_index_key'), nullable=False, index=True),
			Column('fund_ticker', String(20), index=True, unique=True),#If applicable
			Column('fund_name', String(300), index=True),#If applicable
			Column('fund_ticker_feed', String(300)))




	"""
	Index files table (consider dropping)

	NOTE: A paired UNIQUE constraint should be created on (central_index_key, index_url) in Postgres before populating
	i.e., ALTER TABLE index_files ADD CONSTRAINT unique_cik_index_url UNIQUE (central_index_key, index_url);
	This prevents duplicate url entries for each central_index_key
	"""
	index_files = Table('index_files', MetaData(),
				  Column('central_index_key', Integer(), ForeignKey('companies.central_index_key'), nullable=False, index=True),
			      Column('index_url', String(300), index=True), # Url for the filing's index (includes primary doc and exhibits)
			      Column('processed', String(1), default=('N'), index=True),
			      Column('form', String(30)),
				  Column('date', Date(), default=datetime.date),
				  extend_existing=True)


	tempindex = Table('tempindex', MetaData(),
			  Column('central_index_key', Integer(), ForeignKey('companies.central_index_key'), nullable=False, index=True),
		      Column('index_url', String(300), index=True), # Url for the filing's index (includes primary doc and exhibits)
		      Column('processed', String(1), default=('N'), index=True),
		      Column('form', String(30)),
			  Column('date', Date(), default=datetime.date),
			  extend_existing=True)









































