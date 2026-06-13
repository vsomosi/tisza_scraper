import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime
import re

def fetch_tiszadorogma_data():
    url = "https://www.hydroinfo.hu/tables/tishid.html"
    
    try:
        # 1. Weboldal letöltése
        response = requests.get(url)
        response.raise_for_status() # Hibát dob, ha nem sikeres a letöltés (pl. 404)
        response.encoding = 'utf-8' # Beállítjuk a magyar ékezetek megfelelő kezeléséhez
        
        # 2. HTML tartalom feldolgozása
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Észlelés dátumának kinyerése az oldalszövegből (pl. 2023. 10. 25.)
        date_match = re.search(r'(20\d{2}\.\s*\d{1,2}\.\s*\d{1,2}\.)', soup.get_text())
        observation_date = date_match.group(1).strip() if date_match else datetime.now().strftime("%Y.%m.%d.")

        # 3. Keresés a táblázat soraiban ('tr' tagek)
        rows = soup.find_all('tr')
        
        target_data = []
        tiszapalkonya_data = []
        
        for row in rows:
            # Kinyerjük a sorban lévő cellákat ('td' vagy 'th')
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            
            if row_data:
                # Kikeressük Tiszadorogma és Tiszapalkonya sorát is
                if any("Tiszadorogma" in cell for cell in row_data):
                    target_data = row_data
                if any("Tiszapalkonya" in cell for cell in row_data):
                    tiszapalkonya_data = row_data
                
        if not target_data:
            print("Nem található 'Tiszadorogma' a weboldalon lévő táblázatban.")
            return

        # Tiszapalkonya reggeli hozam adatának (7. index) beillesztése Tiszadorogma adatai közé
        if tiszapalkonya_data and len(tiszapalkonya_data) > 7 and len(target_data) > 7:
            target_data[7] = tiszapalkonya_data[7]

        # 4. Adatok mentése CSV fájlba
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(script_dir, "tiszadorogma_adatok.csv")
        file_exists = os.path.isfile(filename)
        
        # Ellenőrizzük, hogy erre a dátumra van-e már mentett adatunk
        if file_exists:
            with open(filename, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.reader(csv_file, delimiter=';')
                for row in reader:
                    # Ha a 2. oszlopban (index 1) már szerepel a kinyert dátum, nem rögzítünk újra
                    if len(row) > 1 and row[1] == observation_date:
                        print(f"Erre a napra ({observation_date}) már van rögzített adat. Nem történt mentés.")
                        return

        # Hasznos lehet tudni, mikor történt a mentés, ezt beszúrjuk az elejére
        scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_data.insert(0, observation_date)
        target_data.insert(0, scrape_time)
        
        # 'a' (append) mód biztosítja, hogy a korábbi adatokat ne írjuk felül
        with open(filename, mode='a', newline='', encoding='utf-8-sig') as csv_file:
            # A magyar nyelvű Excel a pontosvesszőt (;) ismeri fel alapértelmezett oszlopelválasztóként
            writer = csv.writer(csv_file, delimiter=';')
            
            # Fejléc írása, ha a fájl még nem létezett
            if not file_exists:
                headers = [
                    "Lekérdezés ideje", "Észlelés dátuma", "Állomáskód", "Állomás név", 
                    "Folyónév", "Vízállás tegnap reggel", "Vízállás tegnap este", 
                    "Vízállás ma reggel", "Változás 24 óra alatt", "Reggeli hozam", "Reggeli víz hőmérséklet", "Reggeli jégállapot"
                ]
                writer.writerow(headers)
                
            writer.writerow(target_data)
            
        print(f"Sikeres adatmentés! Fájl: {filename}")
        print(f"Kimentett adatsor: {target_data}")

    except requests.exceptions.RequestException as e:
        print(f"Hálózati hiba történt a weboldal elérésekor: {e}")
    except Exception as e:
        print(f"Váratlan hiba történt: {e}")

if __name__ == "__main__":
    fetch_tiszadorogma_data()