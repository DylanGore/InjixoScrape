# InjixoScrape

A python script designed to login and scrape and store shift and event data from Injixo.

## Requirements

- [ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/downloads)
- [Python 3](https://www.python.org/downloads/)
  - [Selenium](https://www.seleniumhq.org/)
  - [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
  - [PyMongo](https://api.mongodb.com/python/current/)
  - [dnspython](https://github.com/rthalley/dnspython)

## Installation

1. Download and add ```chromedriver``` to path.
2. Install Python 3 if it's not already installed.
3. Install python dependencies ```pip install -r requirments.txt```.
4. Rename the file ```config.sample.py``` to ```config.py``` and update the variables as needed

## Usage

To run:

```python -m injixoscrape```

Command line arguments:

- new - forces the HTML code to be re-downloaded
