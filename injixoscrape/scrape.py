from os import path, mkdir
from sys import exit, argv
from shutil import rmtree
from selenium import webdriver
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime, timedelta

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
schedule_url = 'https://www.injixo.com/me/schedule/revise?calendar%5Bdate%5D='

date_url = '%Y-%m-%d'
date_display = '%d %B, %Y'

agent_username = config.username[:len(config.username) - 12]

db_client = MongoClient(config.mongo_db_url)
db = db_client.get_database()

db_events = db.get_collection('events')
db_schedule = db.get_collection('schedule')

soup_dict = {}


def main(argv):
    # Print agent username
    print('\nAgent: ' + agent_username)
    # If the 'new' argument is used when calling the script, delete all downloaded HTML
    if 'new' in argv:
        if path.exists('html'):
            rmtree('html')
        cleanDatabase()
        # Pull data from HTML for upcoming events
        try:
            loginAndScrape()
            dashboard_soup = makeSoup(dashboard_file_path)
            processUpcomingEvents(dashboard_soup)
            for item in soup_dict:
                processSevenDaySchedule(item, soup_dict[item])
        except Exception as e:
            print('Error reading schedule. Are you sure your login credentials are correct?')
            print(e)
            exit(1)

    displayUpcomingEvents()
    displaySchedule()


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
        options.add_argument('log-level=3')
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

        today = datetime.today()
        delta = timedelta(days=1)
        curr_date = today
        end_date = today + timedelta(days=6)
        while curr_date <= end_date:
            date_str = curr_date.strftime(date_url)
            schedule_url_new = schedule_url + date_str
            schedule_file_path_new = schedule_file_path + date_str + '.html'
            print('Saving schedule for: ' + date_str)
            scrapeSave(driver, schedule_url_new, schedule_file_path_new)
            soup = makeCalendarSoup(schedule_file_path_new)
            soup_dict[date_str] = soup
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


def makeCalendarSoup(file_path):
    # Read the given file and store it in a variable
    file = open(file_path, 'r')
    html = file.read()
    file.close()

    # Use BeautifulSoup to parse the HTML code
    soup = BeautifulSoup(html, 'html.parser')
    cal_soup = soup.find('div', {'id': 'calendar'})
    return cal_soup


def displayUpcomingEvents():
    print('\nUpcoming Events')
    print('Total Events: ' + str(db_events.count()) + '\n')
    for event in db_events.find():
        if event['isMain'] == True:
            print(event['date'] + ' ' + event['time'] + ', ' + event['name'] + ' [Main Event]')
        else:
            print(event['date'] + ' ' + event['time'] + ', ' + event['name'])


def displaySchedule():
    print('\nSchedule:')
    print('Days: ' + str(db_schedule.count()))
    for day in db_schedule.find():
        print('\n' + day['date'])
        events = day['events']
        if len(events) != 0:
            for event in events:
                print(' ' + event['title'] + ' ' +  event['start_time'] + ' - ' + event['end_time'] + ' (' + event['type'] + ')')
        else:
            print(' No events')


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
    main_event_time = main_event_meta[16:]

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
        # Remove leading blank space if one exists
        if date[0] == ' ':
            date[0] = ''
        date = ''.join(date)

        # Find event time
        if i <= len(upcoming_events_times) - 1:
            time = upcoming_events_times[i].text
        else:
            # Fixes issues caused if no time is associated (ie. vacation days)
            time = 'N/A'

        # Collects data and inserts into database
        this_event = {'name': title, 'date': date, 'time': time, 'isMain': False, 'agent': agent_username}
        db_events.insert_one(this_event)


def processSevenDaySchedule(date, page_soup):
    this_events = []
    events = page_soup.findAll('div', {'class': 'fc-content'})

    for event in events:
        event_time = event.find('div', {'class': 'fc-time'}).text
        event_time_start = event_time[:5]
        event_time_end = event_time[8:]

        event_name = event.find('div', {'class': 'fc-title'}).text

        this_event = {'title': event_name, 'start_time': event_time_start, 'end_time': event_time_end,
                      'length': getEventLength(event_time_start, event_time_end),
                      'type': getEventType(event_name)}
        this_events.append(this_event)

    this_schedule = {
        'agent': agent_username,
        'date': date,
        'events': this_events
    }
    db_schedule.insert_one(this_schedule)


def cleanDatabase():
    db_events.drop()
    db_schedule.drop()


def getEventType(event_name):
    return {
        'Technical': 'Work',
        'Break': 'Break',
        'Lunch': 'Break',
        'Training': 'Time Off',
        'Training Mandatory': 'Time Off',
        'Digital Academy': 'Time Off',
        'TeamBrief': 'Time Off',
        'One to One meeting': 'Time Off',
        'Meeting': 'Time Off',
        'QBU': 'Time Off',
        'Vacation': 'Holiday'
    }.get(event_name, 'Time Off')


def getEventLength(start, end):
    time_str = '%H:%M'
    delta = datetime.strptime(end, time_str) - datetime.strptime(start, time_str)
    return str(delta)


# Run main function
if __name__ == "__main__":
    main(argv[1:])
