"""
Phone number list management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import phonenumbers
from io import BytesIO
import re
import logging

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.models import NumberList, PhoneNumber, User
from app.schemas import NumberListCreate, NumberListResponse, PhoneNumberResponse

router = APIRouter(prefix="/numbers", tags=["Phone Numbers"])
logger = logging.getLogger(__name__)

# Maximum file size in bytes (default 10MB)
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_ROWS = 50000


def validate_phone_number(phone: str, default_region: str = "TR") -> tuple[bool, str]:
    """Validate and format phone number"""
    try:
        # Clean the phone number
        cleaned = re.sub(r'[^\d+]', '', phone)

        # Parse the number
        parsed = phonenumbers.parse(cleaned, default_region)

        if phonenumbers.is_valid_number(parsed):
            # Format in E.164
            formatted = phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
            return True, formatted
        else:
            return False, phone
    except Exception:
        return False, phone


@router.get("/lists", response_model=List[NumberListResponse])
async def list_number_lists(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all number lists"""
    query = db.query(NumberList).filter(NumberList.owner_id == current_user.id)

    if status:
        query = query.filter(NumberList.status == status)

    lists = query.order_by(NumberList.created_at.desc()).offset(skip).limit(limit).all()
    return lists


@router.post("/upload", response_model=NumberListResponse)
async def upload_numbers(
    name: str,
    file: UploadFile = File(...),
    phone_column: str = "phone",
    name_column: Optional[str] = "name",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload phone numbers from Excel/CSV file.
    Maximum file size: 10MB (configurable).
    Maximum rows: 50,000
    """
    # Validate file type by extension
    filename = file.filename or ""
    if not filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported."
        )

    # Read file content with size limit
    content = b""
    chunk_size = 1024 * 1024  # 1MB chunks
    total_read = 0

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB."
            )
        content += chunk

    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        # Parse file
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))

        # Check required column
        if phone_column not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Phone column '{phone_column}' not found in file. Available columns: {list(df.columns)[:10]}"
            )

        # Limit number of rows
        if len(df) > MAX_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"File contains too many rows ({len(df)}). Maximum is {MAX_ROWS} rows."
            )

        # Create number list
        number_list = NumberList(
            name=name,
            file_name=filename,
            owner_id=current_user.id,
            status="processing"
        )
        db.add(number_list)
        db.commit()
        db.refresh(number_list)

        # Process numbers
        total = 0
        valid = 0
        invalid = 0
        seen = set()
        duplicates = 0

        for _, row in df.iterrows():
            phone_raw = str(row[phone_column]).strip()

            # Skip empty
            if not phone_raw or phone_raw == 'nan':
                continue

            total += 1

            # Validate phone
            is_valid, formatted_phone = validate_phone_number(phone_raw)

            # Check duplicate
            if formatted_phone in seen:
                duplicates += 1
                continue
            seen.add(formatted_phone)

            # Get name if column exists
            customer_name = None
            if name_column and name_column in df.columns:
                raw_name = row[name_column]
                if pd.notna(raw_name):
                    customer_name = str(raw_name).strip()[:255]  # Limit name length

            # Collect custom data (sanitize values)
            custom_data = {}
            for col in df.columns:
                if col not in [phone_column, name_column] and pd.notna(row[col]):
                    safe_col = str(col)[:100]
                    safe_val = str(row[col])[:500]
                    custom_data[safe_col] = safe_val

            # Create phone number record
            phone_number = PhoneNumber(
                phone=formatted_phone,
                name=customer_name,
                is_valid=is_valid,
                custom_data=custom_data if custom_data else None,
                number_list_id=number_list.id
            )
            db.add(phone_number)

            if is_valid:
                valid += 1
            else:
                invalid += 1

        # Update list stats
        number_list.total_numbers = total
        number_list.valid_numbers = valid
        number_list.invalid_numbers = invalid
        number_list.duplicates = duplicates
        number_list.status = "ready"
        number_list.custom_fields = {"columns": list(df.columns)[:50]}

        db.commit()
        db.refresh(number_list)

        return number_list

    except HTTPException:
        raise
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="File is empty or has no valid data")
    except Exception as e:
        logger.error(f"Error processing file upload: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@router.get("/lists/{list_id}", response_model=NumberListResponse)
async def get_number_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get number list details"""
    number_list = db.query(NumberList).filter(
        NumberList.id == list_id,
        NumberList.owner_id == current_user.id
    ).first()

    if not number_list:
        raise HTTPException(status_code=404, detail="Number list not found")

    return number_list


@router.delete("/lists/{list_id}")
async def delete_number_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a number list"""
    number_list = db.query(NumberList).filter(
        NumberList.id == list_id,
        NumberList.owner_id == current_user.id
    ).first()

    if not number_list:
        raise HTTPException(status_code=404, detail="Number list not found")

    # Delete associated phone numbers
    db.query(PhoneNumber).filter(PhoneNumber.number_list_id == list_id).delete()

    db.delete(number_list)
    db.commit()

    return {"success": True, "message": "Number list deleted successfully"}


@router.get("/lists/{list_id}/numbers", response_model=List[PhoneNumberResponse])
async def get_list_numbers(
    list_id: int,
    is_valid: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get phone numbers from a list"""
    # Verify list ownership
    number_list = db.query(NumberList).filter(
        NumberList.id == list_id,
        NumberList.owner_id == current_user.id
    ).first()

    if not number_list:
        raise HTTPException(status_code=404, detail="Number list not found")

    query = db.query(PhoneNumber).filter(PhoneNumber.number_list_id == list_id)

    if is_valid is not None:
        query = query.filter(PhoneNumber.is_valid == is_valid)

    if search:
        # Sanitize search input
        search_term = search[:50]
        query = query.filter(
            (PhoneNumber.phone.ilike(f"%{search_term}%")) |
            (PhoneNumber.name.ilike(f"%{search_term}%"))
        )

    numbers = query.offset(skip).limit(limit).all()
    return numbers


@router.delete("/lists/{list_id}/numbers/{number_id}")
async def delete_phone_number(
    list_id: int,
    number_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a phone number from a list"""
    # Verify list ownership
    number_list = db.query(NumberList).filter(
        NumberList.id == list_id,
        NumberList.owner_id == current_user.id
    ).first()

    if not number_list:
        raise HTTPException(status_code=404, detail="Number list not found")

    phone_number = db.query(PhoneNumber).filter(
        PhoneNumber.id == number_id,
        PhoneNumber.number_list_id == list_id
    ).first()

    if not phone_number:
        raise HTTPException(status_code=404, detail="Phone number not found")

    # Update list stats safely
    if phone_number.is_valid:
        number_list.valid_numbers = max(0, number_list.valid_numbers - 1)
    else:
        number_list.invalid_numbers = max(0, number_list.invalid_numbers - 1)
    number_list.total_numbers = max(0, number_list.total_numbers - 1)

    db.delete(phone_number)
    db.commit()

    return {"success": True, "message": "Phone number deleted"}


@router.post("/validate")
async def validate_single_number(phone: str):
    """Validate a single phone number"""
    # Sanitize input
    phone = phone[:50]
    is_valid, formatted = validate_phone_number(phone)
    return {
        "original": phone,
        "formatted": formatted,
        "is_valid": is_valid
    }
