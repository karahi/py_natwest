#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
import os, re, sys, time, datetime, yaml, getpass

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select, WebDriverWait

from .constants import NATWEST_URL

def get_newest_file(path):
    files = os.listdir(path)
    paths = [os.path.join(path, basename) for basename in files]
    return max(paths, key=os.path.getctime)



class ConfigManager():
    def __init__(self, credentials_file=None, pass_credentials='n'):
        if pass_credentials=='n' and not credentials_file is None:
            with open(credentials_file, 'r') as stream:
                try:
                    self.config = yaml.load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
        else:
            self.config={}

            while(True):
                customer_number = getpass.getpass("Enter customer number for autotype: ")
                customer_number = customer_number.strip()
                if len(customer_number)>10:
                    print("customer number should only be 10 digits!")
                else:
                    break

            while(True):
                pin_no = getpass.getpass("Enter Natwest PIN for autotype: ")
                pin_no = pin_no.strip()
                if len(pin_no)>4:
                    print("Pin number should only be 4 digits!")
                else:
                    break

            passwd = getpass.getpass("Enter Natwest password for autotype: ")
            self.config['customer_number']=customer_number
            self.config['pin']=pin_no
            self.config['password']=passwd

    def get_config(self):
        if not self.config:
            sys.stderr.write('Unable to read config')
            sys.exit(1)
        else:
            return self.config


