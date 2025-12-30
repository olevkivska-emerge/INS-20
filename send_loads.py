#!/usr/bin/env python3
"""
Script to process test cases from Excel file and send POST requests to the loads API.
"""

import pandas as pd
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# API Configuration
API_URL = "https://int-insights-webapi.emergemarket.dev/api/v1/loads"
ORGANIZATION_ID = "b8411102-f0a5-423f-bd8a-c84734288fb1"

# Authentication
import os
API_USERNAME = os.getenv("EMERGE_API_USERNAME", "int")
API_PASSWORD = os.getenv("EMERGE_API_PASSWORD", "vXfAZJ7Zg9pJf6Uyy")

def clean_value(value):
    """Clean pandas values (handle NaN, None, etc.)"""
    if pd.isna(value) or value is None:
        return None
    if isinstance(value, str):
        return value.strip() if value.strip() else None
    return value

def build_location(row: pd.Series, prefix: str) -> Optional[Dict[str, Any]]:
    """Build location object from row data with given prefix."""
    address1 = clean_value(row.get(f'{prefix}_LOCATION_ADDRESS1'))
    if not address1:
        return None
    
    location = {
        "name": clean_value(row.get(f'{prefix}_LOCATION_NAME')) or "",
        "location_code": clean_value(row.get(f'{prefix}_LOCATION_CODE')) or "",
        "address1": address1,
        "address2": clean_value(row.get(f'{prefix}_LOCATION_ADDRESS2')) or "",
        "city": clean_value(row.get(f'{prefix}_LOCATION_CITY')) or "",
        "state": clean_value(row.get(f'{prefix}_LOCATION_STATE')) or "",
        "postal_code": str(clean_value(row.get(f'{prefix}_LOCATION_POSTAL_CODE')) or ""),
        "country_code": clean_value(row.get(f'{prefix}_LOCATION_COUNTRY_CODE')) or "US"
    }
    return location

def build_appointment(row: pd.Series, prefix: str) -> Optional[Dict[str, Any]]:
    """Build appointment object from row data with given prefix."""
    appt_type = clean_value(row.get(f'{prefix}_APPOINTMENT_TYPE'))
    if not appt_type or appt_type == 'NONE':
        return {"type": "NONE"}
    
    appointment = {
        "type": appt_type,
        "scheduled_earliest": clean_value(row.get(f'{prefix}_APPOINTMENT_SCHEDULED_EARLIEST')),
        "scheduled_latest": clean_value(row.get(f'{prefix}_APPOINTMENT_SCHEDULED_LATEST')),
        "original_earliest": clean_value(row.get(f'{prefix}_APPOINTMENT_ORIGINAL_EARLIEST')),
        "original_latest": clean_value(row.get(f'{prefix}_APPOINTMENT_ORIGINAL_LATEST'))
    }
    
    # Remove None values
    appointment = {k: v for k, v in appointment.items() if v is not None}
    return appointment

def build_actual(row: pd.Series, prefix: str) -> Optional[Dict[str, Any]]:
    """Build actual object from row data with given prefix."""
    arrived_at = clean_value(row.get(f'{prefix}_ACTUAL_ARRIVED_AT'))
    departed_at = clean_value(row.get(f'{prefix}_ACTUAL_DEPARTED_AT'))
    
    if not arrived_at and not departed_at:
        return None
    
    actual = {}
    if arrived_at:
        actual["arrived_at"] = arrived_at
    if departed_at:
        actual["departed_at"] = departed_at
    
    return actual if actual else None

def build_stop(row: pd.Series, prefix: str) -> Optional[Dict[str, Any]]:
    """Build stop object from row data with given prefix."""
    location = build_location(row, prefix)
    if not location:
        return None
    
    stop = {
        "sequence_number": int(clean_value(row.get(f'{prefix}_SEQUENCE_NUMBER')) or 0),
        "stop_type": clean_value(row.get(f'{prefix}_STOP_TYPE')) or "PICKUP",
        "loading_type": clean_value(row.get(f'{prefix}_LOADING_TYPE')) or "LIVE",
        "location": location
    }
    
    # Add appointment if available
    appointment = build_appointment(row, prefix)
    if appointment:
        stop["appointment"] = appointment
    
    # Add actual if available
    actual = build_actual(row, prefix)
    if actual:
        stop["actual"] = actual
    
    # Add notes if available
    notes = clean_value(row.get(f'{prefix}_NOTES'))
    if notes:
        stop["notes"] = notes
    
    return stop

