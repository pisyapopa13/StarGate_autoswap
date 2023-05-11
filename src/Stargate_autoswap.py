import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.expected_conditions import invisibility_of_element_located
import time
import random
import threading
from queue import Queue
from selenium.common.exceptions import NoSuchElementException



chrome_driver_path = "C:\\you\\personal\\path\\to\\chromedriver-win-x64.exe"
CUSTOM_FACTOR = 0.993
additional_delay = 69
desired_trx = 10
metamask_url = "chrome-extension://cfkgdnlcieooajdnoehjhgbmpbiacopjflbjpnkm/home.html#"
allowed_networks_user = {"Optimism", "Arbitrum", "Avalanche", "Polygon", "Fantom", "BNB Chain"}


columns = ["Profile ID", "Optimism", "Arbitrum", "Avalanche", "Polygon", "Fantom", "Totall TRX", "Totall Volume"]
start_idx = int(input("Enter the starting index of the profile range: "))
end_idx = int(input("Enter the ending index of the profile range: "))
max_simultaneous_profiles = int(input("Enter the max simultaneous worker: "))
Stargate = "https://stargate.finance/transfer"
data = pd.read_excel("data\\profiles_data.xlsx", dtype={"Profile ID": str})
with open("config\\profile_ids.txt", "r") as file:
    profile_ids = [line.strip() for line in file.readlines()]
with open("config\\passwords.txt", "r") as file:
    passwords = [line.strip() for line in file.readlines()]

networks = [
    ("//*[contains(text(), 'Optimism')]", "Optimism"),
    ("//*[contains(text(), 'Arbitrum One')]", "Arbitrum"),
    ("//*[contains(text(), 'Avalanche Network C-Chain')]", "Avalanche"),
    ("//*[contains(text(), 'Polygon Mainnet')]", "Polygon"),
    ("//*[contains(text(), 'Fantom Opera')]", "Fantom"),
    ("//*[contains(text(), 'BNB Smart Chain (previously Binance Smart Chain Mainnet)')", "BNB Chain"),
]
def click_random_button(driver, selected_network_name, allowed_networks=None):
    if allowed_networks is None:
        allowed_networks = allowed_networks_user

    buttons = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//button"))
    )

    valid_buttons = []

    for button in buttons:
        try:
            label = button.find_element(By.XPATH, ".//div[contains(@class, 'label')]")
            if label.text in allowed_networks and selected_network_name not in label.text:
                valid_buttons.append(button)
        except NoSuchElementException:
            continue

    if valid_buttons:
        random.choice(valid_buttons).click()
def confirm_transaction(driver):
    metamask_window_handle = None

    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if 'MetaMask Notification' in driver.title:
            metamask_window_handle = handle
            break

    if metamask_window_handle:
        find_confirm_button_js = '''
        function findConfirmButton() {
          return document.querySelector('[data-testid="page-container-footer-next"]');
        }
        return findConfirmButton();
        '''
        confirm_button = driver.execute_script(find_confirm_button_js)

        if confirm_button:
            driver.execute_script("arguments[0].scrollIntoView(true);", confirm_button)
            for i in range(5):
                if metamask_window_handle not in driver.window_handles:
                    print("MetaMask Notification window closed as expected")
                    return
                driver.execute_script("arguments[0].click();", confirm_button)
                print(f"Click attempt {i + 1}")
                time.sleep(3)
            print("Transaction is confirmed")
        else:
            print("Confirm button not found")
    else:
        print("MetaMask Notification window not found")
def confirm_connection(driver):
    metamask_window_handle = None
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if 'MetaMask Notification' in driver.title:
            metamask_window_handle = handle
            break
    if metamask_window_handle:
        Confirm_conection_xpath = '/html/body/div[1]/div/div[2]/div/div[3]/div[2]/button[2]'
        click_if_exists(driver, Confirm_conection_xpath)
        Confirm_conection2_xpath = '/html/body/div[1]/div/div[2]/div/div[2]/div[2]/div[2]/footer/button[2]'
        click_if_exists(driver, Confirm_conection2_xpath)
        print("Metamask is connected")
    else:
        print("MetaMask already connected")

