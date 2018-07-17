from selenium import webdriver
from sys import exit, platform
from bs4 import BeautifulSoup as soup
import os.path
from os import remove
from time import sleep
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

if platform == 'win32':
    webdriver_loc = 'phantomjs.exe'
elif platform == 'linux' or 'linux2' or 'darwin':
    webdriver_loc = 'phantomjs'

login_url = "https://www.injixo.com/login"
internal_url = 'https://www.injixo.com/me/dashboard'


def main():
    

    page_soup = loginAndScrape()

    try:
        main_event = page_soup.find('div', {'id': 'upcoming-list-next'}).text
        main_event.replace('\n', ' ').replace('\r', '')
        print(main_event)

        upcoming_events_rest = page_soup.find('div', {'id': 'upcoming-list-rest'})
        upcoming_events_titles = upcoming_events_rest.findAll('span', {'class': 'agenda_event_title'})
        upcoming_events_dates = upcoming_events_rest.findAll('div', {'class': 'event-date'})
        upcoming_events_times = upcoming_events_rest.findAll('div', {'class': 'event-time'})

        for i in range(len(upcoming_events_titles)):
            title = upcoming_events_titles[i].text
            title = title.replace('\n', ' ').replace('\r', '')
            title = list(title)
            title[0] = ''
            title[len(title) - 1] = ''
            title1 = ''.join(title)

            date = upcoming_events_dates[i].text
            date = list(date)
            date[0] = ''
            date1 = ''.join(date)

            time = upcoming_events_times[i].text

            print(time + ' ' + date1 + ' ' + title1)

            if(i == 0):
                os.remove(output_file_path)
            csv = open(output_file_path, 'a+')
            csv.write(str(i + 1) + '. ' + title1 + ', ' + date1 + ', ' + time + '\n')
            csv.close()
    except:
        print('Error reading schedule. Are you sure your login credentials are correct?')
        exit(1)

def loginAndScrape():
    if not os.path.exists(html_file_path):
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

    html_file = open(html_file_path, 'r')
    html = html_file.read()
    html_file.close()

    page_soup = soup(html, 'html.parser')

    return page_soup

if __name__== "__main__":
    main()
