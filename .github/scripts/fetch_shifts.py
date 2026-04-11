import requests
import json
import os
from datetime import datetime, timezone, date
import calendar

DEPUTY_TOKEN = os.environ["DEPUTY_TOKEN"]
SUBDOMAIN = "rbpt.uk.deputy.com"
BASE_URL = f"https://{SUBDOMAIN}/api/v1"

HEADERS = {
    "Authorization": f"Bearer {DEPUTY_TOKEN}",
    "Content-Type": "application/json",
}

def get_today_range():
    # Deputy stores times as Unix timestamps in local time (Europe/London)
    # Use calendar to get today's range in UTC but accounting for BST offset
    import subprocess
    # Get current date in London time
    result = subprocess.run(
        ['date', '-d', 'today 00:00:00', '+%s'],
        capture_output=True, text=True
    )
    # Simpler: use the deputy API's own date format
    # Just use a wide range - start of today UTC to end of tomorrow UTC
    # to catch all shifts regardless of timezone offset
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()
    start = int(datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=timezone.utc).timestamp())
    end = int(datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc).timestamp())
    # Add 2 hours buffer on each side for BST
    start -= 7200
    end += 7200
    print(f"Date range: {start} to {end} ({today})")
    return start, end

def fetch_employees():
    resp = requests.get(f"{BASE_URL}/resource/Employee?max=200", headers=HEADERS)
    resp.raise_for_status()
    employees = {}
    for emp in resp.json():
        employees[emp["Id"]] = {
            "name": f"{emp.get('FirstName', '')} {emp.get('LastName', '')}".strip(),
        }
    print(f"Fetched {len(employees)} employees")
    return employees

def fetch_departments():
    resp = requests.get(f"{BASE_URL}/resource/OperationalUnit?max=200", headers=HEADERS)
    resp.raise_for_status()
    departments = {}
    for dept in resp.json():
        departments[dept["Id"]] = dept.get("OperationalUnitName", "Unknown")
    print(f"Fetched {len(departments)} departments")
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
    start, end = get_today_range()
    employees = fetch_employees()
    departments = fetch_departments()
    rosters = fetch_rosters(start, end)

    shifts = []
    for r in rosters:
        emp_id = r.get("Employee")
        dept_id = r.get("OperationalUnit")
        emp = employees.get(emp_id, {})
        dept_name = departments.get(dept_id, "Unknown")
        shift_start = datetime.fromtimestamp(r.get("StartTime", 0))
        shift_end = datetime.fromtimestamp(r.get("EndTime", 0))
        shifts.append({
            "name": emp.get("name", "Unknown"),
            "department": dept_name,
            "start": shift_start.strftime("%H:%M"),
            "end": shift_end.strftime("%H:%M"),
        })

    now = datetime.now()
    output = {
        "date": now.strftime("%A %d %B %Y"),
        "generated": datetime.now(timezone.utc).isoformat(),
        "shifts": shifts
    }

    with open("shifts-today.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Written {len(shifts)} shifts to shifts-today.json")

if __name__ == "__main__":
    main()
