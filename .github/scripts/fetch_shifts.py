import requests
import json
import os
from datetime import datetime, timezone, timedelta

DEPUTY_TOKEN = os.environ["DEPUTY_TOKEN"]
SUBDOMAIN = "rbpt.uk.deputy.com"
BASE_URL = f"https://{SUBDOMAIN}/api/v1"

HEADERS = {
    "Authorization": f"Bearer {DEPUTY_TOKEN}",
    "Content-Type": "application/json",
}

def get_london_time():
    # Get current UTC time and apply BST offset (UTC+1 in summer, UTC+0 in winter)
    # Deputy stores timestamps in local time, so we need London time
    now_utc = datetime.now(timezone.utc)
    # Use UTC+1 for BST (Mar-Oct), UTC+0 for GMT (Nov-Feb)
    # Simple check: BST is last Sunday March to last Sunday October
    month = now_utc.month
    if 3 < month < 10:
        offset = 1
    elif month == 3 or month == 10:
        # Check if past last Sunday
        # Approximate: use offset 1 for March after 25th, October before 25th
        offset = 1 if (month == 3 and now_utc.day >= 25) or (month == 10 and now_utc.day < 25) else 0
    else:
        offset = 0
    london_tz = timezone(timedelta(hours=offset))
    return datetime.now(london_tz), offset

def get_today_range():
    now_london, offset = get_london_time()
    today = now_london.date()
    # Midnight to 23:59 in London time, converted to UTC timestamps
    start_local = datetime(today.year, today.month, today.day, 0, 0, 0) - timedelta(hours=offset)
    end_local = datetime(today.year, today.month, today.day, 23, 59, 59) - timedelta(hours=offset)
    start = int(start_local.timestamp())
    end = int(end_local.timestamp())
    print(f"Date: {today}, UTC offset: +{offset}h, range: {start} to {end}")
    return start, end, offset

def fetch_employees():
    resp = requests.get(f"{BASE_URL}/resource/Employee?max=200", headers=HEADERS)
    resp.raise_for_status()
    employees = {}
    for emp in resp.json():
        employees[emp["Id"]] = {
            "name": f"{emp.get('FirstName', '')} {emp.get('LastName', '')}".strip(),
        }
    return employees

def fetch_departments():
    resp = requests.get(f"{BASE_URL}/resource/OperationalUnit?max=200", headers=HEADERS)
    resp.raise_for_status()
    departments = {}
    for dept in resp.json():
        departments[dept["Id"]] = dept.get("OperationalUnitName", "Unknown")
    return departments

def fetch_rosters(start, end):
    payload = {
        "search": {
            "s1": {"field": "StartTime", "type": "ge", "data": start},
            "s2": {"field": "StartTime", "type": "le", "data": end}
        },
        "sort": {"StartTime": "asc"},
        "max": 200
    }
    resp = requests.post(f"{BASE_URL}/resource/Roster/QUERY", headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()
    print(f"Fetched {len(data)} rosters")
    return data

def main():
    start, end, offset = get_today_range()
    employees = fetch_employees()
    departments = fetch_departments()
    rosters = fetch_rosters(start, end)

    london_tz = timezone(timedelta(hours=offset))
    shifts = []
    for r in rosters:
        emp_id = r.get("Employee")
        dept_id = r.get("OperationalUnit")
        emp = employees.get(emp_id, {})
        dept_name = departments.get(dept_id, "Unknown")
        # Parse timestamps and display in London time
        shift_start = datetime.fromtimestamp(r.get("StartTime", 0), tz=timezone.utc).astimezone(london_tz)
        shift_end = datetime.fromtimestamp(r.get("EndTime", 0), tz=timezone.utc).astimezone(london_tz)
        shifts.append({
            "name": emp.get("name", "Unknown"),
            "department": dept_name,
            "start": shift_start.strftime("%H:%M"),
            "end": shift_end.strftime("%H:%M"),
        })

    now_london = datetime.now(london_tz)
    output = {
        "date": now_london.strftime("%A %d %B %Y"),
        "generated": datetime.now(timezone.utc).isoformat(),
        "shifts": shifts
    }

    with open("shifts-today.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Written {len(shifts)} shifts to shifts-today.json")

if __name__ == "__main__":
    main()
