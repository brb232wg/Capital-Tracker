from csv import excel

import pandas as pd
import os
import sqlite3
import random
from faker import Faker
from datetime import datetime

fake = Faker()

# output directory
output_dir = "Sanction-db-files"
os.makedirs(output_dir, exist_ok=True)

#External_country-ccy file
country_file = "../Source-files/Country_Codes_Scoring.xlsx"
country_df = pd.read_excel(country_file)
country_df.columns = country_df.columns.str.strip()

country_df = country_df.rename(columns={
    "Country Name": "country_name",
    "Country Code": "country_code",
    "Tax_haven?": "tax_haven",
    "High_risk?": "high_risk",
    "Terror_haven?": "terror_haven",
    "CCY": "ccy"
})
country_df["country_code"] = country_df["country_code"].astype(str).str.upper().str.strip()
countries = country_df["country_code"].dropna().tolist()


def get_currency(country_code):
    match = country_df[country_df["country_code"] == country_code]

    if match.empty:
        return "USD"

    raw_ccy = str(match.iloc[0].get("ccy", "")).strip().upper()

    if raw_ccy and raw_ccy not in ["#N/A", "NAN", "NONE", ""]:
        return raw_ccy

    eur_fallback = {
        "AD","AT","BE","HR","CY","EE","FI","FR","DE","GR","IE","IT","LV","LT",
        "LU","MT","MC","ME","NL","PT","SM","SK","SI","ES","VA","AX"
    }

    usd_fallback = {
        "AS","BQ","EC","SV","FM","GU","MH","MP","PW","PA","PR","TC","UM","VI"
    }

    gbp_fallback = {
        "GG","IM","JE"
    }

    aud_fallback = {
        "CX","CC","HM","KI","NR","NF","TV"
    }

    xpf_fallback = {
        "NC","PF","WF"
    }

    xof_fallback = {
        "BJ","BF","CI","GW","ML","NE","SN","TG"
    }

    xaf_fallback = {
        "CM","CF","TD","CG","GQ","GA"
    }

    if country_code in eur_fallback:
        return "EUR"
    elif country_code in usd_fallback:
        return "USD"
    elif country_code in gbp_fallback:
        return "GBP"
    elif country_code in aud_fallback:
        return "AUD"
    elif country_code in xpf_fallback:
        return "XPF"
    elif country_code in xof_fallback:
        return "XOF"
    elif country_code in xaf_fallback:
        return "XAF"

    return "USD"


def generate_operations_countries(registered_country, countries):
    num_extra = random.randint(1, 3)  # number of additional countries

    possible = [c for c in countries if c != registered_country]
    selected = random.sample(possible, num_extra)
    all_countries = [registered_country] + selected

    return ",".join(all_countries)

def get_multi_country_risk(operations_country):
    country_list = operations_country.split(",")
    return max(get_country_risk(c) for c in country_list)

def get_country_risk(country_code):
    match = country_df[country_df["country_code"] == country_code]

    if match.empty:
        return 2

    row = match.iloc[0]  # converts matched row into a single record

    score = 1

    if str(row["high_risk"]).strip().upper() == "Y":
        score += 1

    if str(row["tax_haven"]).strip().upper() == "Y":
        score += 1

    terror_value = str(row["terror_haven"]).strip().upper()

    if terror_value == "Y":
        score += 2
    elif terror_value == "P":
        score += 1

    return min(score, 3)

def generate_entity():
    country = random.choice(countries)
    ent_type = "P" if random.random() < 0.60 else "C"

    if ent_type == "P":
        dob = fake.date_of_birth(minimum_age=18, maximum_age=85)
        dob_str = dob.strftime("%Y%m%d")
        entity_id = country + dob_str
        turnover = random.randint(50000, 250000)
        return {
            "Entity_ID": entity_id,
            "Registered_country": country,
            "Operations_country": country,
            "Entity_type": "P",
            "Entity_name": fake.name().upper(),
            "Date_of_birth": dob,
            "Registered_number": None,
            "Entity_segment_1": "PRIVATE",
            "Entity_segment_2": None,
            "Entity_segment_3": None,
            "Risk_score": get_country_risk(country),
            "PE_flag": "Y" if random.random() < 0.08 else "N",
            "Expected_turnover": turnover,
            "Turnover_ccy": get_currency(country),
            "Last_updated": datetime.today().date()
        }
    else:
        size_roll = random.random()
        if size_roll < 0.6:
            seg2, turnover = "SMALL", random.randint(100000, 1_000_000)
        elif size_roll < 0.9:
            seg2, turnover = "MEDIUM", random.randint(1_000_000, 10_000_000)
        else:
            seg2, turnover = "LARGE", random.randint(10_000_000, 100_000_000)

        unique = str(random.randint(10000000, 99999999))  # your registered number
        entity_id = country + unique
        operations_country = generate_operations_countries(country, countries)

        return {
            "Entity_ID": entity_id,
            "Registered_country": country,
            "Operations_country": operations_country,
            "Entity_type": "C",
            "Entity_name": fake.company().upper(),
            "Date_of_birth": None,
            "Registered_number": unique,
            "Entity_segment_1": "CORPORATE",
            "Entity_segment_2": seg2,
            "Entity_segment_3": "INDUSTRIAL",
            "Risk_score": get_multi_country_risk(country),
            "PE_flag": "Y" if random.random() < 0.08 else "N",
            "Expected_turnover": turnover,
            "Turnover_ccy": get_currency(country),
            "Last_updated": datetime.today().date()
        }

# generate dataset (changeable count)
data = [generate_entity() for _ in range(200)]
df = pd.DataFrame(data)

#Local database file
db_path = os.path.join(output_dir, "sanctions_network.db")
conn = sqlite3.connect(db_path)
df.to_sql("entities", conn, if_exists="replace", index=False)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM entities")
db_count = cursor.fetchone()[0]
conn.close()

print(f"Inserted rows (DataFrame): {len(df)}")
print(f"Rows in DB (entities table): {db_count}")

# export
excel_path = os.path.join(output_dir,"entities_mock.xlsx")
df.to_excel(excel_path, index=False)

print(f"Database generated: {db_path}")
print(f"Dataset generated: {excel_path}")