from src.bots.execute_query import ExecuteQueryBot
from src.utils.config import load_config
from src.bots.download_query import DownloadQueryBot

import pdb

def main():
    # Load configuration
    config = load_config('config.yaml')
    
    if config['workflow'].get('execute_query', False):
        bot = ExecuteQueryBot(config)
        bot.execute()

    if config['workflow'].get('download_query', False):
        bot = DownloadQueryBot(config)
        bot.execute()
if __name__=='__main__':
    main()