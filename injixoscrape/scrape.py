from os import path, mkdir
from sys import exit, argv
from shutil import rmtree
from selenium import webdriver
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime

# Ensure the existence of the config file
try:
    import injixoscrape.config as config
except Exception as ex:
    print('Config file is missing!')
    print(ex)
    exit(1)

try:
    email = config.username
    password = config.password
    dashboard_file_path = config.dashboard_file
    schedule_file_path = config.schedule_file
except Exception as e:
    print('Formatting error with config file. Is something missing?')
    print(e)
    exit(1)

login_url = "https://www.injixo.com/login"
dashboard_url = 'https://www.injixo.com/me/dashboard'
schedule_url = 'https://www.injixo.com/me/schedule/revise?calendar%5Bview_mode%5D='

date_url = '%Y-%m-%d'
date_display = '%d %B, %Y'

agent_username = config.username[:len(config.username) - 12]

db_client = MongoClient(config.mongo_db_url)
db = db_client.get_database()

db_events = db.get_collection('events')


def main(argv):
    # If the 'new' argument is used when calling the script, delete all downloaded HTML
    if 'new' in argv and path.exists('html'):
        rmtree('html')

    # Get the parsed HTML code
    loginAndScrape()
    dashboard_soup = makeSoup(dashboard_file_path)

    # Cleanup Database
    cleanDatabase()

    # Pull data from HTML for upcoming events
    try:
        processUpcomingEvents(dashboard_soup)
    except Exception as e:
        print('Error reading schedule. Are you sure your login credentials are correct?')
        print(e)
        exit(1)


# Function to handle getting the raw HTML from Injixo
def loginAndScrape():
    # Create the html subdirectory if it doesn't already exist
    if not path.exists('html'):
        try:
            mkdir('html')
        except Exception as e:
            print('Unable to create HTML directory!')
            print(e)
            exit(1)

    # if the HTML code for the dashboard has not already been downloaded, log in and download it
    if not path.exists(dashboard_file_path):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        driver = webdriver.Chrome(chrome_options=options)
        driver.get(login_url)
        email_field = driver.find_element_by_id('email')
        password_field = driver.find_element_by_id('password')
        login_button = driver.find_element_by_class_name('btn-block')

        email_field.send_keys(email)
        password_field.send_keys(password)
        login_button.click()

        # Dashboard HTML
        scrapeSave(driver, dashboard_url, dashboard_file_path)

        today = datetime.datetime.today()
        delta = datetime.timedelta(days=1)
        curr_date = today
        end_date = today + datetime.timedelta(days=6)
        while curr_date <= end_date:
            date_str = curr_date.strftime(date_url)
            schedule_url_new = schedule_url + date_str
            schedule_file_path_new = schedule_file_path + date_str + '.html'
            print(date_str)
            scrapeSave(driver, schedule_url_new, schedule_file_path_new)
            soup = makeSoup(schedule_file_path_new)
            processSevenDaySchedule(soup)
            curr_date += delta
    # end if

def scrapeSave(driver, url, path):
    driver.get(url)
    html = driver.page_source
    file = open(path, 'w+', encoding='utf-8')
    file.write(html)
    file.close()

def makeSoup(file_path):
    # Read the given file and store it in a variable
    file = open(file_path, 'r')
    html = file.read()
    file.close()

    # Use BeautifulSoup to parse the HTML code
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def processUpcomingEvents(page_soup):
    # Finds and prints the main event from the upcoming events section
    main_event = page_soup.find('div', {'id': 'upcoming-list-next'})
    main_event_title = main_event.find('div', {'class': 'top-event'}).text
    main_event_meta = main_event.find('div', {'class': 'meta'}).text

    # Fix spacing
    if main_event_title == 'TeamBrief':
        main_event_title = 'Team Brief'

    # Separate date and time into different variables
    main_event_meta = main_event_meta.replace('\n', ' ').replace('\r', '')
    main_event_date = main_event_meta[:13]
    main_event_time = main_event_meta[15:]

    # Print results to console
    print(main_event_date + ' ' + main_event_time + ' ' + main_event_title + ' [Main Event]')

    # Collects data and inserts into database
    this_event = {'name': main_event_title, 'date': main_event_date, 'time': main_event_time, 'isMain': True,
                  'agent': agent_username}
    db_events.insert_one(this_event)

    # Finds and stores a list of upcoming events and their information in variables
    upcoming_events_rest = page_soup.find('div', {'id': 'upcoming-list-rest'})
    upcoming_events_titles = upcoming_events_rest.findAll('span', {'class': 'agenda_event_title'})
    upcoming_events_dates = upcoming_events_rest.findAll('div', {'class': 'event-date'})
    upcoming_events_times = upcoming_events_rest.findAll('div', {'class': 'event-time'})

    # Loops through list of upcoming events and extracts and formats the information removing unnecessary spaces and breaks
    for i in range(len(upcoming_events_titles)):
        # Find and format event title
        title = upcoming_events_titles[i].text
        title = title.replace('\n', ' ').replace('\r', '')
        title = list(title)
        title[0] = ''
        title[len(title) - 1] = ''
        title = ''.join(title)

        # Fix spacing
        if title == 'TeamBrief':
            title = 'Team Brief'

        # Find and format event date
        date = upcoming_events_dates[i].text
        date = list(date)
        date[0] = ''
        date = ''.join(date)

        # Find event time
        time = upcoming_events_times[i].text

        # Print result to console
        print(date + ' ' + time + ' ' + title)

        # Collects data and inserts into database
        this_event = {'name': title, 'date': date, 'time': time, 'isMain': False, 'agent': agent_username}
        db_events.insert_one(this_event)


def processSevenDaySchedule(page_soup):
    #schedule = page_soup.find('div', {'id': 'calendar'})
    events = page_soup.findAll('div', {'class': 'fc-content'})

    for event in events:
        event_time = event.find('div', {'class': 'fc-time'}).text
        event_time_start = event_time[:5]
        event_time_end = event_time[8:]

        event_name = event.find('div', {'class': 'fc-title'}).text
        print('EVENT: ' + event_time_start + ' - ' + event_time_end + ' ' + event_name)

    # today = datetime.datetime.today().strftime(date_display)
    # today = list(today)
    # today = ''.join(today)
    # print(today)
    #current_day_tag = schedule.find('span', text=today)
    #print(current_day_tag.text)
    # print(events)


def cleanDatabase():
    db_events.drop()


# Run main function
if __name__ == "__main__":
    main(argv[1:])
