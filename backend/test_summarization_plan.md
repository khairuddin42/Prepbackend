# Unit Test Plan for Summarization Endpoint

## Test Setup
1. Install test dependencies: `pip install pytest pytest-asyncio httpx`
2. Set up test database with sample data
3. Mock authentication for testing

## Test Cases

### Test 1: First-time Summary Generation
**Scenario**: Upload a file and generate summary for the first time
**Steps**:
1. Upload a test file (e.g., short lecture notes)
2. Call `POST /ai/summarize/{file_id}` with valid auth token
3. Verify response contains new summary
4. Check database for saved summary record

**Expected Response**:
```json
{
  "summary_id": "550e8400-e29b-41d4-a716-446655440000",
  "summary_text": "This document covers the fundamental concepts of photosynthesis, including the light-dependent and light-independent reactions. The process converts light energy into chemical energy through chlorophyll pigments. Key components include water, carbon dioxide, and sunlight as inputs, producing glucose and oxygen as outputs.",
  "cached": false,
  "filename": "biology_notes.pdf"
}
```

### Test 2: Cached Summary Retrieval
**Scenario**: Call summarize endpoint again for same file
**Steps**:
1. Use same file_id from Test 1
2. Call `POST /ai/summarize/{file_id}` again
3. Verify cached summary is returned
4. Verify no new database record is created

**Expected Response**:
```json
{
  "summary_id": "550e8400-e29b-41d4-a716-446655440000",
  "summary_text": "This document covers the fundamental concepts of photosynthesis, including the light-dependent and light-independent reactions. The process converts light energy into chemical energy through chlorophyll pigments. Key components include water, carbon dioxide, and sunlight as inputs, producing glucose and oxygen as outputs.",
  "cached": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Test 3: File Not Found
**Scenario**: Try to summarize non-existent file
**Steps**:
1. Call `POST /ai/summarize/invalid-file-id` with valid auth
2. Verify 404 error response

**Expected Response**:
```json
{
  "detail": "File not found or access denied"
}
```

### Test 4: Unauthorized Access
**Scenario**: Try to summarize file owned by different user
**Steps**:
1. Upload file with User A
2. Call summarize endpoint with User B's token
3. Verify 404 error (security through obscurity)

**Expected Response**:
```json
{
  "detail": "File not found or access denied"
}
```

### Test 5: Empty Text Content
**Scenario**: File with no extractable text
**Steps**:
1. Upload corrupted/empty file
2. Call summarize endpoint
3. Verify 422 error

**Expected Response**:
```json
{
  "detail": "File has no extractable text"
}
```

### Test 6: Large Text Chunking
**Scenario**: File with text longer than chunk threshold
**Steps**:
1. Upload file with 10,000+ character text
2. Call summarize endpoint
3. Verify text is chunked and combined properly
4. Check summary quality

**Expected Response**:
```json
{
  "summary_id": "550e8400-e29b-41d4-a716-446655440000",
  "summary_text": "This comprehensive document covers multiple topics including advanced calculus concepts, statistical analysis methods, and machine learning algorithms. The material progresses from basic mathematical foundations to complex algorithmic implementations, providing both theoretical understanding and practical applications.",
  "cached": false,
  "filename": "advanced_math_notes.pdf"
}
```

### Test 7: AI Service Error
**Scenario**: Model fails to generate summary
**Steps**:
1. Mock model failure
2. Call summarize endpoint
3. Verify 502 error with friendly message

**Expected Response**:
```json
{
  "detail": "AI service error - unable to generate summary at this time"
}
```

## Test Implementation Example

```python
import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    # Mock authentication headers
    return {"Authorization": "Bearer mock-token"}

@pytest.fixture
def sample_file_id():
    # Mock file ID from uploaded file
    return "550e8400-e29b-41d4-a716-446655440001"

def test_first_time_summary_generation(auth_headers, sample_file_id):
    """Test generating summary for the first time."""
    response = client.post(
        f"/ai/summarize/{sample_file_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "summary_id" in data
    assert "summary_text" in data
    assert data["cached"] == False
    assert len(data["summary_text"]) > 50  # Reasonable summary length

def test_cached_summary_retrieval(auth_headers, sample_file_id):
    """Test retrieving cached summary."""
    # First call
    response1 = client.post(
        f"/ai/summarize/{sample_file_id}",
        headers=auth_headers
    )
    
    # Second call (should be cached)
    response2 = client.post(
        f"/ai/summarize/{sample_file_id}",
        headers=auth_headers
    )
    
    assert response2.status_code == 200
    data = response2.json()
    assert data["cached"] == True
    assert data["summary_id"] == response1.json()["summary_id"]

def test_file_not_found(auth_headers):
    """Test handling of non-existent file."""
    response = client.post(
        "/ai/summarize/non-existent-id",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_empty_text_content(auth_headers, empty_file_id):
    """Test handling of file with no text."""
    response = client.post(
        f"/ai/summarize/{empty_file_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 422
    assert "no extractable text" in response.json()["detail"]
```

## Performance Considerations

### Chunking Strategy
- **Small files** (< 3000 chars): Single chunk, direct summarization
- **Medium files** (3000-6000 chars): 2 chunks, combine summaries
- **Large files** (> 6000 chars): Multiple chunks, hierarchical summarization

### Model Selection
- **Primary**: `facebook/bart-large-cnn` (good balance of speed/quality)
- **Fallback**: `t5-small` (faster, lower quality)
- **API**: Hugging Face Inference API (when local fails)

### Caching Benefits
- **First call**: ~5-15 seconds (model processing)
- **Cached call**: ~100-200ms (database lookup)
- **Memory usage**: Minimal (only summary text stored)

## Error Handling Matrix

| Error Type | HTTP Code | Response Message | User Action |
|------------|-----------|------------------|-------------|
| File not found | 404 | "File not found or access denied" | Check file ID |
| Empty text | 422 | "File has no extractable text" | Upload different file |
| AI service down | 502 | "AI service error - unable to generate summary at this time" | Retry later |
| Auth failure | 401 | "Invalid authentication token" | Re-login |
| Server error | 500 | "Summarization failed: [details]" | Contact support |

## Integration Testing

### End-to-End Flow
1. **Upload** → File stored with extracted text
2. **Summarize** → AI processes text, saves summary
3. **Retrieve** → Cached summary returned instantly
4. **Delete** → File and associated summary removed

### Database Consistency
- Summary records properly linked to files
- Cascade deletion works correctly
- User isolation maintained (RLS policies)
- Indexes support fast lookups

This test plan ensures the summarization endpoint works correctly across all scenarios while maintaining security, performance, and user experience standards.
