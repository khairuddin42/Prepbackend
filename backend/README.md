# AI Exam-Prep Tutor - FastAPI Backend

A FastAPI backend with Supabase authentication for the AI Exam-Prep Tutor application.

## Features

- **User Authentication**: Signup and login endpoints using Supabase Auth
- **Protected Routes**: JWT token validation for secure endpoints
- **Async Support**: All endpoints are async for better performance
- **Environment Configuration**: Secure configuration using environment variables
- **CORS Support**: Configured for frontend integration

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and router configuration
│   ├── config.py            # Environment variables and settings
│   ├── deps.py              # Dependency injection for authentication
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Authentication endpoints (signup/login)
│       └── protected.py     # Protected endpoints example
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10 or higher
- Supabase project with Auth enabled
- **Tesseract OCR** (for image text extraction)

#### Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS (with Homebrew):**
```bash
brew install tesseract
```

**Windows:**
1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to PATH
3. Restart your terminal/IDE

### 2. Environment Setup

Create a `.env` file in the `backend` directory:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your Supabase credentials:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# FastAPI Configuration
FASTAPI_HOST=127.0.0.1
FASTAPI_PORT=8000

# Security (change in production)
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Required Python packages for file processing:**
- `pdfplumber` - PDF text extraction (preferred)
- `PyPDF2` - PDF text extraction (fallback)
- `python-docx` - DOCX file processing
- `pytesseract` - OCR for image text extraction
- `Pillow` - Image processing for OCR
- `supabase` - Supabase client for database operations

### 4. Run the Application

```bash
# Development mode with auto-reload
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Or run directly
python -m app.main
```

The API will be available at `http://127.0.0.1:8000`

### 5. API Documentation

- **Interactive Docs**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## API Endpoints

### File Upload Endpoints

#### POST `/files/upload_file`
Upload a file and extract text content for AI processing.

**Supported file types:**
- PDF (.pdf)
- DOCX (.docx)
- TXT (.txt)
- Images (.png, .jpg, .jpeg)

**Maximum file size:** 10MB

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request Body:**
```
file: <binary file data>
```

**Response (201):**
```json
{
  "file_id": "uuid-string",
  "message": "File uploaded and text extracted successfully",
  "filename": "lecture_notes.pdf",
  "text_length": 15420
}
```

**Error Responses:**
- `400`: Unsupported file type
- `413`: File too large (>10MB)
- `422`: Could not extract text (corrupted file or OCR failure)

### Authentication Endpoints

#### POST `/auth/signup`
Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201):**
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "message": "User created successfully"
}
```

#### POST `/auth/login`
Authenticate user and get access tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access_token": "jwt-token-string",
  "refresh_token": "refresh-token-string",
  "expires_in": 3600,
  "user_id": "uuid-string",
  "email": "user@example.com"
}
```

### Protected Endpoints

#### GET `/protected/ping`
Test endpoint that requires authentication.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "msg": "pong",
  "user": {
    "id": "uuid-string",
    "email": "user@example.com"
  }
}
```

## Testing with cURL

### 1. Upload a file

```bash
curl -X POST "http://127.0.0.1:8000/files/upload_file" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -F "file=@/path/to/your/lecture_notes.pdf"
```

**Expected Response:**
```json
{
  "file_id": "12345678-1234-1234-1234-123456789abc",
  "message": "File uploaded and text extracted successfully",
  "filename": "lecture_notes.pdf",
  "text_length": 15420
}
```

### 2. Signup a new user

```bash
curl -X POST "http://127.0.0.1:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

**Expected Response:**
```json
{
  "user_id": "12345678-1234-1234-1234-123456789abc",
  "email": "test@example.com",
  "message": "User created successfully"
}
```

### 3. Login with credentials

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "user_id": "12345678-1234-1234-1234-123456789abc",
  "email": "test@example.com"
}
```

### 4. Access protected endpoint

```bash
curl -X GET "http://127.0.0.1:8000/protected/ping" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Expected Response:**
```json
{
  "msg": "pong",
  "user": {
    "id": "12345678-1234-1234-1234-123456789abc",
    "email": "test@example.com"
  }
}
```

## Security Notes

- **Service Key**: The `SUPABASE_SERVICE_KEY` should only be used on the server side and never exposed to clients
- **Token Validation**: All protected endpoints validate JWT tokens with Supabase Auth
- **CORS**: Configure CORS origins appropriately for production
- **Environment Variables**: Never commit `.env` files to version control

## Frontend Integration

For frontend applications, the recommended flow is:

1. **Client-side**: Use `supabase-js` for user signup/login
2. **Token Storage**: Store the access token securely (e.g., in localStorage or httpOnly cookies)
3. **API Calls**: Include the access token in the `Authorization: Bearer <token>` header for protected endpoints

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `201`: Created (signup)
- `400`: Bad Request (validation errors)
- `401`: Unauthorized (invalid credentials/token)
- `409`: Conflict (user already exists)
- `503`: Service Unavailable (Supabase connection issues)

## Development

### Adding New Protected Endpoints

1. Create a new router in `app/routers/`
2. Import and use the `get_current_user` dependency
3. Include the router in `main.py`

Example:
```python
from fastapi import APIRouter, Depends
from app.deps import get_current_user, User

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}"}
```

### Environment Variables

Add new environment variables in `app/config.py`:

```python
class Settings(BaseSettings):
    # Existing variables...
    NEW_VARIABLE: str = "default_value"
```

## Production Deployment

1. Set `FASTAPI_HOST=0.0.0.0` for external access
2. Use a production ASGI server like Gunicorn with Uvicorn workers
3. Configure proper CORS origins
4. Use environment-specific Supabase projects
5. Implement proper logging and monitoring