def build_load_payload(row: pd.Series) -> Dict[str, Any]:
    """Build the complete load payload from a row."""
    payload = {
        "external_shipment_id": clean_value(row.get('EXTERNAL_SHIPMENT_ID')) or "",
        "external_tender_id": clean_value(row.get('EXTERNAL_TENDER_ID')) or "",
        "type": clean_value(row.get('TYPE')) or "SHIPMENT",
        "status": clean_value(row.get('STATUS')) or "TENDERED",
        "contract_type": clean_value(row.get('CONTRACT_TYPE')) or "UNKNOWN",
        "mode": clean_value(row.get('MODE')) or "TRUCKLOAD",
        "equipment_type": clean_value(row.get('EQUIPMENT_TYPE')) or "",
    }
    
    # Length of haul
    loh_value = clean_value(row.get('LENGTH_OF_HAUL_VALUE'))
    loh_unit = clean_value(row.get('LENGTH_OF_HAUL_UNIT'))
    if loh_value is not None:
        payload["length_of_haul"] = {
            "value": float(loh_value),
            "unit": loh_unit or "MI"
        }
    
    # Weight
    weight_value = clean_value(row.get('WEIGHT_VALUE'))
    weight_unit = clean_value(row.get('WEIGHT_UNIT'))
    if weight_value is not None:
        payload["weight"] = {
            "value": float(weight_value),
            "unit": weight_unit or "LB"
        }
    
    # Tender (simplified - using current timestamp)
    payload["tender"] = {
        "status": "PENDING",
        "tender_created_at": datetime.utcnow().isoformat() + "Z",
        "tendered_at": datetime.utcnow().isoformat() + "Z"
    }
    
    # Carrier
    carrier_name = clean_value(row.get('CARRIER_NAME'))
    if carrier_name:
        payload["carrier"] = {
            "name": carrier_name,
            "external_reference": clean_value(row.get('CARRIER_EXTERNAL_REFERENCE')) or "",
            "scac": clean_value(row.get('CARRIER_SCAC')) or "",
            "dot": clean_value(row.get('CARRIER_DOT')) or "",
            "docket": clean_value(row.get('CARRIER_DOCKET')) or ""
        }
    
    # Stops
    stops = []
    
    # Origin stop
    origin_stop = build_stop(row, 'ORIGIN')
    if origin_stop:
        stops.append(origin_stop)
    
    # Destination stop
    dest_stop = build_stop(row, 'DESTINATION')
    if dest_stop:
        stops.append(dest_stop)
    
    payload["stops"] = stops
    
    # Charges (empty for now)
    payload["charges"] = {
        "line_items": []
    }
    
    # References (empty for now)
    payload["references"] = []
    
    # Metadata
    payload["metadata"] = {
        "shipment_created_at": datetime.utcnow().isoformat() + "Z",
        "source_system": "test",
        "commodity": "",
        "customer": {
            "external_id": "",
            "name": ""
        },
        "division": {
            "external_id": "",
            "name": ""
        },
        "oversize": False,
        "temperature_controlled": False,
        "hazmat": False
    }
    
    return payload

def send_load(payload: Dict[str, Any]) -> requests.Response:
    """Send a single load payload to the API."""
    headers = {
        "Content-Type": "application/json",
        "organization-id": ORGANIZATION_ID
    }
    
    # Add Basic Auth if credentials are provided
    auth = None
    if API_USERNAME and API_PASSWORD:
        auth = (API_USERNAME, API_PASSWORD)
    
    response = requests.post(API_URL, json=payload, headers=headers, auth=auth)
    return response

def main():
    """Main function to process Excel file and send requests."""
    # Check authentication
    if not API_USERNAME or not API_PASSWORD:
        print("WARNING: API credentials not set!")
        print("The API requires Basic Authentication.")
        print("Please set your credentials using one of these methods:")
        print("  1. Set environment variables:")
        print("     export EMERGE_API_USERNAME='your_username'")
        print("     export EMERGE_API_PASSWORD='your_password'")
        print("  2. Edit the script and set API_USERNAME and API_PASSWORD directly")
        print("\nContinuing without authentication (requests will likely fail with 401)...\n")
    
    # Read Excel file
    print("Reading Excel file...")
    df = pd.read_excel('Address Normalization Test Cases (3).xlsx')
    
    print(f"Found {len(df)} test cases")
    print("\nProcessing and sending requests...\n")
    
    results = []
    
    for idx, row in df.iterrows():
        test_case_id = clean_value(row.get('TEST_CASE_ID')) or f"ROW_{idx+1}"
        external_shipment_id = clean_value(row.get('EXTERNAL_SHIPMENT_ID')) or ""
        
        print(f"Processing {test_case_id} ({external_shipment_id})...")
        
        try:
            # Build payload
            payload = build_load_payload(row)
            
            # Send request
            response = send_load(payload)
            
            # Store result
            try:
                response_json = response.json() if response.text else {}
            except:
                response_json = {}
            
            result = {
                "test_case_id": test_case_id,
                "external_shipment_id": external_shipment_id,
                "status_code": response.status_code,
                "success": response.status_code in [200, 201],
                "response": response.text[:500] if response.text else "",
                "response_json": response_json
            }
            
            results.append(result)
            
            if result["success"]:
                print(f"  ✓ Success (Status: {response.status_code})")
                if response_json:
                    print(f"    Response: {json.dumps(response_json, indent=2)[:200]}")
            else:
                print(f"  ✗ Failed (Status: {response.status_code})")
                if response_json:
                    print(f"    Response: {json.dumps(response_json, indent=2)}")
                elif response.text:
                    print(f"    Response: {response.text[:200]}")
                else:
                    print(f"    Response: (empty)")
        
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({
                "test_case_id": test_case_id,
                "external_shipment_id": external_shipment_id,
                "status_code": None,
                "success": False,
                "response": str(e)
            })
        
        print()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    print(f"Total: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    # Save results to file
    results_df = pd.DataFrame(results)
    results_df.to_csv('api_results.csv', index=False)
    print(f"\nResults saved to api_results.csv")
    
    # Print failed cases
    if failed > 0:
        print("\nFailed cases:")
        for result in results:
            if not result["success"]:
                print(f"  - {result['test_case_id']}: {result['response']}")

if __name__ == "__main__":
    main()

