from sqlalchemy import *
import psycopg2; import codecs; import inspect; import datetime; import time
import sys; import tablesModule as db; from sqlalchemy.dialects.postgresql import TSVECTOR; import json; import requests;
from stem import Signal; from stem.control import Controller; import socket;
import socks; import urllib.request; import csv; from bs4 import BeautifulSoup; import string;
import iterModule as im; import timeout_decorator


def pop_financials(engine, metadata):
	#NOTE: This is a one-time updater function since the financial data is far less than the filings table
	# So we can iterate the annuals in one function; takes approximately ~15 mins. Just call db.pop_financials(engine, metadata)
	# In the main file and run

	financials = db.financials(metadata)

	# Initialize dictionary for all filers
	filers = {}



	#RUN 10-K, 20-F, 40-F THROUGH FIRST BLOCK

	# Iterate over the years for all financials
	for n in range(2013, 2020)[::-1]:
		print("Gathering ciks from year " + str(n) + ".")
		table = db.tmp_financials(metadata, n)
		#Iteration successively selects central_index_keys from the financialsYYYY table, 2013-2019

		# Gather data from the annual reports (not amended)
		r = select([table]).distinct(table.c.central_index_key).where(or_(
				  and_(table.c.stmnt != None, table.c.form == "10-K", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "10-K", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "10-KT", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "10-KT", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "20-F", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "20-F", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "40-F", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "40-F", table.c.qrtrs == 4)))
		#Selects only those tables whose input is given ('10-K', '20-F', etc.)

		for row in engine.execute(r).fetchall():
			#Creates preliminary dictionary consisting of the central_index_key and the desired financial statements
			filers.update({row.central_index_key:{"Metadata":{}, "Balance Sheet":{}, "Income Statement":{}, "Cash Flow":{}, "Comprehensive Income":{}}})


	# Iterate over the years again, populating with data (if we iterate once, the data will be overwritten, so empty values are created first, above)
	for n in range(2013, 2020)[::-1]:
		print("Gathering data from year " + str(n) + ".")
		#Second iteration to gather the data from financialsYYYY tables
		table = db.tmp_financials(metadata, n)

		q = select([table]).where(or_(
				  and_(table.c.stmnt != None, table.c.form == "10-K", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "10-K", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "10-KT", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "10-KT", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "20-F", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "20-F", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "40-F", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "40-F", table.c.qrtrs == 4))).order_by(table.c.ddate).order_by(table.c.line)
		#Selects only those values that match the input form

		for row in engine.execute(q).fetchall():
			#Gathers entries and creates sub-dictionaries for the CIK, adds dates
			if row.stmnt == "BS":
				#BS = Balance sheet values
				filers[row.central_index_key]["Balance Sheet"].update({str(row.ddate):{}})
			elif row.stmnt == "IS":
				#IS = Income Statement values
				filers[row.central_index_key]["Income Statement"].update({str(row.ddate):{}})
			elif row.stmnt == "CF":
				#CF = Cash Flow Statement values
				filers[row.central_index_key]["Cash Flow"].update({str(row.ddate):{}})
			elif row.stmnt == "CI":
				#CF = Comprehensive Income
				filers[row.central_index_key]["Comprehensive Income"].update({str(row.ddate):{}})
			elif row.stmnt == "CP":
				#CP = Metadata
				filers[row.central_index_key]["Metadata"].update({str(row.ddate):{}})


		for row in engine.execute(q).fetchall():
			#Reselects and gathers the label or tag ('Assets', 'Liabilities', etc.) and pairs them with their values in the dictionary
			# That matches the central_index_key as well as the reported date and statement type into the filers dictionary
			if row.stmnt == "BS":
				#Balance sheet values
				try:
					filers[row.central_index_key]["Balance Sheet"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
				except Exception:
					filers[row.central_index_key]["Balance Sheet"][str(row.ddate)].update({row.tag:float(row.uom_value)})
			elif row.stmnt == "IS":
				#Income statement values
				try:
					filers[row.central_index_key]["Income Statement"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
				except Exception:
					filers[row.central_index_key]["Income Statement"][str(row.ddate)].update({row.tag:float(row.uom_value)})
			elif row.stmnt == "CF":
				#Cash flow values
				try:
					filers[row.central_index_key]["Cash Flow"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
				except Exception:
					filers[row.central_index_key]["Cash Flow"][str(row.ddate)].update({row.tag:float(row.uom_value)})
			elif row.stmnt == "CI":
				#Cash flow values
				try:
					filers[row.central_index_key]["Comprehensive Income"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
				except Exception:
					filers[row.central_index_key]["Comprehensive Income"][str(row.ddate)].update({row.tag:float(row.uom_value)})
			elif row.stmnt == "CP":
				#Cash flow values
				try:
					filers[row.central_index_key]["Metadata"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
				except Exception:
					filers[row.central_index_key]["Metadata"][str(row.ddate)].update({row.tag:float(row.uom_value)})



	for n in range(2013, 2020):
		# This section iterates through the amended filings to update the filers dictionary

		print("Gathering amended data from year " + str(n) + ".")
		table = db.tmp_financials(metadata, n)

		# Select the amended filings
		q = select([table]).where(or_(
				  and_(table.c.stmnt != None, table.c.form == "10-K/A", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "10-K/A", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "10-KT/A", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "10-KT/A", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "20-F/A", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "20-F/A", table.c.qrtrs == 4),
				  and_(table.c.stmnt != None, table.c.form == "40-F/A", table.c.qrtrs == 0), 
				  and_(table.c.stmnt != None, table.c.form == "40-F/A", table.c.qrtrs == 4),
				  )).order_by(table.c.ddate).order_by(table.c.line)


		for row in engine.execute(q).fetchall():
			# Update the filers dictionary that matches the central_index_key 
			#as well as the reported date and statement type 
			try:
				if row.stmnt == "BS":
					#Balance sheet values
					try:
						filers[row.central_index_key]["Balance Sheet"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
					except Exception:
						filers[row.central_index_key]["Balance Sheet"][str(row.ddate)].update({row.tag:float(row.uom_value)})
				elif row.stmnt == "IS":
					#Income statement values
					try:
						filers[row.central_index_key]["Income Statement"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
					except Exception:
						filers[row.central_index_key]["Income Statement"][str(row.ddate)].update({row.tag:float(row.uom_value)})
				elif row.stmnt == "CF":
					#Cash flow values
					try:
						filers[row.central_index_key]["Cash Flow"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
					except Exception:
						filers[row.central_index_key]["Cash Flow"][str(row.ddate)].update({row.plabel.tag:float(row.uom_value)})
				elif row.stmnt == "CI":
					#Income statement values
					try:
						filers[row.central_index_key]["Comprehensive Income"][str(row.ddate)].update({row.tag:float(row.uom_value)})
					except Exception:
						filers[row.central_index_key]["Comprehensive Income"][str(row.ddate)].update({row.tag:float(row.uom_value)})
				elif row.stmnt == "CP":
					#Cash flow values
					try:
						filers[row.central_index_key]["Metadata"][str(row.ddate)].update({row.plabel.title():float(row.uom_value)})
					except Exception:
						filers[row.central_index_key]["Metadata"][str(row.ddate)].update({row.tag:float(row.uom_value)})
			except Exception:
				pass


	for k, v in filers.items():

		# Does NOT return an object

		#Iterates through the filer dictionary, extracts each sub-dictionary within the "filers" dictionary, 
		#Inserts the values in the financials table

		ins = financials.insert().values(central_index_key=k, annuals_api=json.dumps(v))
		engine.execute(ins)

		"""
		# Use update on subsequent updates.

		u = update(financials).where(financials.c.central_index_key == k)
		u = u.values(annuals_api=json.dumps(v))
		engine.execute(u)
		"""
		print("CIK " + str(k) + " inserted!")


def rmv_fin_duplicates(engine, financials):
	# Clean up annuals_api; remove duplicates
	# Used on the financials table
	s = select([financials]).where(financials.c.annuals_api != None)
	for row in engine.execute(s).fetchall():
		# Loads the data as a json object
		data = json.loads(row.annuals_api)
		# Initialize placeholder dictionaries
		filer = {}
		meta = {}
		balance = {}
		income = {}
		cincome = {}
		cash = {}
		# Sort the information by sheet; update
		for k, v in data["Metadata"].items():
			meta.update({k:v})
		for k, v in data["Balance Sheet"].items():
			balance.update({k:v})
		for k, v in data["Income Statement"].items():
			income.update({k:v})
		for k, v in data["Comprehensive Income"].items():
			cincome.update({k:v})
		for k, v in data["Cash Flow"].items():
			cash.update({k:v})
		# Load the placheholder dictionaries into the filer dictionary
		# Update the values
		filer.update({row.central_index_key:{"Metdata":meta, "Balance Sheet":balance, "Income Statement":income, "Comprehensive Income":cincome, "Cash Flow":cash}})
		u = update(financials).where(financials.c.central_index_key == row.central_index_key)
		u = u.values(annuals_api=json.dumps(filer))
		#Print the result
		print(str(row.central_index_key) + " financials cleaned.")




