import os
import re
import sys
import time
from pathlib import Path
from typing import List, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urljoin

class bns_crawler:
    def __init__(
            self,
            url: str,
            out_dir: str,
            headless: bool=True,
            wait_s: int=12,
    ) -> None:
        self.url = url
        self.out_dir = out_dir
        self.headless = headless
        self.wait_s = wait_s

        opts = webdriver.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1280,1800")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=opts
        )
        self.wait = WebDriverWait(self.driver, wait_s)

    def _ready(self):
        self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    
    def _visible(self, by, sel):
        return self.wait.until(EC.visibility_of_element_located((by, sel)))

    def extract_chapter_list(self, user_name, pass_word):
        #Login
        self.driver.get(self.url)
        self._ready()

        login_bt = self.driver.find_element(By.CSS_SELECTOR, "a.bg-blue-600")
        login_bt.click()

        username_input = self.wait.until(EC.presence_of_element_located((By.NAME, "login")))
        password = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))

        username_input.send_keys(user_name)
        password.send_keys(pass_word)

        login_cf = self.wait.until(EC.presence_of_element_located(
            (By.XPATH, "//span[@class='button-text' and text()='Đăng nhập']")
        ))
        self.driver.execute_script("arguments[0].click();", login_cf)

        #login_btn_1 = self.driver.find_element(By.XPATH, "//span[@class='button-text' and text()='Đăng nhập']")
        #login_btn_1.click()

        #Muc luc day du
        full_chapters = self.wait.until(EC.presence_of_element_located((By.ID, "chuong-list-more")))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", full_chapters)
        full_chapters.click()

        #Trich xuat duong dan cac chuong
        chap_elems = self.wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#mucluc-list a.chuong-link")))

        chapters = []
        for i, a in enumerate(chap_elems, start=1):
            try:
                title = a.find_element(By.CSS_SELECTOR, ".chuong-name").text.strip()
            except Exception:
                title = a.text.strip()

            href = a.get_attribute("href") or a.get_attribute("data-href") or ""
            if href and href != "about:blank":
                href = urljoin(self.driver.current_url, href)

            chapters.append((i, title, href))

        return chapters
    
    def extract_content(self, user_name, pass_word):
        chapters = self.extract_chapter_list(user_name, pass_word)
        self.driver.get(self.url)
        name = self.driver.find_element(By.ID, "truyen-title").text
        out_dir = os.path.join(self.out_dir, name)
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        for i, title, link in chapters:
            print(f"Đang tải chương {i}: {title} - {link}")
            try:
                self.driver.get(link)
                self._ready()

                html = self.driver.execute_script("return document.documentElement.outerHTML;")

                content_elem = self.wait.until(
                    EC.presence_of_element_located((By.ID, "noi-dung"))
                )
                chap_text = content_elem.text.strip()

                # lưu ra file txt
                safe_title = re.sub(r"[\\/:*?\"<>|]+", " ", title)[:80]
                fname = f"{i:03d}_{safe_title}.txt"
                fpath = Path(out_dir) / fname

                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(title + "\n\n")
                    f.write(chap_text + "\n")

                print(f"  ✓ Saved {fpath.name}")
            except Exception as e:
                print(f"  ⚠️ Lỗi ở chương {i} ({link}): {e}")  

#Example
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    user_name = os.getenv("user_name")
    pass_word = os.getenv("pass_word")
    test = bns_crawler('https://bnsach.com/reader/cau-tai-so-thanh-ma-mon-lam-nhan-tai-convert', "story/com", True, 10)
    test.extract_content(user_name, pass_word)
