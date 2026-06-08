import pandas as pd
import sqlite3

excel_path = "database/OWD_VENIER.xlsx"
db_path = "database/owd_venier.db"

xls = pd.ExcelFile(excel_path)

conn = sqlite3.connect(db_path)

for hoja in xls.sheet_names:

    df = pd.read_excel(
        excel_path,
        sheet_name=hoja
    )

    df.to_sql(
        hoja,
        conn,
        if_exists="replace",
        index=False
    )

    print(f"Migrada hoja: {hoja}")

conn.close()

print("✅ Migración terminada")