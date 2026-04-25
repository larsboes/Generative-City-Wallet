import json
import urllib.request
import urllib.parse


def send_request(url, method="GET", data=None):
    headers = {}
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            print(f"[{method}] {url} -> {status}")
            try:
                parsed = json.loads(body)
                print(
                    json.dumps(parsed, indent=2)[:500]
                    + ("...\n" if len(body) > 500 else "\n")
                )
            except json.JSONDecodeError:
                print(body[:500] + "\n")
    except urllib.error.HTTPError as e:
        print(f"[{method}] {url} -> {e.code}")
        body = e.read().decode("utf-8")
        try:
            parsed = json.loads(body)
            print(json.dumps(parsed, indent=2))
        except json.JSONDecodeError:
            print(body)
    except Exception as e:
        print(f"[{method}] {url} -> ERROR: {e}")
    print("-" * 40)


print("1. Generate History")
send_request(
    "http://127.0.0.1:8000/api/transactions/generate/history",
    method="POST",
    data={
        "city": "München",
        "category": "bar,cafe,restaurant",
        "limit": 10,
        "days": 28,
        "seed": 42,
    },
)

print("2. Generate Live Update")
send_request(
    "http://127.0.0.1:8000/api/transactions/generate/live-update",
    method="POST",
    data={
        "city": "München",
        "category": "bar,cafe,restaurant",
        "limit": 10,
        "seed": 43,
    },
)

endpoints = [
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/api/venues?category=bar,cafe&city=M%C3%BCnchen&limit=10",
]

for url in endpoints:
    send_request(url)

# Fetch venues to get a valid merchant ID
print("Fetching venues to extract a valid merchant ID...")
try:
    with urllib.request.urlopen(
        "http://127.0.0.1:8000/api/venues?category=bar,cafe&city=M%C3%BCnchen&limit=1"
    ) as response:
        data = json.loads(response.read().decode("utf-8"))
        if data.get("venues") and len(data["venues"]) > 0:
            merchant_id = data["venues"][0]["merchant_id"]
            print(f"Using dynamically fetched merchant_id: {merchant_id}\n")

            vendor_endpoints = [
                f"http://127.0.0.1:8000/api/occupancy/{merchant_id}",
                f"http://127.0.0.1:8000/api/vendors/{merchant_id}/transactions/daily",
                f"http://127.0.0.1:8000/api/vendors/{merchant_id}/transactions/averages?lookback_days=28",
                f"http://127.0.0.1:8000/api/vendors/{merchant_id}/revenue/last-7-days",
                f"http://127.0.0.1:8000/api/vendors/{merchant_id}/dashboard/today",
                f"http://127.0.0.1:8000/api/vendors/{merchant_id}/transactions/hour-rankings?lookback_days=28",
            ]

            for url in vendor_endpoints:
                send_request(url)

            print("Occupancy Query")
            send_request(
                "http://127.0.0.1:8000/api/occupancy/query",
                method="POST",
                data={"merchant_ids": [merchant_id], "arrival_offset_minutes": 10},
            )
        else:
            print("No venues found in the response to use for further tests.")
except Exception as e:
    print(f"Failed to fetch venues: {e}")
