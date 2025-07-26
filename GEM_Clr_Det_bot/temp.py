import pytesseract
from PIL import Image
import PIL.Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import time
import json
import db_connect as db
import mail
from fuzzywuzzy import fuzz
import web_interface as wi
import datetime


query = """select * from tender.gem_res_details where
t_id in ('GEM_2023_B_3964212');"""

data = db.get_data_in_list_of_tuple(query)

clr = data[0][13]
res = data[0][12]

clr_dict = clr['0'][0]
res_dict = res['0']
