import urllib.request; from bs4 import BeautifulSoup; import iterModule as im
import json; import datetime; import FinClasses; import timeout_decorator
from sqlalchemy import *

"""
These helper functions are not constrained by the class types and are therefore 
more flexible in their usage. 

"""

def order_api_filings(companies_table, filings_table):
	# Orders the filings in the API (companies.filings_api) in descending date order
	# NOTE: this iterates through ALL filers, and should only need to be run
	# periodically, if at all. 

	ciks = []
	s = select([companies_table.c.central_index_key])

	for cik in engine.execute(s).fetchall():
		ciks.append(*cik)

	for cik in ciks:

		s = select([companies_table]).where(companies_table.c.central_index_key == cik)

		for row in engine.execute(s).fetchall():
			try:
				name = row.company_name
				cik = row.central_index_key 
				filer = {'name': name, 'CIK': cik, 'filings': []}

				p = select([filings_table]).where(filings_table.c.central_index_key == row.central_index_key).order_by(filing_table.c.date.desc()).order_by(filings_table.c.filing_id).order_by(filings_table.c.filing_type.desc())

				for row in engine.execute(p).fetchall():
					filer["filings"].append({'form': row.form, 'accession': row.filing_id, 'description': row.form_description, 'type': row.filing_type, 'date': str(row.date), 'url': row.filing_url})

				u = update(companies_table).where(companies_table.c.central_index_key == row.central_index_key)
				u = u.values(filings_api = json.dumps(filer))
				engine.execute(u)
				print(cik)
			except Exception as e:
				print(e)



def run_delete(engine, index, filings):
	ix_urls = []

	count = 0

	count2 = 0


	s = select([index.c.index_url])

	for row in engine.execute(s).fetchall():
		ix_urls.append(row[0])

	total = len(ix_urls)


	for row in engine.execute(s).fetchall():
		filing_id = newClasses.IndexUrl(row[0]).get_filing_id()
		cik = newClasses.IndexUrl(row[0]).get_cik()
		p = select([filings]).where(and_(filings.c.central_index_key == cik, filings.c.filing_id == filing_id)).limit(1)
		for row_ in engine.execute(p).fetchall():
			ix = back_gen_index_file(row_.central_index_key, row_.filing_id)
			d = delete(index).where(index.c.index_url == ix)
			engine.execute(d)
			count2 += 1
		count += 1
		if count % 1000 == 0:
			pct = count*100/total
			print(str(count) + " out of " + str(total) + " index urls processed (" + str(round(pct, 4)) + "%). " + str(count2) + " deleted.")



