import requests
import json
import os
from datetime import datetime, timezone

DEPUTY_TOKEN = os.environ["DEPUTY_TOKEN"]
SUBDOMAIN = "rbpt.uk.deputy.com"
BASE_URL = f"https://{SUBDOMAIN}/api/v1"

HEADERS = {
    "Authorization": f"DeputyKey {DEPUTY_TOKEN}",
    "Content-Type": "application/json",
}

def get_today_range():
    now = datetime.now()
    start = int(datetime(now.year, now.month, now.day, 0, 0, 0).timestamp())
    end = int(datetime(now.year, now.month, now.day, 23, 59, 59).timestamp())
    return start, end

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
    return resp.json()

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

    output = {
        "date": datetime.now().strftime("%A %-d %B %Y"),
        "generated": datetime.now(timezone.utc).isoformat(),
        "shifts": shifts
    }

    with open("shifts-today.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Written {len(shifts)} shifts to shifts-today.json")

if __name__ == "__main__":
    main()
