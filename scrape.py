from os import remove, path
from sys import exit, platform
from selenium import webdriver
from bs4 import BeautifulSoup as soup

# Ensure the existance of the config file
try:
    import config
except:
    print('Config file is missing!')
    exit(1)

try:
    email = config.username
    password = config.password
    html_file_path = config.html_file
    output_file_path = config.output_file
except:
    print('Formatting error with config file. Is something missing?')
    exit(1)

# Get the correct webdriver for the OS
if platform == 'win32':
    webdriver_loc = 'phantomjs.exe'
elif platform == 'linux' or 'linux2' or 'darwin':
    webdriver_loc = 'phantomjs'

login_url = "https://www.injixo.com/login"
internal_url = 'https://www.injixo.com/me/dashboard'


def main():
    # Get the parsed HTML code
    page_soup = loginAndScrape()

    # Pull data from HTML for upcoming events
    try:
        processUpcomingEvents(page_soup)
    except Exception as e:
        print('Error reading schedule. Are you sure your login credentials are correct?')
        print(e)
        exit(1)

# Function to handle getting the raw HTML from Injxo
def loginAndScrape():
    # if the HTML code for the dashbaord has not already been downloaded, log in and download it
    if not path.exists(html_file_path):
        driver = webdriver.PhantomJS(webdriver_loc)
        driver.get(login_url)
        email_field = driver.find_element_by_id('email')
        password_field = driver.find_element_by_id('password')
        login_button = driver.find_element_by_class_name('btn-block')

        email_field.send_keys(email)
        password_field.send_keys(password)
        login_button.click()

        driver.get(internal_url)
        html = driver.page_source
        html_file = open(html_file_path, 'w+', encoding='utf-8')
        html_file.write(html)
        html_file.close()
    # end if

    # Read the local dashboard.html file and store it in a variable
    html_file = open(html_file_path, 'r')
    html = html_file.read()
    html_file.close()

    # Use BeautifulSoup to parse the HTML code
    page_soup = soup(html, 'html.parser')
    return page_soup

def processUpcomingEvents(page_soup):
    # Finds and prints the main event from the upcoming events section
    main_event = page_soup.find('div', {'id': 'upcoming-list-next'})
    main_event_title = main_event.find('div', {'class': 'top-event'}).text
    main_event_meta = main_event.find('div', {'class': 'meta'}).text
    
    # Fix grammar :)
    if main_event_title == 'TeamBrief':
        main_event_title = 'Team Brief'

    # Aeparate date and time into different variables using
    main_event_meta = main_event_meta.replace('\n', ' ').replace('\r', '')
    main_event_date = main_event_meta[:13]
    main_event_time = main_event_meta[15:]

    print(main_event_date + ' ' + main_event_time + ' ' + main_event_title + ' [Main Event]')

    # Finds and stores a list of upconming events and their information in variables
    upcoming_events_rest = page_soup.find('div', {'id': 'upcoming-list-rest'})
    upcoming_events_titles = upcoming_events_rest.findAll('span', {'class': 'agenda_event_title'})
    upcoming_events_dates = upcoming_events_rest.findAll('div', {'class': 'event-date'})
    upcoming_events_times = upcoming_events_rest.findAll('div', {'class': 'event-time'})

    # Loops through list of upcoming events and extracts and formats the infomration removing unnecessary spaces and breaks
    for i in range(len(upcoming_events_titles)):
        title = upcoming_events_titles[i].text
        title = title.replace('\n', ' ').replace('\r', '')
        title = list(title)
        title[0] = ''
        title[len(title) - 1] = ''
        title = ''.join(title)

        date = upcoming_events_dates[i].text
        date = list(date)
        date[0] = ''
        date = ''.join(date)

        time = upcoming_events_times[i].text

        print(date + ' ' + time + ' ' + title)

        # Print formatted output to csv file
        if(i == 0):
            remove(output_file_path)
        csv = open(output_file_path, 'a+')
        csv.write(str(i + 1) + '. ' + title + ', ' + date + ', ' + time + '\n')
        csv.close()

# Run main function
if __name__== "__main__":
    main()