class Natwest():
    timeout = 10

    def __init__(self,credentials_file=None,download_location=None,command=None, pass_credentials='n'):
        #        display = pyvirtualdisplay.Display(visible=0, size=(1280, 1024,))
        #        display.start()
        print('  Setting up Firefox...')
        if credentials_file is None:
            credentials_file=os.path.expanduser('~/.ssh/.py_natwest.yml')
        self.credentials_file=credentials_file

        self.pass_credentials=pass_credentials

        if download_location is None:
            download_location=os.path.expanduser("~/'Downloads/bank_statements'")
        self.download_location = download_location

        if not os.path.isdir(download_location):
            os.mkdirs(download_location)

        if command is None:
            command='transactions'
        self.command=command

        ff_profile=self.get_profile()

        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')

        self.driver = webdriver.Firefox(firefox_profile=ff_profile,options=options)

        self.config = ConfigManager(credentials_file,pass_credentials=pass_credentials).get_config()


    # main functions
    def fetch(self):
        print('  Going to %s...'%NATWEST_URL)
        self.get_page()
        print('  Entering customer number')
        self.enter_customer_number()
        print('  Entering PIN and password')
        self.login()
        self.download_statement_alternative()
        newest_file = get_newest_file(self.download_location)
        return newest_file


    def get_profile(self):

        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.preferences.instantApply", True)

        profile.set_preference("browser.privatebrowsing.autostart", True)
        profile.set_preference('browser.download.folderList', 2)
        profile.set_preference('browser.download.manager.showWhenStarting', False)

        profile.set_preference('browser.download.dir', self.download_location)
        profile.set_preference("browser.download.useDownloadDir", True);

        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'mimetypes'),'r') as mime_file:
            mime_type_lines=mime_file.readlines()
            mime_types=",".join(mime_type_lines).replace('\n','')

        profile.set_preference("browser.helperApps.neverAsk.saveToDisk",mime_types)
        profile.set_preference("browser.helperApps.alwaysAsk.force", False)
        profile.set_preference("browser.download.manager.showWhenStarting", False)
        profile.set_preference("browser.download.manager.focusWhenStarting", False);
        profile.set_preference("browser.helperApps.alwaysAsk.force", False);
        profile.set_preference("browser.download.panel.shown",False);

        return profile

    def get_page(self):
        self.driver.get(NATWEST_URL)

    def wait_for_iframe_load(self):
        try:
            # Waiting until iframe loads
            element_present = expected_conditions.presence_of_element_located((By.ID, 'aspnetForm'))
            WebDriverWait(self.driver, self.timeout).until(element_present)
        except TimeoutException:
            sys.stderr.write('Timed out waiting for iframe to load')
            sys.exit(1)
        # Additional time for load js with title...
        time.sleep(2)

    def enter_customer_number(self):
        try:
            # Waiting until iframe loads
            element_present = expected_conditions.presence_of_element_located((By.ID, 'ctl00_secframe'))
            WebDriverWait(self.driver, self.timeout).until(element_present)
        except TimeoutException:
            sys.stderr.write('Timed out waiting for page to load')
            sys.exit(1)

        self.driver.switch_to.frame(
            self.driver.find_element_by_id('ctl00_secframe')
        )

        self.wait_for_iframe_load()
        if self.driver.title != 'Log in to Online Banking':
            sys.stderr.write('Wrong page title')
            sys.exit(1)

        form = self.driver.find_element_by_name('aspnetForm')
        customer_number = form.find_element_by_id('ctl00_mainContent_LI5TABA_CustomerNumber_edit')
        customer_number.send_keys(self.config['customer_number'])
        form.submit()
        self.driver.switch_to.default_content()

    def login(self):
        try:
            # Waiting until iframe loads
            element_present = expected_conditions.presence_of_element_located((By.ID, 'ctl00_secframe'))
            WebDriverWait(self.driver, self.timeout).until(element_present)
        except TimeoutException:
            sys.stderr.write('Timed out waiting for page to load')
            sys.exit(1)

        self.driver.switch_to.frame(
            self.driver.find_element_by_id('ctl00_secframe')
        )

        self.wait_for_iframe_load()
        # something wrong with wait for iframe load...
        if self.driver.title.encode('utf8') != 'Log in – PIN and password details':
            sys.stderr.write('Wrong page title')
            sys.exit(1)

        form = self.driver.find_element_by_name('aspnetForm')
        pin = list(self.config['pin'])
        password = list(self.config['password'])
        i = 0
        for char in 'ABCDEF':
            element = form.find_element_by_id('ctl00_mainContent_Tab1_LI6DDAL{0}Label'.format(char))
            psk = re.search('Enter the (\d+)[a-z]{2}', element.text)
            char_num = int(psk.group(1)) - 1
            if i <= 2:
                psk = pin[char_num]
            else:
                psk = password[char_num]

            customer_number = form.find_element_by_id('ctl00_mainContent_Tab1_LI6PPE{0}_edit'.format(char))
            customer_number.send_keys(psk)
            i += 1

        form.submit()

    # TODO: project should be suspended till natwest repair this function...
    def download_statement(self):
        self.wait_for_iframe_load()
        if self.driver.title != 'Account summary':
            sys.stderr.write('Wrong page title')
            sys.exit(1)

        # click statements link
        self.driver.find_element_by_link_text('Statements').click()
        self.driver.find_element_by_link_text('Download or export transactions').click()
        self.wait_for_iframe_load()
        form = self.driver.find_element_by_name('aspnetForm')
        time_period = Select(form.find_element_by_id('ctl00_mainContent_SS6SPDDA'))
        export_type = Select(form.find_element_by_id('ctl00_mainContent_SS6SDDDA'))
        '''
        Available time period:
        - Since last download
        - Last week
        - Last two weeks
        - Last 1 month (4 weeks)
        - Last 2 months
        - Last 3 months
        - Last 4 months
        Available Format Types:
        - Excel, Lotus 123, Text (CSV file)  
        '''
        time_period.select_by_visible_text('Last two weeks')
        export_type.select_by_visible_text('Excel, Lotus 123, Text (CSV file)')
        form.submit()
        # catching errors
        form_error = self.driver.find_element_by_id('ctl00_mainContent_ValidationSummary').text
        if form_error != "":
            sys.stderr(form_error)
            sys.exit(1)

    def download_statement_alternative(self):
        self.wait_for_iframe_load()
        if self.driver.title != 'Account summary':
            sys.stderr.write('Wrong page title')
            sys.exit(1)

        # click statements link
        print('  Navigating to statements section')
        self.driver.find_element_by_link_text('Statements').click()
        self.driver.find_element_by_link_text('Download or export transactions').click()
        self.driver.find_element_by_link_text('Or search between two dates').click()


        form = self.driver.find_element_by_name('aspnetForm')
        #time_period = Select(form.find_element_by_id('ctl00_mainContent_VT2SPDDA'))

        print('  Setting statement dates')
        day_input=form.find_element_by_id('ctl00_mainContent_SS6DEB_day')
        month_selector=Select(form.find_element_by_id('ctl00_mainContent_SS6DEB_month'))
        year_selector=Select(form.find_element_by_id('ctl00_mainContent_SS6DEB_year'))

        last_year_day_input = form.find_element_by_id('ctl00_mainContent_SS6DEA_day')
        last_year_month_selector = Select(form.find_element_by_id('ctl00_mainContent_SS6DEA_month'))
        last_year_year_selector = Select(form.find_element_by_id('ctl00_mainContent_SS6DEA_year'))

        output_format_selector = Select(form.find_element_by_id('ctl00_mainContent_SS6SDDDA'))

        #transaction_type = Select(form.find_element_by_id('ctl00_mainContent_VT2TTDDA'))
        '''
        Available transaction types:
        - All Transactions
        - ATM Transaction
        - Cash & Dep Machine
        - Charges
        - Cheques
        - Credit Transactions
        - Debit Transactions
        - Direct Debits
        - Dividends
        - Interest
        - International Transactions
        - Payroll
        - Standing Orders
        - Debit Card Payments
        - Telephone Banking
        - OnLine Banking        
        '''
        #time_period.select_by_visible_text('Last two weeks')
        #transaction_type.select_by_visible_text('All Transactions')

        now = datetime.datetime.now()
        day_str = now.day
        month_str = now.strftime('%b')
        year_str = str(now.year)

        last_year =  now - datetime.timedelta(days=364)
        ly_day_str = last_year.day
        ly_month_str = last_year.strftime('%b')
        ly_year_str = str(last_year.year)

        
        last_year_day_input.click();
        last_year_day_input.clear()
        last_year_day_input.send_keys(ly_day_str);
        last_year_month_selector.select_by_visible_text(ly_month_str)
        last_year_year_selector.select_by_visible_text(ly_year_str)
    
        day_input.click();
        day_input.clear();
        day_input.send_keys(day_str);
        month_selector.select_by_visible_text(month_str)
        year_selector.select_by_visible_text(year_str)

        #output_format_selector.select_by_visible_text('Microsoft Money (OFX file)')
        output_format_selector.select_by_visible_text('Excel, Lotus 123, Text (CSV file)')


        form.find_element_by_id('ctl00_mainContent_FinishButton_button').click()


#        form.submit()
        self.wait_for_iframe_load()
        form = self.driver.find_element_by_name('aspnetForm')

        form.find_element_by_id('ctl00_mainContent_SS7-LWLA_button_button').click()
        print('  Waiting for download')
        time.sleep(3)
        while(True):
            current_files = os.listdir(self.download_location)
            part_files = [f for f in files if f[-5:]==".part"]
            if len(part_files)>0:
                print
            time.sleep(10)
        self.driver.close()

#        form = self.driver.find_element_by_name('aspnetForm')
#        form.find_element_by_id('ctl00_mainContent_VT2ITCHF').click()
#        select_format = Select(form.find_element_by_id('ctl00_mainContent_VTSDDDA'))
#        select_format.select_by_visible_text('Excel, Lotus 123, Text (CSV file)')
#        self.wait_for_iframe_load()
#        form = self.driver.find_element_by_name('aspnetForm')
#        form.find_element_by_id('ctl00_mainContent_SS7-LWLA_button_button').click()



