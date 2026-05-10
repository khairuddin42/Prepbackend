import tempfile
import os
import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
import pdfplumber
import PyPDF2
from docx import Document
from PIL import Image
import pytesseract
import httpx
from app.deps import get_current_user, User
from app.config import settings

router = APIRouter()

# Supported file types and their MIME types
SUPPORTED_TYPES = {
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'text/plain': '.txt',
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/jpg': '.jpg'
}

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber (preferred) with PyPDF2 fallback."""
    text = ""
    
    try:
        # Try pdfplumber first (better text extraction)
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber failed: {e}, trying PyPDF2 fallback")
        
        # Fallback to PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e2:
            raise Exception(f"Both PDF extraction methods failed: pdfplumber: {e}, PyPDF2: {e2}")
    
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file using python-docx."""
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {e}")

def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file with UTF-8 and latin1 fallback."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin1') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Failed to decode text file: {e}")
    except Exception as e:
        raise Exception(f"Failed to read text file: {e}")

def extract_text_from_image(file_path: str) -> str:
    """Extract text from image using OCR (Tesseract)."""
    try:
        # Open image with Pillow
        image = Image.open(file_path)
        
        # Convert to RGB if necessary (Tesseract works better with RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text using Tesseract OCR
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR failed: {e}")

def extract_text_from_file(file_path: str, content_type: str) -> str:
    """Main function to extract text from any supported file type."""
    if content_type == 'application/pdf':
        return extract_text_from_pdf(file_path)
    elif content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return extract_text_from_docx(file_path)
    elif content_type == 'text/plain':
        return extract_text_from_txt(file_path)
    elif content_type in ['image/png', 'image/jpeg', 'image/jpg']:
        return extract_text_from_image(file_path)
    else:
        raise Exception(f"Unsupported content type: {content_type}")

async def insert_file_to_supabase(user_id: str, filename: str, text_content: str, folder_id: str = None) -> str:
    """Insert file record into Supabase and return the file_id."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/files",
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "user_id": user_id,
                    "filename": filename,
                    "text_content": text_content,
                    "folder_id": folder_id
                }
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Supabase insert failed: {response.status_code} - {response.text}")
            
            # Get the actual file_id from the response
            data = response.json()
            if data and len(data) > 0:
                return data[0]["id"]
            else:
                raise Exception("No file ID returned from database")
            
    except Exception as e:
        raise Exception(f"Database error: {e}")

async def get_default_folder_id(user_id: str) -> str:
    """Get the default 'Untitled' folder ID for a user, creating it if it doesn't exist"""
    try:
        async with httpx.AsyncClient() as client:
            # 1. Try to find existing 'Untitled' folder
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/folders?user_id=eq.{user_id}&name=eq.Untitled",
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_KEY
                }
            )
            
            if response.status_code == 200 and response.json():
                return response.json()[0]["id"]
            
            # 2. If doesn't exist, create it
            print(f"Default 'Untitled' folder not found for user {user_id}, creating one...")
            create_response = await client.post(
                f"{settings.SUPABASE_URL}/rest/v1/folders",
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "user_id": user_id,
                    "name": "Untitled",
                    "color": "#E9D5FF"
                }
            )
            
            if create_response.status_code in [200, 201]:
                data = create_response.json()
                if data and len(data) > 0:
                    return data[0]["id"]
            
            raise Exception(f"Could not find or create default folder: {create_response.text}")
                
    except Exception as e:
        raise Exception(f"Error managing default folder: {e}")

@router.post("/upload_file")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file and extract text content.
    
    Supported file types:
    - PDF (.pdf)
    - DOCX (.docx) 
    - TXT (.txt)
    - Images (.png, .jpg, .jpeg)
    
    Maximum file size: 10MB
    """
    
    # Validate file type
    if file.content_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Supported types: PDF, DOCX, TXT, PNG, JPG, JPEG"
        )
    
    # Validate file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (>10MB). Please upload a smaller file."
        )
    
    # Create temporary file to save uploaded content
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=SUPPORTED_TYPES[file.content_type]) as temp_file:
            temp_file_path = temp_file.name
            
            # Read file content and check size
            content = await file.read()
            
            # Double-check file size after reading
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large (>10MB). Please upload a smaller file."
                )
            
            # Write content to temporary file
            temp_file.write(content)
            temp_file.flush()
        
        # Extract text from the file
        try:
            text_content = extract_text_from_file(temp_file_path, file.content_type)
            
            # Validate extracted text
            if not text_content or len(text_content.strip()) == 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Could not extract text from file. The file may be corrupted or contain no readable text."
                )
            
            # Trim extremely long text (optional - adjust based on your needs)
            if len(text_content) > 1000000:  # 1MB of text
                text_content = text_content[:1000000] + "\n\n[Text truncated due to length]"
            
        except Exception as e:
            error_msg = str(e)
            if "OCR failed" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Unreadable image - try a clearer scan or different image format."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Could not extract text from file. Please check if the file is corrupted or try a different file."
                )
        
        # Get default folder if no folder_id provided
        if not folder_id:
            folder_id = await get_default_folder_id(current_user.id)
        
        # Insert file record into Supabase
        try:
            file_id = await insert_file_to_supabase(
                user_id=current_user.id,
                filename=file.filename,
                text_content=text_content,
                folder_id=folder_id
            )
            
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "file_id": file_id,
                    "message": "File uploaded and text extracted successfully",
                    "filename": file.filename,
                    "text_length": len(text_content)
                }
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass  # Ignore cleanup errors

@router.get("/folder/{folder_id}")
async def get_files_by_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all files for a specific folder.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/files",
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "apikey": settings.SUPABASE_SERVICE_KEY,
                    "Content-Type": "application/json"
                },
                params={
                    "folder_id": f"eq.{folder_id}",
                    "user_id": f"eq.{current_user.id}",
                    "select": "id,filename,text_content,created_at",
                    "order": "created_at.desc"
                }
            )
            
            if response.status_code == 200:
                files = response.json()
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=files
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to fetch files"
                )
                
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching files: {str(e)}"
        )