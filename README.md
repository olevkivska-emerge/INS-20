# INS-20 Loads API Script

This script processes test cases from the Excel file and sends POST requests to the Emerge Insights API.

## Setup

1. Install required Python packages:
```bash
pip3 install pandas openpyxl requests
```

## Configuration

The API requires Basic Authentication. You need to provide your credentials using one of these methods:

### Method 1: Environment Variables (Recommended)
```bash
export EMERGE_API_USERNAME='your_username'
export EMERGE_API_PASSWORD='your_password'
```

### Method 2: Edit the Script
Edit `send_loads.py` and update these lines:
```python
API_USERNAME = "int"
API_PASSWORD = "vXfAZJ7Zg9pJf6Uyy"
```

## Usage

Run the script:
```bash
python3 send_loads.py
```

The script will:
1. Read test cases from `Address Normalization Test Cases (3).xlsx`
2. Process each test case and build the API payload
3. Send POST requests to `https://int-insights-webapi.emergemarket.dev/api/v1/loads`
4. Save results to `api_results.csv`

## API Endpoint

- **URL**: `https://int-insights-webapi.emergemarket.dev/api/v1/loads`
- **Method**: POST
- **Headers**:
  - `Content-Type: application/json`
  - `organization-id: b8411102-f0a5-423f-bd8a-c84734288fb1`
- **Authentication**: Basic Auth (username/password)

## Output

The script generates `api_results.csv` with the following columns:
- `test_case_id`: Test case identifier
- `external_shipment_id`: External shipment ID
- `status_code`: HTTP status code from API
- `success`: Boolean indicating if request was successful
- `response`: API response text

## Files

- `send_loads.py`: Main script
- `Address Normalization Test Cases (3).xlsx`: Test case data
- `Warehouse Addresses Database (1).csv`: Warehouse address reference data
- `api_results.csv`: Generated results file

