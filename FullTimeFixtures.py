import pandas as pd
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 

options = uc.ChromeOptions()

options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage") 
options.add_argument("--window-size=1920,1080")

options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-gpu")
options.add_argument("--incognito")

options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# All 4 fixtures URLs added to a list
urls = ["https://fulltime.thefa.com/fixtures.html?selectedSeason=634837132&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_578301195&selectedDateCode=all&selectedClub=&selectedTeam=998476034&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_578301195&previousSelectedClub=&itemsPerPage=25", "https://fulltime.thefa.com/fixtures.html?selectedSeason=503728397&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_714435981&selectedDateCode=all&selectedClub=&selectedTeam=732123121&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_714435981&previousSelectedClub=&itemsPerPage=25", "https://fulltime.thefa.com/fixtures.html?selectedSeason=503728397&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_250182602&selectedDateCode=all&selectedClub=&selectedTeam=130926545&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_250182602&previousSelectedClub=&itemsPerPage=25", "https://fulltime.thefa.com/fixtures.html?selectedSeason=342849661&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_843400620&selectedDateCode=all&selectedClub=&selectedTeam=373010773&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_843400620&previousSelectedClub=&itemsPerPage=25" ]

# A list to store the dataframe from each URL
all_dfs = []

try:
    with uc.Chrome(options=options, use_subprocess=True) as driver:
           
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

        for index, url in enumerate(urls, start=1):
            print(f"Scraping page {index} of {len(urls)}...")
            driver.get(url)

            # Introduce a slightly dynamic variance in loading delay to mimic a human user
            time.sleep(4)


            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//table'))
                )

                table = driver.find_element(By.XPATH, '//table')
                row_elements = table.find_elements(By.XPATH, './/tbody/tr')

                page_rows = []
                for row in row_elements:
                    cells = row.find_elements(By.XPATH, './/td')
                    row_data = [c.text.strip() for c in cells]
                    
                    if len(row_data) == 10:  # Ensure the row has the expected number of columns
                        page_rows.append(row_data)

                # turn this specific page's rows into a temporary dataframe
                columns_list = ['Type', "Date/Time", "Home Team", "Blank1", "VS", "Blank2", "Away Team", "Venue", "Competition", "Status"]
                temp_df = pd.DataFrame(page_rows, columns=columns_list)

                if index in [1, 3]:
                    temp_df['Player'] = 'Max'
                elif index == 2:
                    temp_df['Player'] = 'Leo'
                elif index == 4:
                    temp_df['Player'] = 'Nyla'

                # Track which URL/Source it came from (helpful for debugging)
                temp_df['Source_Page'] = f"Page {index}"

                all_dfs.append(temp_df)

            except Exception as e:
                print(f"Error scraping page {index}: {e}")

except OSError as e:
    if "WinError 6" not in str(e):
        raise e

# append all dataframes together into one single sheet
if all_dfs:
    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df = final_df.drop(columns=['Blank1','VS','Blank2'])  # Drop unnecessary columns
    final_df.to_csv("fixtures.csv", index=False)
    print(f"Success! Saved {len(final_df)} total fixtures to fixtures.csv")

else:
    print("No data was extracted")
