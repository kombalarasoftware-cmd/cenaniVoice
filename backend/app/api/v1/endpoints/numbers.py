"""
Phone Numbers endpoints
"""

from fastapi import APIRouter, UploadFile, File

router = APIRouter()


@router.get("/lists")
async def list_number_lists():
    """List all number lists"""
    return {"message": "List number lists endpoint"}


@router.post("/lists")
async def create_number_list():
    """Create a new number list"""
    return {"message": "Create number list endpoint"}


@router.get("/lists/{list_id}")
async def get_number_list(list_id: str):
    """Get number list by ID"""
    return {"message": f"Get number list {list_id}"}


@router.delete("/lists/{list_id}")
async def delete_number_list(list_id: str):
    """Delete number list"""
    return {"message": f"Delete number list {list_id}"}


@router.post("/upload")
async def upload_numbers(file: UploadFile = File(...)):
    """Upload Excel file with phone numbers"""
    # TODO: Process Excel file
    return {"message": f"Uploaded file: {file.filename}"}


@router.get("/lists/{list_id}/numbers")
async def get_numbers_in_list(list_id: str):
    """Get all numbers in a list"""
    return {"message": f"Numbers in list {list_id}"}


@router.post("/lists/{list_id}/assign")
async def assign_list_to_campaign(list_id: str, campaign_id: str):
    """Assign number list to a campaign"""
    return {"message": f"Assign list {list_id} to campaign {campaign_id}"}
