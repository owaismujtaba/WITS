class Login:
    def __init__(self, page, config):
        self.page = page
        self.config = config
        
    def setup_creds(self):
        email = self.config['credentials']['email']
        password = self.config['credentials']['password']
        return email, password
    
    def perform_login(self):
        email, password = self.setup_creds()
        self.page.goto(self.config['urls']['login'], timeout=30000)
        self.page.fill('#UserNameTextBox', email)
        self.page.fill('#UserPassTextBox', password)
        self.page.click('#btnSubmit')
        self.page.wait_for_load_state('domcontentloaded')
        try:
            self.page.wait_for_selector('text=Logout', timeout=10000)
            print("Login successful.")    
            return True  
        except:
            print("Login failed or took too long.")
            return False
        