def click_if_exists(driver, locator, by=By.XPATH):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((by, locator))
            )
            WebDriverWait(driver, 10).until(
                invisibility_of_element_located((By.CSS_SELECTOR, ".loading-overlay"))
            )

            element.click()
            return True
        except TimeoutException:
            return False
        except StaleElementReferenceException:
            attempts += 1
            time.sleep(3)
    return False
def input_text_if_exists(driver, locator, text, by=By.XPATH, timeout=20):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, locator))
            )
            element.send_keys(text)
            return True
        except TimeoutException:
            return False
        except StaleElementReferenceException:
            attempts += 1
            time.sleep(3)
    return False
def get_value_if_exists(driver, xpath):
    try:
        element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
        return float(element.text) if element.text else 0.0
    except TimeoutException:
        return None
def instruction(idx, profile_id):
        print(f"Processing profile {idx}: {profile_id}")
        req_url = f'http://localhost:3001/v1.0/browser_profiles/{profile_id}/start?automation=1'
        response = requests.get(req_url)
        response_json = response.json()
        print(response_json)
        port = str(response_json['automation']['port'])
        options = webdriver.ChromeOptions()
        options.debugger_address = f'127.0.0.1:{port}'
        service = Service(executable_path=chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        initial_window_handle = driver.current_window_handle

        driver.get(metamask_url)
        for tab in driver.window_handles:
            if tab != initial_window_handle:
                driver.switch_to.window(tab)
                driver.close()
        driver.switch_to.window(initial_window_handle)

        password_input = '//*[@id="password"]'
        input_text_if_exists(driver, password_input, passwords[idx - 1])
        connection_confirm = '//*[@id="app-content"]/div/div[3]/div/div/button'
        click_if_exists(driver, connection_confirm)
        total_trx = data.loc[data["Profile ID"] == profile_id, "Totall TRX"].item()
        success = False
        while not success or total_trx < desired_trx:
            success = False
            driver.get(metamask_url)
            assets = '/html/body/div[1]/div/div[3]/div/div/div/div[3]/ul/li[1]/button'
            click_if_exists(driver, assets)
            row_data = {"Profile ID": profile_id}
            for network_xpath, network_name in networks:
                selector_1 = '/html/body/div[1]/div/div[1]/div/div[2]/div/div'
                click_if_exists(driver, selector_1)
                time.sleep(random.uniform(2.5, 3))
                click_if_exists(driver, network_xpath)
                time.sleep(random.uniform(2.5, 3))
                assets = '/html/body/div[1]/div/div[3]/div/div/div/div[3]/ul/li[1]/button'
                click_if_exists(driver, assets)
                value_xpath = "/html/body/div[1]/div/div[3]/div/div/div/div[3]/div[2]/div[2]/div"
                click_if_exists(driver, value_xpath)
                number_xpath = "/html/body/div[1]/div/div[3]/div/div[2]/div[1]/div/div[1]/span[2]"
                value = get_value_if_exists(driver, number_xpath)
                row_data[network_name] = value
                data.loc[data["Profile ID"] == profile_id, network_name] = value
                print(f"{network_name}: {value}")
            data.to_excel("data\\profiles_data.xlsx", index=False)

            network_values = {}
            for network_name in columns[1:]:
                network_values[network_name] = data.loc[data["Profile ID"] == profile_id, network_name].item()
            max_value = -69
            selected_network_xpath = None
            selected_network_name = None
            for network_xpath, network_name in networks:
                value = network_values[network_name]
                if value > max_value:
                    max_value = value
                    selected_network_xpath = network_xpath
                    selected_network_name = network_name
            print(f"Selected network: {selected_network_name}, Value: {max_value}")

            time.sleep(random.uniform(2, 3))
            selector = '/html/body/div[1]/div/div[1]/div/div[2]/div/div'
            click_if_exists(driver, selector)
            time.sleep(random.uniform(2, 3))
            click_if_exists(driver, selected_network_xpath)
            time.sleep(random.uniform(2, 3))

            driver.get(Stargate)
            Connect_Wallet = '/html/body/div/header[1]/div/div[3]/button[2]'
            click_if_exists(driver, Connect_Wallet)
            Metamask_confirm = '/html/body/div[2]/div[3]/div/div[2]/div/li[1]'
            click_if_exists(driver, Metamask_confirm)
            time.sleep(10)
            confirm_connection(driver)

            driver.refresh()
            time.sleep(20)
            USDC_selection_open = '/html/body/div/main/div[2]/section/div[1]/div[2]/div[1]/div[1]/div/div[1]/div[1]/div'
            click_if_exists(driver, USDC_selection_open)
            time.sleep(random.uniform(2, 3))
            USDC_selection = f"//button[contains(., 'USDC') and contains(., '{selected_network_name}')]"
            click_if_exists(driver, USDC_selection)
            time.sleep(random.uniform(2, 3))
            input_network2 = '/html/body/div/main/div[2]/section/div[1]/div[2]/div[1]/div[3]/div/div[1]/div[2]/div[2]'
            click_if_exists(driver, input_network2)
            time.sleep(random.uniform(2, 3))
            click_random_button(driver, selected_network_name)
            time.sleep(random.uniform(2, 3))
            value_input = '/html/body/div/main/div[2]/section/div[1]/div[2]/div[1]/div[4]/div[2]/div/input'
            input_text_if_exists(driver, value_input, round(max_value * CUSTOM_FACTOR, 3))
            transfer = '/html/body/div/main/div[2]/section/div[1]/div[2]/div[3]/div[2]/div/button'
            click_if_exists(driver, transfer)
            time.sleep(20)
            confirm_transaction(driver)
            try:
                time.sleep(30)
                confirm_transaction(driver)
            except Exception as e:
                print(f"Error encountered: {e}")
            time.sleep(30)
            got_it_bottom = '/html/body/div/main/div[2]/section/div[2]/div[2]/button'
            driver.switch_to.window(driver.window_handles[0])
            success = click_if_exists(driver, got_it_bottom)
            if not success:
                print(f"Failed for profile {idx}: {profile_id}, retrying...")
            else:
                data.loc[data["Profile ID"] == profile_id, "Totall TRX"] += 1
                data.loc[data["Profile ID"] == profile_id, "Totall Volume"] += max_value
                total_trx = data.loc[data["Profile ID"] == profile_id, "Totall TRX"].item()
                data.to_excel("data\\profiles_data.xlsx", index=False)
                print(f"Transfer successful for profile {idx}: {profile_id}")
                timer_element_locator = '//div[contains(@class, "MuiGrid-container")]//span'
                wait_for_timer(driver, timer_element_locator)
                time.sleep(additional_delay)
            if total_trx >= desired_trx:
                driver.close()
                print("TRX is reached")
                break
            else:
                continue
def get_timer_value(driver, timer_element_locator):
    try:
        element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, timer_element_locator)))
        if element.text in {"Finishing...", "Complete"}:
            return 1
        match = re.match(r'(\d+)m (\d+)s', element.text)
        if match:
            minutes, seconds = int(match.group(1)), int(match.group(2))
            timer_value = minutes * 60 + seconds
            return timer_value
        return None
    except TimeoutException:
        return None
def wait_for_timer(driver, timer_element_locator):
    timer_value = get_timer_value(driver, timer_element_locator)
    if timer_value is not None:
        time.sleep(timer_value)
def worker():
    while True:
        idx, profile_id = task_queue.get()
        if profile_id is None:
            break
        instruction(idx, profile_id)
        task_queue.task_done()


task_queue = Queue(max_simultaneous_profiles)
threads = []

for _ in range(max_simultaneous_profiles):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

for idx, profile_id in zip(range(start_idx, end_idx + 1), profile_ids[start_idx - 1:end_idx]):
    task_queue.put((idx, profile_id))
    time.sleep(20)

task_queue.join()

for _ in range(max_simultaneous_profiles):
    task_queue.put((None, None))

for t in threads:
    t.join()
#PERFORM BY @BROKEBOI_CAPITAL & GPT4