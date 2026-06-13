import pandas as pd
import os

def merge_historical_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_csv_path = os.path.join(script_dir, "tiszadorogma_adatok.csv")
    hist_csv_path = os.path.join(script_dir, "historikus.csv")

    if not os.path.exists(hist_csv_path):
        print(f"Hiba: Nem található a '{hist_csv_path}' fájl!")
        return

    if not os.path.exists(main_csv_path):
        print(f"Hiba: Nem található a '{main_csv_path}' fájl!")
        return

    print("Adatok beolvasása...")
    df_main = pd.read_csv(main_csv_path, delimiter=';')
    df_hist = pd.read_csv(hist_csv_path, delimiter=';')

    # Historikus adatok előkészítése: Dátumformátum és hiányzó adatok generálása
    if 'Észlelés dátuma' in df_hist.columns:
        parsed_dates = pd.to_datetime(df_hist['Észlelés dátuma'], errors='coerce')
        df_hist['Észlelés dátuma'] = parsed_dates.dt.strftime('%Y.%m.%d.')
        # Lekérdezés ideje kiegészítése: mindennap déli 12:00:00
        df_hist['Lekérdezés ideje'] = parsed_dates.dt.strftime('%Y-%m-%d 12:00:00')

    # Vízállás ma reggel másolása a tegnap estébe
    if 'Vízállás ma reggel' in df_hist.columns:
        df_hist['Vízállás tegnap este'] = df_hist['Vízállás ma reggel']

    # 1. Hiányzó oszlopok kiegészítése a historikus fájlban (üres értékekkel)
    for col in df_main.columns:
        if col not in df_hist.columns:
            df_hist[col] = ''

    # Csak a megfelelő oszlopokat tartjuk meg, pont olyan sorrendben, ahogy a fő fájlban van
    df_hist = df_hist[df_main.columns]

    # 2. Összefűzés
    df_merged = pd.concat([df_main, df_hist], ignore_index=True)

    # 3. Dátum szerinti sorbarendezés és ismétlődések kiszűrése
    df_merged['temp_date'] = pd.to_datetime(df_merged['Észlelés dátuma'].astype(str).str.replace(' ', ''), format='%Y.%m.%d.', errors='coerce')
    df_merged.sort_values(by='temp_date', inplace=True)
    df_merged.drop_duplicates(subset=['Észlelés dátuma'], keep='last', inplace=True)
    df_merged.drop(columns=['temp_date'], inplace=True)

    # 4. Mentés vissza az eredeti fájlba
    df_merged.to_csv(main_csv_path, sep=';', index=False, encoding='utf-8-sig')
    print("Sikeres összefésülés! A historikus adatok bekerültek a fő CSV fájlba.")

if __name__ == "__main__":
    merge_historical_data()