from sqlalchemy import *
from sqlalchemy import exc; import psycopg2;  import datetime; import time; import urllib.request
from FinClasses import *
import api_dump; import json; import os
import iterModule as im; import traceback; from bs4 import BeautifulSoup; import PyPDF2

#CMD+Option+G for multiple text selection/replace in SublimeText

engine = create_engine('postgresql+psycopg2://postgres:@localhost:5432/forager')
#Initializes engine in Postgres db; psycopg2 is used in conjunction with sqlalchemy

print(datetime.datetime.now())

companies = dataTable.companies

filings_table = dataTable.filings

index = dataTable.index_files


eod = {}


while True:

	if datetime.datetime.today().weekday() < 5 and datetime.datetime.now().hour > 4: 
		# Only runs if the day of the week is Mon through Friday (Sat/Sun = 5/6)
		# and between 5 a.m and midnight

		date = datetime.datetime.now().date() # Date in yyyymmdd format

		print("Waiting for feed...")

		time.sleep(5) # Set to sleep and check feed every 5 seconds

		try:
			# Real-time feed url, latest 40 filings
			rss = Feed.rss40

			for file in URL(rss).ix_feed():

				#For each entry in the feed, this section attempts to enter the url and other related data in to the table

				try:
					ins1 = index.insert().values(
						    central_index_key=int(file["cik"]),
							index_url=file["url"],
							processed="N",
							form=file["form"],
							date=file["date"])
					engine.execute(ins1)
					print("Index url inserted: " + file["url"])

				except exc.IntegrityError:

					# If the entry into the index table fails, it is likely because the primary key does not exist in the primary key table
					# This will enter the primary key into the table with the primary keys
					# If the primary key already exists, so does the filing, so the script will pass on Exception

					try:
						ins = companies.insert().values(
							central_index_key=file["cik"],
							company_name=file["name"])
						engine.execute(ins)
						print(file["cik"], file["name"])

						# Attempts to update the SIC and industry

						industry = CIK(file["cik"]).get_industry()

						try:
							u1 = update(companies).where(companies.c.central_index_key == file["cik"])
							u1 = u1.values(industrial_code=industry["SIC"], industry=industry["industry"])
							engine.execute(u1)
						except:
							pass

						# Attempts to update location state

						state = CIK(file["cik"]).get_state()

						try:
							u2 = update(companies).where(companies.c.central_index_key == file["cik"])
							u2 = u2.values(loc_state=state)
							engine.execute(u2)
						except:
							pass

						# Then will enter the url and other related data into the table (as in the first "try")
						
						ins1 = index.insert().values(
						    central_index_key=int(file["cik"]),
							index_url=file["url"],
							processed="N",
							form=file["form"],
							date=file["date"])
						engine.execute(ins1)
						print("Index url inserted: " + file["url"])

					except:
						pass
	

		except Exception:
			# Passes the exception if the feed is not available for some reason
			pass

		

		if eod.get(date) == True:

			# If the date checked = True in the dictionary (line 19), the daily index file has already been checked, 
			# so lines 89 through 157 don't run, and the following is printed:

			print("Daily .txt file already checked...")


		else:

			# Otherwise, if the daily file has not been checked yet, the program will raise an exception (because the checked date will not exist)

			if datetime.datetime.now().hour != 19:

				# Daily index files are published between 22:00 and 23:00 ET, so if it is not beteween 22:00 and 23:00, the program doesn't check the daily index file

				pass

			elif datetime.datetime.now().hour == 19:

				# If the time is between 22:00 and 23:00, the following script runs

				print("Checking daily .txt file...")

				daily = Feed.daily # Generates a daily url to be checked for index files


				try:
					subcount = 0 # Set to count the full number of files in the index file
					check = 0 # Set to count the number of files that have already been entered

					#For each entry in the daily index file, this section attempts to enter the url and other related data into the table

					for file in URL(daily).ix_files():
						subcount += 1

						# Raise the number of files counted by 1
						# each file is a dictionary that includes the following:
						# {"cik":cik, "name":name, "form":form, "date":date, "url":index_url}

						try:
							ins1 = index.insert().values(
								    central_index_key=int(file["cik"]),
									index_url=file["url"],
									processed="N",
									form=file["form"],
									date=file["date"])
							engine.execute(ins1)
							print("Index url inserted: " + file["url"])
							eod.update({date:True})

						except exc.IntegrityError:

							# If the entry into the index table fails, it is likely because the primary key does not exist in the primary key table
							# or because the url already exists.
							# This will attempt to enter the company with its primary key (cik), then attempt to enter the url again

							try:
								ins = companies.insert().values(
									central_index_key=file["cik"],
									company_name=file["name"])
								engine.execute(ins)
								print(file["cik"], file["name"])


								# Attempts to update the SIC and industry

								industry = CIK(file["cik"]).get_industry()

								try:
									u1 = update(companies).where(companies.c.central_index_key == file["cik"])
									u1 = u1.values(industrial_code=industry["SIC"], industry=industry["industry"])
									engine.execute(u1)
								except:
									pass


								# Attempts to update location state

								state = CIK(file["cik"]).get_state()

								try:
									u2 = update(companies).where(companies.c.central_index_key == file["cik"])
									u2 = u2.values(loc_state=state)
									engine.execute(u2)
								except:
									pass

								# Enter company, enter url
								
								ins1 = index.insert().values(
								    central_index_key=int(file["cik"]),
									index_url=file["url"],
									processed="N",
									form=file["form"],
									date=file["date"])
								engine.execute(ins1)
								print("Index url inserted: " + file["url"])
								eod.update({date:True})

							except:
								# Adds +1 to the check counter if both he CIK and url exist
								check += 1


					if check == subcount:

						# Checks the number of filings vs the number that have been entered.
						# If filings in the .txt file exist but filings have not been entered
						# into the database, this means the counted filings already exist
						# in the database, so the end-of-day update is marked "True" for the 
						# date and the script will not check the file again. 

						print("All daily files accounted for.")
						eod.update({date:True})
					else:
						pass
				except urllib.error.HTTPError:

					# Passes the exception when the daily index file is not available

					print("Daily .txt file not available...")
			else:
				# Otherwise, the script does nothing
				pass


		# Selects all the files in the index table where the "processed" column = N ("No") or E ("Error")

		s = select([index]).where(or_(index.c.processed == 'N', index.c.processed == 'E')).order_by(index.c.central_index_key)

		icount = 0

		for row in engine.execute(s).fetchall():

			# Counts the number of filings where processed = "Y" or "E"

			icount += 1

		if icount > 0:
			# If that count is greater than zero, the following script runs

			print("Processing index files...")

			for row in engine.execute(s).fetchall():
				try:
					cik = IndexUrl(row.index_url).get_cik()

					filings = IndexUrl(row.index_url).get_filings()

					for filing in filings:

						# Selects each index file in the index files table and processes
						# The information below, entering it into the filings table

						try:
							ins = filings_table.insert().values(
								  central_index_key=cik,
								  filing_id=filing["accession"],
								  filing_url=filing["url"],
								  date=filing["date"],
								  form=filing["form"],
								  filing_type=filing["type"],
								  form_description=filing["description"],
								  category=im.category[filing["form"].split(".")[0]],
								  archived='N')


							engine.execute(ins)
							print(filing["url"])


						except Exception:
							#Exceptions are passed because they already exist in the filings table
							pass

					# Once each filing (primary filing and exhibits) is entered into the filing table
					# The main (index) file url is labeled as processed (processed='Y')

					u4 = update(index).where(index.c.index_url == row.index_url)
					u4 = u4.values(processed="Y")
					engine.execute(u4)

				except Exception:

					# For any other exceptions, if there's a problem with the index file in general, 
					# It's labeled as E (for "Error") and an attempt to process it will happen
					# In the next cycle

					u5 = update(index).where(index.c.index_url == row.index_url)
					u5 = u5.values(processed="E")
					engine.execute(u5)
					print("Error: " + row.index_url)



		q = select([filings_table]).where(filings_table.c.archived == 'N').distinct(filings_table.c.filing_url)

		for row in engine.execute(q).fetchall():
			ext = row.filing_url.split(".")[-1] # Url extension: html, xml, pdf, etc.
			ftype = row.filing_type
			try:
				if ftype == 'XML':

					# XML files are generally not needed at this point and have been removed prior
					# But this script deletes them just in case they appear
					# Script for processing XML in progress

					d = delete(filings_table).where(filings_table.c.filing_url == row.filing_url)
					engine.execute(d)
					print("Deleted " + row.filing_url)

				elif row.form == 'ABS-15G' or row.form == 'ABS-15G/A' or ext == "paper":

					# Pass for processing later (still working on script block for this)

					u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
					u = u.values(filing_text=None, financial_data=None, verbose_form_description=None, search_filing_text=None, archived='Y')
					engine.execute(u)
					print("Updated " + row.filing_url)

				elif ext == "pdf" or ext == "PDF":

					#PDFs will need to be processed later; for now, sets all parameters to None and archived to 'R' (for "Reprocessing" required)


					u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
					u = u.values(filing_text=None, financial_data=None, verbose_form_description=None, search_filing_text=None, archived='R')
					engine.execute(u)
					print("Updated " + row.filing_url)

				elif row.form == 'NSAR-A' or row.form == 'NSAR-A/A' or row.form == "NSAR-AT"\
				or row.form == "NSAR-AT/A" or row.form == "NSAR-B" or row.form == "NSAR-B/A"\
				or row.form == "NSAR-BT" or row.form == "NSAR-BT/A":

					# These filings are currently not needed to be processed; sets all parameters to None

					u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
					u = u.values(filing_text=None, financial_data=None, verbose_form_description=None, search_filing_text=None, archived='Y')
					engine.execute(u)
					print("Updated " + row.filing_url)

				elif ftype == 'exhibit' and ext == "txt" or ftype == 'exhibit' and ext == "htm"\
				or ftype == 'exhibit' and ext == ".TXT" or ftype == 'exhibit' and ext == "HTM":
					try:

						# Block updates the full plain text and tsvector columns for exhibits in the database
						# Currently runs on a timeout decorator (2 seconds)
						# Times out if url request takes too long

						if __name__ == '__main__':
							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(filing_text=URL(row.filing_url).extract_text())
							engine.execute(u)

							su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
							engine.execute(su)
							print("Updated " + row.filing_url)

					except Exception as e:
						print(e)

						# If the request times out (generally because of a very large html file)
						# Updates the "archived" block to "T" (for "Timeout") for later processing

						u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u = u.values(archived='T')
						engine.execute(u)
						print("Error " + row.filing_url)


				elif row.form == "3" or row.form == "3/A":
					# Processes forms 3 and 3/A

					if ".xml" not in row.filing_url:

						# Older filings are not in xml; there's currently no efficient way to process them,
						# so they are simply updated to archived='Y'

						u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u = u.values(archived='Y')
						engine.execute(u)

					elif len(row.filing_url.split("/")) == 9:

						# Two types of form 3 and 3/A: XML and HTML
						# The XML filing url is a modification of the HTML file url
						# So the XML version is deleted

						d = delete(filings_table).where(filings_table.c.filing_url == row.filing_url)
						engine.execute(d)
						print("Deleted: " + row.filing_url)

					else:

						# The "get_ownership()" method temporarily modifies the HMTL url to XML (built into the method), 
						# and retrieves and updates the XML data in the financial_data column
						# This is done so we can both use the HTML url for linking out to display
						# and process the XML at the same time

						u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u = u.values(financial_data=json.dumps(URL(row.filing_url).get_ownership()), archived='Y')
						engine.execute(u)
						print("Updated: " + row.filing_url)


				elif row.form == "4" or row.form == "4/A" or row.form == '5' or row.form == '5/A':

						# Processes forms 4, 4/A, 5, and 5/A

					if ".xml" not in row.filing_url:

						# Older filings are not in xml; there's currently no efficient way to process them,
						# so they are simply updated to archived='Y'

						u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u = u.values(archived='Y')
						engine.execute(u)



					elif len(row.filing_url.split("/")) == 9:

						# Two types of form 3 and 3/A: XML and HTML
						# The XML filing url is a modification of the HTML file url
						# So the XML version is deleted

						d = delete(filings_table).where(filings_table.c.filing_url == row.filing_url)
						engine.execute(d)
						print("Deleted: " + row.filing_url)

					else:

						# The "update_change_ownership()" method temporarily modifies the HMTL url to XML (built into the method), 
						# and retrieves and updates the XML data in the financial_data column
						# This is done so we can both use the HTML url for linking out to display
						# and process the XML at the same time

						u1 = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u1 = u1.values(financial_data=json.dumps(URL(row.filing_url).update_change_ownership()), archived='Y')
						engine.execute(u1)
						print("Updated: " + row.filing_url)



				elif row.form == '8-K' or row.form == '8-K/A':

					# Processes forms 8-K and 8-K/A
					# These forms are special because there is metadata in the index file that needs to be collected

					ixfile = Util.gen_ixfile(row.central_index_key, row.filing_id) # Generates and index file url for the filing to be crawled

					try:

						# Block updates the full plain text and tsvector columns for the main (not index) filing in the database
						# Currently runs on a timeout decorator (2 seconds)
						# Times out if url request takes too long


						if __name__ == '__main__':

							# Also updates the metadata in the verbose_form_description column, using the previously generated index file url (line 454)

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(filing_text=URL(row.filing_url).extract_text(), verbose_form_description=IndexUrl(ixfile).current())
							engine.execute(u)

							# Locates hyperlinked documents in the main filing and iterates over them
							# Typically, the hyperlinks are exhibits with full form names
							# This block attempts to update the urls found in the main document
							# with their long-form descriptions (for example, an exhibit may be labeled "Press Release."
							# This will find the url in the database and update the verbose_form_description with "Press Release,"
							# even though the form and form description are likely labeled "Additional Exhibits." This gives us
							# more specificity when searching for documents, because, for example, 
							# "Additional Exhibits" could almost be anything
							try:
								for url, description in URL(row.filing_url).verbose().items():
									uv = update(filings_table).where(filings_table.c.filing_url == url)
									uv = uv.values(verbose_form_description=description)
									engine.execute(uv)
							except Exception:
								pass

							# Updates the tsvector column
							su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
							engine.execute(su)

							print("Updated " + row.filing_url)

					except Exception as e:
						print(e)

						# If the request times out (generally because of a very large html file)
						# Updates the "archived" block to "T" (for "Timeout") for later processing

						u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u = u.values(archived='T')
						engine.execute(u)
						print("Error " + row.filing_url)

				elif ftype == 'primary' and ext == "txt" or ftype == 'primary' and ext == "htm" in row.filing_url\
				or ftype == 'primary' and ext == "TXT" or ftype == 'primary' and ext == "HTM" in row.filing_url:

					# Processes primary filings that are either text or html files only
					# Note: certain older filings that are now filed in XML would have been filed as .txt or .htm
					# This block will process those older filings, but later the database can be bulk updated
					# To remove unneeded/unwanted data. 

					try:

						# Block updates the full plain text and tsvector columns for the main filing in the database
						# Currently runs on a timeout decorator (2 seconds)
						# Times out if url request takes too long

						if __name__ == '__main__':
							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(filing_text=URL(row.filing_url).extract_text())
							engine.execute(u)

							# Locates hyperlinked documents in the main filing and iterates over them
							# Typically, the hyperlinks are exhibits with full form names
							# This block attempts to update the urls found in the main document
							# with their long-form descriptions (for example, an exhibit may be labeled "Press Release."
							# This will find the url in the database and update the verbose_form_description with "Press Release,"
							# even though the form and form description are likely labeled "Additional Exhibits." This gives us
							# more specificity when searching for documents, since "Additional Exhibits" could almost be anything
							try:
								for url, description in URL(row.filing_url).verbose().items():
									uv = update(filings_table).where(filings_table.c.filing_url == url)
									uv = uv.values(verbose_form_description=description)
									engine.execute(uv)
							except Exception:
								pass

							# Updates the tsvector column
							su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
							engine.execute(su)
							print("Updated " + row.filing_url)

					except Exception as e:
						print(e)

						# If the request times out (generally because of a very large html file)
						# Updates the "archived" block to "T" (for "Timeout") for later processing

						u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u = u.values(archived='T')
						engine.execute(u)
						print("Error " + row.filing_url)

				else:

					# The only files not directly processed in the script above would be primary filings (usually xml)
					# For now, archived is set at "P" (for "Primary") so I can build methods specific to a filing, 
					# similar to how methods for forms 3, 4, and 5 are built
					# Note: these are not yet primary priorities for the site. 

					# Here is a current list of the (33) forms that individual methods will need to be built for:
					# ['1-A', '1-K', '1-Z', '13F', '25', 'C', 'CFPORTAL', 'D', 'EFFECT', 
					# 'MA', 'MA-I', 'MA-W', 'N-CEN', 'N-MFP', 'N-MFP1', 'N-MFP2', 'NPORT', 'NPORT-NP', 
					# 'NPORT-P', 'QUALIF', SBSE', 'SBSE-A', 'SBSE-BD', 'SBSE-C', 'SBSE-W', 'SDR',
					# 'TA', 'TA-1', 'TA-2', 'TA-W', 'X-17A-5', 485BPOS, 497]

					#{"1-A":True, "1-A/A":True, "1-K":True, "1-K/A":True, "1-Z":True, "1-Z/A":True, }


					u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
					u = u.values(filing_text=None, financial_data=None, verbose_form_description=None, search_filing_text=None, archived='P')
					engine.execute(u)
					print("Updated " + row.filing_url)

			except Exception as e:
				print(e)

				# If there are errors other than Timeout errors, this will update the archived column to "E" (for "Error") for later processing

				u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
				u = u.values(archived='E')
				engine.exceute(u)
				print("Error " + row.filing_url)
		else:
			# Otherwise, if there are no new files to process, the function resets at the top. 
			pass

	elif datetime.datetime.today().weekday() < 5 and datetime.datetime.now().hour < 5:

		# This block attempts to reprocess any files that timed out. 
		# Because timed-out files can be large and take awhile to process, 
		# This makes it impractical to process during the filing day period
		# And processes these files between midnight and 5 a.m.

		sq = select([filings_table]).where(filings_table.c.archived == 'T').distinct(filings_table.c.filing_url)


		sqcount = 0

		for row in engine.execute(sq).fetchall():

			# Counts the number of filings where processed = "T"

			sqcount += 1

		if sqcount > 0:

			for row in engine.execute(sq).fetchall():

				ext = row.filing_url.split(".")[-1] # Url extension: html, xml, pdf, etc.
				ftype = row.filing_type

				try:

					if ftype == 'exhibit' and ext == "txt" or ftype == 'exhibit' and ext == "htm"\
					or ftype == 'exhibit' and ext == ".TXT" or ftype == 'exhibit' and ext == "HTM":

						try:

							# This block updates the full plain text and tsvector columns for exhibits in the database
							# DOES NOT run on a timeout decorator
							# Still times out if url request takes too long (a general Timeout exception)

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(filing_text=URL(row.filing_url).extract_text())
							engine.execute(u)

							su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
							engine.execute(su)
							print("Updated " + row.filing_url)

						except Exception:

							# If the request times out (generally because of a very large html file)
							# Updates the "archived" block to "X" for later processing
							# Note: I've designated "X" as a random variable to annotate that
							# the script has attempted to process the filing more than 
							# once and has still encountered errors. 

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(archived='X')
							engine.execute(u)
							print("Error " + row.filing_url)


					elif row.form == "3" or row.form == "3/A":
						# Processes forms 3 and 3/A

						if ".xml" not in row.filing_url:

							# Older filings are not in xml; there's currently no efficient way to process them,
							# so they are simply updated to archived='Y'

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(archived='Y')
							engine.execute(u)

						elif len(row.filing_url.split("/")) == 9:

							# Two types of form 3 and 3/A: XML and HTML
							# The XML filing url is a modification of the HTML file url
							# So the XML version is deleted

							d = delete(filings_table).where(filings_table.c.filing_url == row.filing_url)
							engine.execute(d)
							print("Deleted: " + row.filing_url)

						else:

							# The "get_ownership()" method temporarily modifies the HMTL url to XML (built into the method), 
							# and retrieves and updates the XML data in the financial_data column
							# This is done so we can both use the HTML url for linking out to display
							# and process the XML at the same time

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(financial_data=json.dumps(URL(row.filing_url).get_ownership()), archived='Y')
							engine.execute(u)
							print("Updated: " + row.filing_url)


					elif row.form == "4" or row.form == "4/A" or row.form == '5' or row.form == '5/A':

							# Processes forms 4, 4/A, 5, and 5/A

						if ".xml" not in row.filing_url:

							# Older filings are not in xml; there's currently no efficient way to process them,
							# so they are simply updated to archived='Y'

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(archived='Y')
							engine.execute(u)



						elif len(row.filing_url.split("/")) == 9:

							# Two types of form 3 and 3/A: XML and HTML
							# The XML filing url is a modification of the HTML file url
							# So the XML version is deleted

							d = delete(filings_table).where(filings_table.c.filing_url == row.filing_url)
							engine.execute(d)
							print("Deleted: " + row.filing_url)

						else:

							# The "update_change_ownership()" method temporarily modifies the HMTL url to XML (built into the method), 
							# and retrieves and updates the XML data in the financial_data column
							# This is done so we can both use the HTML url for linking out to display
							# and process the XML at the same time

							u1 = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u1 = u1.values(financial_data=json.dumps(URL(row.filing_url).update_change_ownership()), archived='Y')
							engine.execute(u1)
							print("Updated: " + row.filing_url)



					elif row.form == '8-K' or row.form == '8-K/A':

						# Processes forms 8-K and 8-K/A
						# These forms are special because there is metadata in the index file that needs to be collected

						ixfile = Util.gen_ixfile(row.central_index_key, row.filing_id) # Generates and index file url for the filing to be crawled

						try:

							# Block updates the full plain text and tsvector columns for the main (not index) filing in the database
							# DOES NOT run on a timeout decorator


							# Also updates the metadata in the verbose_form_description column, using the previously generated index file url (line 454)

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(filing_text=URL(row.filing_url).extract_text(), verbose_form_description=IndexUrl(ixfile).current())
							engine.execute(u)

							# Locates hyperlinked documents in the main filing and iterates over them
							# Typically, the hyperlinks are exhibits with full form names
							# This block attempts to update the urls found in the main document
							# with their long-form descriptions (for example, an exhibit may be labeled "Press Release."
							# This will find the url in the database and update the verbose_form_description with "Press Release,"
							# even though the form and form description are likely labeled "Additional Exhibits." This gives us
							# more specificity when searching for documents, because, for example, 
							# "Additional Exhibits" could almost be anything
							try:
								for url, description in URL(row.filing_url).verbose().items():
									uv = update(filings_table).where(filings_table.c.filing_url == url)
									uv = uv.values(verbose_form_description=description)
									engine.execute(uv)
							except Exception:
								pass

							# Updates the tsvector column
							su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
							engine.execute(su)

							print("Updated " + row.filing_url)

						except Exception:

							# If the request times out (generally because of a very large html file)
							# Updates the "archived" block to "X" for later processing
							# Note: I've designated "X" as a random variable to annotate that
							# the script has attempted to process the filing more than 
							# once and has still encountered errors.

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(archived='X')
							engine.execute(u)
							print("Error " + row.filing_url)

					elif ftype == 'primary' and ext == "txt" or ftype == 'primary' and ext == "htm" in row.filing_url\
					or ftype == 'primary' and ext == "TXT" or ftype == 'primary' and ext == "HTM" in row.filing_url:

						# Processes primary filings that are either text or html files only
						# Note: certain older filings that are now filed in XML would have been filed as .txt or .htm
						# This block will process those older filings, but later the database can be bulk updated
						# To remove unneeded/unwanted data. 

						try:

							# This block updates the full plain text and tsvector columns for the main filing in the database
							# Currently runs on a timeout decorator (2 seconds)
							# Times out if url request takes too long

							if __name__ == '__main__':
								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(filing_text=URL(row.filing_url).extract_text())
								engine.execute(u)

								# Locates hyperlinked documents in the main filing and iterates over them
								# Typically, the hyperlinks are exhibits with full form names
								# This block attempts to update the urls found in the main document
								# with their long-form descriptions (for example, an exhibit may be labeled "Press Release."
								# This will find the url in the database and update the verbose_form_description with "Press Release,"
								# even though the form and form description are likely labeled "Additional Exhibits." This gives us
								# more specificity when searching for documents, since "Additional Exhibits" could almost be anything
								try:
									for url, description in URL(row.filing_url).verbose().items():
										uv = update(filings_table).where(filings_table.c.filing_url == url)
										uv = uv.values(verbose_form_description=description)
										engine.execute(uv)
								except Exception:
									pass

								# Updates the tsvector column
								su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
								engine.execute(su)
								print("Updated " + row.filing_url)

						except Exception:

							# If the request times out (generally because of a very large html file)
							# Updates the "archived" block to "X" for later processing
							# Note: I've designated "X" as a random variable to annotate that
							# the script has attempted to process the filing more than 
							# once and has still encountered errors.

							u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
							u = u.values(archived='X')
							engine.execute(u)
							print("Error " + row.filing_url)


				except Exception:

					# If there are general errors, this will update the archived column to "E" (for "Error") for later processing
					# Note: I've designated "X" as a random variable to annotate that
					# the script has attempted to process the filing more than 
					# once and has still encountered errors.

					u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
					u = u.values(archived='X')
					engine.excecute(u)
					print("Error " + row.filing_url)

		else:

			eq = select([filings_table]).where(filings_table.c.archived == 'E').distinct(filings_table.c.filing_url)


			eqcount = 0

			for row in engine.execute(eq).fetchall():

				# Counts the number of filings where processed = "E"

				eqcount += 1

			if eqcount > 0:

				for row in engine.execute(sq).fetchall():

					ext = row.filing_url.split(".")[-1] # Url extension: html, xml, pdf, etc.
					ftype = row.filing_type

					try:

						if ftype == 'exhibit' and ext == "txt" or ftype == 'exhibit' and ext == "htm"\
						or ftype == 'exhibit' and ext == ".TXT" or ftype == 'exhibit' and ext == "HTM":

							try:

								# This block updates the full plain text and tsvector columns for exhibits in the database
								# DOES NOT run on a timeout decorator
								# Still times out if url request takes too long (a general Timeout exception)

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(filing_text=URL(row.filing_url).extract_text())
								engine.execute(u)

								su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
								engine.execute(su)
								print("Updated " + row.filing_url)

							except Exception:

								# If the request times out (generally because of a very large html file)
								# Updates the "archived" block to "X" for later processing
								# Note: I've designated "X" as a random variable to annotate that
								# the script has attempted to process the filing more than 
								# once and has still encountered errors. 

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(archived='X')
								engine.execute(u)
								print("Error " + row.filing_url)


						elif row.form == "3" or row.form == "3/A":
							# Processes forms 3 and 3/A

							if ".xml" not in row.filing_url:

								# Older filings are not in xml; there's currently no efficient way to process them,
								# so they are simply updated to archived='Y'

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(archived='Y')
								engine.execute(u)

							elif len(row.filing_url.split("/")) == 9:

								# Two types of form 3 and 3/A: XML and HTML
								# The XML filing url is a modification of the HTML file url
								# So the XML version is deleted

								d = delete(filings_table).where(filings_table.c.filing_url == row.filing_url)
								engine.execute(d)
								print("Deleted: " + row.filing_url)

							else:

								# The "get_ownership()" method temporarily modifies the HMTL url to XML (built into the method), 
								# and retrieves and updates the XML data in the financial_data column
								# This is done so we can both use the HTML url for linking out to display
								# and process the XML at the same time

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(financial_data=json.dumps(URL(row.filing_url).get_ownership()), archived='Y')
								engine.execute(u)
								print("Updated: " + row.filing_url)


						elif row.form == "4" or row.form == "4/A" or row.form == '5' or row.form == '5/A':

								# Processes forms 4, 4/A, 5, and 5/A

							if ".xml" not in row.filing_url:

								# Older filings are not in xml; there's currently no efficient way to process them,
								# so they are simply updated to archived='Y'

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(archived='Y')
								engine.execute(u)



							elif len(row.filing_url.split("/")) == 9:

								# Two types of form 3 and 3/A: XML and HTML
								# The XML filing url is a modification of the HTML file url
								# So the XML version is deleted

								d = delete(filings_table).where(filings_table.c.filing_url == row.filing_url)
								engine.execute(d)
								print("Deleted: " + row.filing_url)

							else:

								# The "update_change_ownership()" method temporarily modifies the HMTL url to XML (built into the method), 
								# and retrieves and updates the XML data in the financial_data column
								# This is done so we can both use the HTML url for linking out to display
								# and process the XML at the same time

								u1 = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u1 = u1.values(financial_data=json.dumps(URL(row.filing_url).update_change_ownership()), archived='Y')
								engine.execute(u1)
								print("Updated: " + row.filing_url)



						elif row.form == '8-K' or row.form == '8-K/A':

							# Processes forms 8-K and 8-K/A
							# These forms are special because there is metadata in the index file that needs to be collected

							ixfile = Util.gen_ixfile(row.central_index_key, row.filing_id) # Generates and index file url for the filing to be crawled

							try:

								# Block updates the full plain text and tsvector columns for the main (not index) filing in the database
								# DOES NOT run on a timeout decorator


								# Also updates the metadata in the verbose_form_description column, using the previously generated index file url (line 454)

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(filing_text=URL(row.filing_url).extract_text(), verbose_form_description=IndexUrl(ixfile).current())
								engine.execute(u)

								# Locates hyperlinked documents in the main filing and iterates over them
								# Typically, the hyperlinks are exhibits with full form names
								# This block attempts to update the urls found in the main document
								# with their long-form descriptions (for example, an exhibit may be labeled "Press Release."
								# This will find the url in the database and update the verbose_form_description with "Press Release,"
								# even though the form and form description are likely labeled "Additional Exhibits." This gives us
								# more specificity when searching for documents, because, for example, 
								# "Additional Exhibits" could almost be anything
								try:
									for url, description in URL(row.filing_url).verbose().items():
										uv = update(filings_table).where(filings_table.c.filing_url == url)
										uv = uv.values(verbose_form_description=description)
										engine.execute(uv)
								except Exception:
									pass

								# Updates the tsvector column
								su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
								engine.execute(su)

								print("Updated " + row.filing_url)

							except Exception:

								# If the request times out (generally because of a very large html file)
								# Updates the "archived" block to "X" for later processing
								# Note: I've designated "X" as a random variable to annotate that
								# the script has attempted to process the filing more than 
								# once and has still encountered errors.

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(archived='X')
								engine.execute(u)
								print("Error " + row.filing_url)

						elif ftype == 'primary' and ext == "txt" or ftype == 'primary' and ext == "htm" in row.filing_url\
						or ftype == 'primary' and ext == "TXT" or ftype == 'primary' and ext == "HTM" in row.filing_url:

							# Processes primary filings that are either text or html files only
							# Note: certain older filings that are now filed in XML would have been filed as .txt or .htm
							# This block will process those older filings, but later the database can be bulk updated
							# To remove unneeded/unwanted data. 

							try:

								# This block updates the full plain text and tsvector columns for the main filing in the database
								# Currently runs on a timeout decorator (2 seconds)
								# Times out if url request takes too long


								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(filing_text=URL(row.filing_url).extract_text())
								engine.execute(u)

								# Locates hyperlinked documents in the main filing and iterates over them
								# Typically, the hyperlinks are exhibits with full form names
								# This block attempts to update the urls found in the main document
								# with their long-form descriptions (for example, an exhibit may be labeled "Press Release."
								# This will find the url in the database and update the verbose_form_description with "Press Release,"
								# even though the form and form description are likely labeled "Additional Exhibits." This gives us
								# more specificity when searching for documents, since "Additional Exhibits" could almost be anything

								try:
									for url, description in URL(row.filing_url).verbose().items():
										uv = update(filings_table).where(filings_table.c.filing_url == url)
										uv = uv.values(verbose_form_description=description)
										engine.execute(uv)
								except Exception:
									pass

								# Updates the tsvector column
								su = u.values(search_filing_text=func.to_tsvector('English', filings_table.c.filing_text), archived='Y')
								engine.execute(su)
								print("Updated " + row.filing_url)

							except Exception:

								# If the request times out (generally because of a very large html file)
								# Updates the "archived" block to "X" for later processing
								# Note: I've designated "X" as a random variable to annotate that
								# the script has attempted to process the filing more than 
								# once and has still encountered errors.

								u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
								u = u.values(archived='X')
								engine.execute(u)
								print("Error " + row.filing_url)


					except Exception:

						# If there are general errors, this will update the archived column to "E" (for "Error") for later processing
						# Note: I've designated "X" as a random variable to annotate that
						# the script has attempted to process the filing more than 
						# once and has still encountered errors.

						u = update(filings_table).where(filings_table.c.filing_url == row.filing_url)
						u = u.values(archived='X')
						engine.excecute(u)
						print("Error " + row.filing_url)

			else:
				# Otherwise, if it is a Saturday or Sunday, the whole program sleeps for 1 hour, every hour
				print("Sleeping...")
				time.sleep(1800)
	else:
		# Otherwise, if it is a Saturday or Sunday, the whole program sleeps for 1 hour, every hour
		print("Sleeping...")
		time.sleep(1800)




