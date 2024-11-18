This is old, unfinished code I’d written for scraping the Securities Exchange Commission’s website for financial data from publicly traded companies. 
This code was last updated December 27th, 2019, and includes new functions for XBRL that still have some kinks to be worked out.

api_dump.py drops annual filing into Postgres by company. From there I intended to serve the data as JSON objects via API so that querying a company, year, and specific forms could be achieved.
financialsModule.py sifts through companies and locates the balance sheets and drops them into Postgres as JSON objects
iterModule.py includes general data to be used in queries like form names, descriptions, industries, categories, unique identifiers, exhibits, etc.
FinClasses.py is a group of classes and class-based modules for processing SEC urls, central index keys, filings, types, tickers, news, etc., and utility functions for creating SQL tables in Postgres
xbrl_sandbox.py includes some methods for gathering the separate XBRL financial data files and synthesizing them as cohesive financial document. 
Main_run.py is the main script I’d use to call many of these functions depending on what I wanted to do. 

GENERAL INFORMATION

1. The SEC website is very large and stores financial documents of publicly traded companies dating back to the 90s. 
2. They have made their data accessible via automated means (you must stay within the rate limit)
3. The first task the SEC had to make the data available was to index every company using a unique identifier called a Central Index Key
4. To locate a company, you need to query the the sec website and add slash “/“ and the CIK
5. This opens a file structure for the company separated by years. Add the year to the url and another file structure will open up with all the forms and descriptions filed for that year. 
6. File names have no logic, so the form number and description section must be determined while retrieving the file. 
7. From there, you can get whatever data you need and drop it into a database


GENERAL USE

1. This code was written by an amateur (me). It is commented well in places, others, not so much. If you’d like to use this code, you may have to review it to figure out what I was trying to do. 
2. The most useful modules will be FinClasses, xbrl_sandbox, and iterModule. The other modules I’d written to update SQL databases with the information I gathered. 
3. The SEC started allowing use of XBRL around 2005, but most filers didn’t start consistently filing with XBRL until 2012-2013, so the XBRL is really only useful from 2013 onwards
