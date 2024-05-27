import os
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import pytesseract
from ollama import generate
import streamlit as st


service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=service, options=options)

def scroll_page():
    last_height = driver.execute_script('return arguments[0].scrollHeight', 
                                        driver.find_element(By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf'))
    
    while True:
        scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf')
        driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
        
        time.sleep(2)  # Adjust the sleep time if needed
        
        new_height = driver.execute_script('return arguments[0].scrollHeight', scrollable_div)
        
        if new_height == last_height:
            break
        last_height = new_height

    # Scroll back to the top
    driver.execute_script('arguments[0].scrollTop = 0', scrollable_div)

def search_google_maps(merchant_name):

    try:
        # Open Google Maps
        driver.get("https://www.google.com/maps")

        # Maximize the browser window
        driver.maximize_window()
        time.sleep(5)

        # Wait for the search box to be present
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )

        # Enter the merchant name in the search box and submit
        search_box.send_keys(merchant_name)
        search_box.send_keys(Keys.RETURN)

        # Wait for the search results to load
        time.sleep(5)

        # Extract the merchant name from the page
        merchant_name_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf.lfPIob"))
        )
        merchant_name_text = merchant_name_element.text

        # Create a directory for saving screenshots based on the merchant name
        directory_name = merchant_name_text.replace(' ', '_')
        if not os.path.exists(directory_name):
            os.makedirs(directory_name)

        # Locate the image button and click it
        image_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.aoRNLd"))
        )
        image_button.click()

        try:
            # Wait for the element with specific class names and text content to be present
            menu_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'Gpq6kf') and contains(@class, 'fontTitleSmall') and normalize-space(text())='Menu']"))
            )

            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView();", menu_button)

            # Click the menu button using JavaScript
            driver.execute_script("arguments[0].click();", menu_button)

        except Exception as e:
            print("Menu button not found. Exiting...")
            driver.quit()
            exit()
        
        # scroll to load menu photos
        scroll_page()

        # wait for other menu photos to load (ajax)
        time.sleep(4)


        # Find all images in the "Menu" tab
        images = driver.find_elements(By.CSS_SELECTOR, "a[data-photo-index]")

        for index, image in enumerate(images):
            try:
                # Click the image to view it
                image.click()
                
                # Wait for the image to load
                time.sleep(5)

                # Get the date element
                date_element = driver.find_element(By.CSS_SELECTOR, 'div.mqX5ad')
                date_text = date_element.text
                
                # Extract the year from the date text
                year = int(date_text.split()[-1])
                
                # Check if the year is in the specified range
                if year in {2020, 2021, 2022, 2023, 2024}:
                    # Take a full screenshot and save it to a file
                    full_screenshot_path = f'{directory_name}/full_screenshot_{index}.png'
                    driver.save_screenshot(full_screenshot_path)

                    # Define the coordinates for the partial screenshot (adjust as necessary)
                    left = 1000
                    top = 200
                    right = 3500
                    bottom = 1700

                    # Open the full screenshot image
                    full_screenshot = Image.open(full_screenshot_path)

                    # Crop the image
                    partial_screenshot = full_screenshot.crop((left, top, right, bottom))

                    # Save the partial screenshot
                    partial_screenshot_path = f'{directory_name}/partial_screenshot_{index}.png'
                    partial_screenshot.save(partial_screenshot_path)
                    
                    # Wait before the next iteration
                    time.sleep(2)
                    continue

            except Exception as e:
                print(f"Error processing image {index}: {e}")
                continue

    finally:
        driver.quit()

    ocr_string = ""

    for index in range(len(images)):
        partial_screenshot_path = f'{directory_name}/partial_screenshot_{index}.png'
        if os.path.exists(partial_screenshot_path):
            result = pytesseract.image_to_string(Image.open(partial_screenshot_path))
            
            # Check if result is not None before iterating
            if result is not None and len(result) > 0:
                ocr_string += result + " "
            else:
                print(f"OCR failed for image {index} at path {partial_screenshot_path}")
        else:
            print(f"Image file not found at path {partial_screenshot_path}")
            
    return ocr_string
    
# Define the function to process text and generate a summary or structured list
def process_text(input_text):
    print(f"\nProcessing text:\n{input_text}\n")

    full_response = ''
    # Generate a summary or structured list of the text
    for response in generate(model='llama3:8b',
                            prompt='Buatkan list daftar menu yang bagus tanpa harga dari teks berikut:\n\n' + input_text + '\n\nDaftar Menu:',
                            stream=True):
        # Print the response to the console and add it to the full response
        print(response['response'], end='', flush=True)
        full_response += response['response']

    # Format the generated text as a paragraph or list
    structured_text = '\n'.join(full_response.splitlines())  # Join lines with newlines

    return structured_text

# Function to convert structured menu text to a dataframe
def menu_to_dataframe(structured_menu):
    # Remove numbers and trim whitespace
    menu_items = [re.sub(r'^\d+\.\s*', '', line).strip() for line in structured_menu.split("\n") if line.strip()]
    menu_df = pd.DataFrame(menu_items, columns=["Menu Item"])
    
    # Remove the first and last row
    if not menu_df.empty:
        menu_df = menu_df.iloc[1:-1].reset_index(drop=True)
    
    return menu_df

st.title('Google Maps Menu Scraper')

merchant_name = st.text_input('Enter the merchant name:')

if st.button('Get Menu'):
    with st.spinner('Fetching menu...'):
        start_time = time.time()
        
        ocr_text = search_google_maps(merchant_name)
        st.text("Combined OCR Text:")
        st.write(ocr_text)
        
        structured_menu = process_text(ocr_text)
        st.text("Generated Structured Menu:")
        st.write(structured_menu)

        menu_df = menu_to_dataframe(structured_menu)
        st.text("Menu DataFrame:")
        st.write(menu_df)

        end_time = time.time()
        total_time = end_time - start_time
        st.text(f"Total Execution Time: {total_time:.2f} seconds")
