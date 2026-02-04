import os
from pathlib import Path
import random
from src.utils.browser import BrowserManager
from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.utils.login import Login

from src.wits.navigation import select_existing_query
from src.wits.navigation import navigate_to_advanced_query
from src.wits.reporter import modify_reporter
from src.wits.reporter import click_final_submit    

class ExecuteQueryBot:
    def __init__(self, config):
        self.config = config
        self.logger = setup_logger(name='execute_query')
        self.browser_manager = None
        self.page = None
        self.setup_dirs()
        
    def setup_dirs(self):
        self.logger.info("Setting up directories...")
        cur_dir = os.getcwd()
        output_dir = Path(cur_dir) / 'output' / 'queries'
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        self.done_dir = output_dir / 'done'
        self.done_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir = output_dir / 'failed'
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def start_browser(self):
        self.logger.info("Starting browser...")
        self.browser_manager = BrowserManager(self.config)
        self.page = self.browser_manager.start()
    
    def login(self):
        self.logger.info("Performing login...")
        login_manager = Login(self.page, self.config)
        if login_manager.perform_login():
            self.logger.info("Login successful.")
            return True
    

    def execute(self):
        self.start_browser()
        if self.login():
            self.logger.info("\n" + "="*60)
            self.logger.info("   WITS AUTOMATION: STARTING EXECUTION")
            self.logger.info("="*60 + "\n")
            
            query_names = self.config['query_name']
            if isinstance(query_names, str):
                query_names = [query_names]
            random.shuffle(query_names)
            for query_name in query_names:
                self.logger.info("\n" + "-"*50)
                self.logger.info(f"   [QUERY] Processing Query: {query_name}")
                self.logger.info("-"*50)
                
                try:
                    self.execute_single_query(query_name)
                    self.logger.info(f"   [SUCCESS] Query {query_name} completed.")
                except Exception as e:
                    self.logger.error(f"   [ERROR] Query {query_name} crashed: {e}")
            
            
            self.logger.info("\n" + "="*60)
            self.logger.info("   WITS AUTOMATION: COMPLETED")
            self.logger.info("="*60)
            
            
        else:
            self.logger.error("   [FATAL] Login failed. Aborting.")
            self.browser_manager.stop()
            self.logger.info("Browser closed.")
            

    def execute_single_query(self, query_name):
        import time
        query_start_time = time.time()
        
        self.logger.info(f"   -> Loading Progress status...")
        done_countries = self.load_done_countries(query_name)
        all_countries = set(self.config['iso3_to_country'].keys())
        countries_to_process = all_countries - done_countries
        countries_to_process = sorted(countries_to_process)
        #random.shuffle(countries_to_process)
        failed_countries = set()
        
        total = len(countries_to_process)
        self.logger.info(f"   -> Found {len(done_countries)} completed. Remaining: {total}")
        

        current_idx = 1
        success_count = 0
        stats_total_duration = 0
        stats_success_count = 0
        failed = False
        for country_code in countries_to_process:
            country_start_time = time.time()
            self.logger.info(f"\n   [{current_idx}/{total}] Processing Country: {country_code}")
            
            result = self.process_country(query_name, country_code)
            
            country_duration = time.time() - country_start_time
            
            if not result:
                self.write_failed_country(query_name, country_code)
                self.logger.warning(f"      [RESULT] Failed: {country_code} [TIME: {country_duration:.2f}s]")
                failed = True
                self.logger.info("Browser closed.")
                self.browser_manager.stop()
                self.start_browser()
                self.login()
            else:
                stats_total_duration += country_duration
                stats_success_count += 1
                avg_duration = stats_total_duration / stats_success_count
                
                self.write_done_country(query_name, country_code)
                self.logger.info(f"      [RESULT] Success: {country_code} [TIME: {country_duration:.2f}s | AVG: {avg_duration:.2f}s]")
                if failed:
                    success_count = 0
                    failed = False
                success_count += 1
                if success_count % 3 == 0:
                    self.logger.info(f"      [SUCCESS] {success_count} out of {total} countries processed successfully.") 
                    self.logger.info("      -> Waiting for 70 Seconds...")
                    self.page.wait_for_timeout(70*1000)
                else:
                    self.page.wait_for_timeout(10*1000)
                current_idx += 1
        
        query_duration = time.time() - query_start_time
        self.logger.info(f"   [QUERY FINISHED] Total Time: {query_duration:.2f}s")

        
    
    def process_country(self, query_name, country_code):
        # self.logger.info(f"Processing country {country_code} for query {query_name}...") 
        # (Redundant log removed in favor of loop log)
        try:
            navigation_advanced_query = navigate_to_advanced_query(self.page, self.logger)
            if not navigation_advanced_query:
                self.logger.error("      [ERROR] Nav to Advanced Query failed.")
                return False
            
            query_selection = select_existing_query(self.page, query_name, self.logger)
            if not query_selection:
                self.logger.error(f"      [ERROR] Selecting query '{query_name}' failed.")
                return False
            
            reporter_modification = modify_reporter(
                page=self.page,logger=self.logger, 
                country_code=country_code, query_name=query_name, 
                country_name=self.config['iso3_to_country'][country_code]
            )
            if not reporter_modification:
                self.logger.error("      [ERROR] Modify Reporter failed.")
                return False
            
            submit  = click_final_submit(self.page, self.logger)
            if not submit:
                self.logger.error("      [ERROR] Final Submit failed.")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"      [EXCEPTION] {e}")
            return False
    
    def write_done_country(self, query_name, country_code):
        filename = f"{query_name}.txt"
        filepath = self.done_dir / filename
        with open(filepath, 'a') as f:
            f.write(f"{country_code}\n")
        self.logger.info(f"Marked country {country_code} as done for query {query_name}.")
    def write_failed_country(self, query_name, country_code):
        filename = f"{query_name}.txt"
        filepath = self.failed_dir / filename
        with open(filepath, 'a') as f:
            f.write(f"{country_code}\n")
        self.logger.info(f"Marked country {country_code} as failed for query {query_name}.")  
        
    def load_done_countries(self, query_name):
        filename = f"{query_name}.txt"
        filepath = self.done_dir / filename
        if not filepath.exists():
            self.logger.info(f"No done countries for query {query_name}. Starting fresh.")
            return set()
        with open(filepath, 'r') as f:
            countries = {line.strip() for line in f if line.strip()}
        self.logger.info(f"Loaded {len(countries)} done countries for query {query_name}.")
        return countries