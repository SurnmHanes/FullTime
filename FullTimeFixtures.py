import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
import random
import re

options = uc.ChromeOptions()

options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage") 
options.add_argument("--window-size=1920,1080") # need full window size for some table columns to render properly
options.add_argument("--disable-gpu")

options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# All 4 fixtures URLs added to a list
urls = ["https://fulltime.thefa.com/fixtures.html?selectedSeason=634837132&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_578301195&selectedDateCode=all&selectedClub=&selectedTeam=998476034&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_578301195&previousSelectedClub=&itemsPerPage=25", "https://fulltime.thefa.com/fixtures.html?selectedSeason=503728397&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_714435981&selectedDateCode=all&selectedClub=&selectedTeam=732123121&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_714435981&previousSelectedClub=&itemsPerPage=25", "https://fulltime.thefa.com/fixtures.html?selectedSeason=503728397&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_250182602&selectedDateCode=all&selectedClub=&selectedTeam=130926545&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_250182602&previousSelectedClub=&itemsPerPage=25", "https://fulltime.thefa.com/fixtures.html?selectedSeason=342849661&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_843400620&selectedDateCode=all&selectedClub=&selectedTeam=373010773&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_843400620&previousSelectedClub=&itemsPerPage=25" ]

# Regex for UK postcodes (covers standard and GIR 0AA formats)
POSTCODE_RE = re.compile(
    r"\b([Gg][Ii][Rr] 0[Aa]{2})"
    r"|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|"
    r"(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?))))"
    r"\s?[0-9][A-Za-z]{2})\b"
)

def extract_address(raw):
    """Return (postcode_or_None, fallback_first_two_lines)."""
    if not raw:
        return None, None

    # remove excessive whitespace and newlines, then strip leading/trailing spaces
    cleaned = re.sub(r"\s+", " ", raw).strip()
    
    # Search for postcode using regex
    m = POSTCODE_RE.search(cleaned)
    postcode = m.group(0).upper() if m else None
    
    # Split on commas to get address lines
    lines = [p.strip() for p in cleaned.split(",") if p.strip()]
    
    # Use the first two lines as a fallback if postcode is not found
    fallback = ", ".join(lines[:2]) if lines else None
    
    return postcode, fallback


# A list to store the dataframe from each URL
all_dfs = []

# A list to store (fixture_url) for away games, plus which DataFrame/row they belong to
away_fixtures = []  # each entry: {"df_index": i, "url": url}

try:
    with uc.Chrome(options=options, use_subprocess=True, version_main=157) as driver:
           
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

        for index, url in enumerate(urls, start=1):
            print(f"Scraping page {index} of {len(urls)}...")
            driver.get(url)

            # Introduce a slightly dynamic variance in loading delay to mimic a human user
            time.sleep(random.uniform(4, 7))

            table_found = False
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, '//table'))
                )
            except Exception:
                # one retry in case the page was slow to load
                print(f"   No table yet on page {index}. Retrying once...")
                driver.get(url)
                time.sleep(random.uniform(5, 8))
                
                try:
                    WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, '//table'))
                    )
                except Exception:
                    print(f"Error: Page {index} is permanently blocked by CloudFlare firewall filters.")
                    continue

            # table exists - extract data
            try:
                table = driver.find_element(By.XPATH, '//table')
                row_elements = table.find_elements(By.XPATH, './/tbody/tr')

                page_rows = []
                page_fixture_urls = []  # aligns 1:1 with page_rows

                for row in row_elements:
                    cells = row.find_elements(By.XPATH, './/td')
                    row_data = [c.text.strip() for c in cells]
                    
                    if len(row_data) == 10:  # Ensure the row has the expected number of columns
                        # Capture the fixture detail URL (link is in the first cell)
                        fixture_url = None
                        try:
                            fixture_url = cells[0].find_element(By.TAG_NAME, 'a').get_attribute('href')
                        except Exception:
                            pass

                        page_rows.append(row_data)
                        page_fixture_urls.append(fixture_url)

                if not page_rows:
                    print(f"Page {index} has a table but no usable rows - likely no fixtures. Skipping.")
                    continue
                    
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

                # Placeholder columns for address info (filled later for MJPL away games only)
                temp_df['Postcode'] = None
                temp_df['Address'] = None

                # Get the fixture URLs for games (only for the first page, which is MJPL fixtures)
                if index == 1:
                    for local_idx, fixture_url in enumerate(page_fixture_urls):
                        if fixture_url:  # only record if a URL exists
                            away_fixtures.append({
                                "temp_df": temp_df,
                                "local_idx": local_idx,
                                "url": fixture_url
                            })

                all_dfs.append(temp_df)

            except Exception as e:
                print(f"Error scraping page {index}: {e}")

        # ------------------------------------------------------------------
        # Phase 2: visit each fixture page and pull the address block
        # ------------------------------------------------------------------
        print(f"\nNow fetching addresses for {len(away_fixtures)} fixtures...")

        # Cache by URL to avoid re-visiting the same fixture (e.g. if it appears twice)
        address_cache = {}

        for i, fixture in enumerate(away_fixtures, start=1):
            url = fixture["url"]
            if url in address_cache:
                postcode, address = address_cache[url]
            else:
                try:
                    driver.get(url)
                    time.sleep(random.uniform(2, 4))  # gentle pace

                    postcode, address = None, None
                    # Wait for the address block; fall through silently if missing
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, '//address/p'))
                        )
                        raw = driver.find_element(By.XPATH, '//address/p').text
                        postcode, address = extract_address(raw)
                    except Exception:
                        # No <address><p> on the page — try the whole address text as a fallback
                        try:
                            raw = driver.find_element(By.XPATH, '//address').text
                            postcode, address = extract_address(raw)
                        except Exception:
                            pass

                    address_cache[url] = (postcode, address)

                except Exception as e:
                    print(f"   [{i}/{len(away_fixtures)}] Error fetching {url}: {e}")
                    address_cache[url] = (None, None)

            if i % 10 == 0 or i == len(away_fixtures):
                print(f"   Fetched {i}/{len(away_fixtures)} addresses")

        # ------------------------------------------------------------------
        # Phase 3: stitch addresses back into the dataframes
        # ------------------------------------------------------------------
        for fixture in away_fixtures:
            postcode, address = address_cache.get(fixture["url"], (None, None))
            temp_df = fixture["temp_df"]
            local_idx = fixture["local_idx"]
            temp_df.at[local_idx, "Postcode"] = postcode
            temp_df.at[local_idx, "Address"] = address

except OSError as e:
    if "WinError 6" not in str(e):
        raise e

# append all dataframes together into one single sheet
if all_dfs:
    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df = final_df.drop(columns=['Blank1','VS','Blank2'])  # Drop unnecessary columns
    final_df['Date/Time'] = pd.to_datetime(final_df['Date/Time'], format="%d/%m/%y %H:%M", errors='coerce')
    final_df = final_df.sort_values(["Date/Time", "Player"], ignore_index=True)
    final_df.to_csv("fixtures.csv", index=False)
    print(f"\nSuccess! Saved {len(final_df)} total fixtures to fixtures.csv")

    # Quick summary of address coverage
    have_pc = final_df['Postcode'].notna().sum()
    have_addr = final_df['Address'].notna().sum()
    print(f"Address coverage: {have_pc} postcodes, {have_addr} full addresses out of {len(final_df)} rows")

else:
    print("No data was extracted")
