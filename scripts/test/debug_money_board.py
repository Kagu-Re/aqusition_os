import requests
import json

def test_money_board():
    try:
        response = requests.get("http://localhost:8000/api/money-board?db=acq.db")
        response.raise_for_status()
        data = response.json()
        
        print(f"Columns: {len(data['columns'])}")
        for col in data['columns']:
            print(f"Status: {col['status']}, Count: {col['count']}")
            if col['items']:
                first = col['items'][0]
                print(f"  First Item: {json.dumps(first, indent=2)}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_money_board()
