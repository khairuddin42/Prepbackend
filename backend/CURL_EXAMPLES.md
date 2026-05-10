# Quiz Generation Endpoint - cURL Examples

## Prerequisites
- Backend server running on `localhost:8000`
- Valid Supabase JWT token
- File uploaded to the system with a valid file_id

## 1. Test AI Quiz Generation (No Authentication Required)

```bash
curl -X POST "http://localhost:8000/test-ai-quiz" \
  -H "Content-Type: application/json" \
  -v
```

**Expected Response:**
```json
{
  "message": "AI quiz generation test completed",
  "original_text_length": 500,
  "questions": [
    {
      "question": "What is photosynthesis?",
      "options": [
        "Process by which plants convert light energy to chemical energy",
        "Process by which animals digest food",
        "Process by which cells divide",
        "Process by which DNA replicates"
      ],
      "answer_index": 0
    }
  ],
  "question_count": 4,
  "is_ai_generated": true
}
```

## 2. Generate Quiz for File (Authentication Required)

```bash
# Replace YOUR_JWT_TOKEN with actual Supabase JWT token
# Replace YOUR_FILE_ID with actual file ID

curl -X POST "http://localhost:8000/quiz/YOUR_FILE_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -v
```

**Expected Response (New Quiz):**
```json
{
  "quiz_id": "123e4567-e89b-12d3-a456-426614174000",
  "questions": [
    {
      "question": "What is the main topic discussed?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer_index": 1
    },
    {
      "question": "Which statement is true?",
      "options": ["A", "B", "C", "D"],
      "answer_index": 0
    }
  ],
  "cached": false,
  "filename": "lecture_notes.pdf",
  "question_count": 4
}
```

**Expected Response (Cached Quiz):**
```json
{
  "quiz_id": "123e4567-e89b-12d3-a456-426614174000",
  "questions": [...],
  "cached": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

## 3. Delete Quiz

```bash
curl -X DELETE "http://localhost:8000/quiz/YOUR_FILE_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -v
```

**Expected Response:**
```json
{
  "message": "Quiz deleted successfully. Call quiz endpoint again to generate a new quiz.",
  "file_id": "YOUR_FILE_ID"
}
```

## 4. Test Error Scenarios

### Invalid Authentication
```bash
curl -X POST "http://localhost:8000/quiz/YOUR_FILE_ID" \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -v
```

**Expected Response:**
```json
{
  "detail": "Invalid authentication token"
}
```

### File Not Found
```bash
curl -X POST "http://localhost:8000/quiz/invalid-file-id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -v
```

**Expected Response:**
```json
{
  "detail": "File not found or access denied"
}
```

### No Authentication
```bash
curl -X POST "http://localhost:8000/quiz/YOUR_FILE_ID" \
  -H "Content-Type: application/json" \
  -v
```

**Expected Response:**
```json
{
  "detail": "Not authenticated"
}
```

## 5. Complete Test Workflow

```bash
#!/bin/bash

# Set your variables
JWT_TOKEN="your-supabase-jwt-token"
FILE_ID="your-file-id"

echo "🧪 Testing Quiz Generation Endpoint"
echo "=================================="

# Test 1: AI Quiz Generation (no auth)
echo "1. Testing AI Quiz Generation..."
curl -X POST "http://localhost:8000/test-ai-quiz" \
  -H "Content-Type: application/json" \
  -s | jq '.'

echo -e "\n"

# Test 2: Generate Quiz
echo "2. Generating Quiz for File..."
curl -X POST "http://localhost:8000/quiz/$FILE_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.'

echo -e "\n"

# Test 3: Generate Quiz Again (should be cached)
echo "3. Generating Quiz Again (should be cached)..."
curl -X POST "http://localhost:8000/quiz/$FILE_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.'

echo -e "\n"

# Test 4: Delete Quiz
echo "4. Deleting Quiz..."
curl -X DELETE "http://localhost:8000/quiz/$FILE_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.'

echo -e "\n"

# Test 5: Generate Quiz After Deletion
echo "5. Generating Quiz After Deletion..."
curl -X POST "http://localhost:8000/quiz/$FILE_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.'

echo -e "\n"
echo "✅ Test Workflow Completed!"
```

## 6. Using with jq for Pretty Output

```bash
# Install jq if not already installed
# macOS: brew install jq
# Ubuntu: sudo apt-get install jq

# Pretty print JSON responses
curl -X POST "http://localhost:8000/test-ai-quiz" \
  -H "Content-Type: application/json" \
  -s | jq '.'
```

## 7. Save Response to File

```bash
# Save quiz response to file
curl -X POST "http://localhost:8000/quiz/YOUR_FILE_ID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.' > quiz_response.json

echo "Quiz saved to quiz_response.json"
```

## 8. Test with Different File Types

```bash
# Test with PDF file
curl -X POST "http://localhost:8000/quiz/pdf-file-id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.'

# Test with DOCX file
curl -X POST "http://localhost:8000/quiz/docx-file-id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.'

# Test with TXT file
curl -X POST "http://localhost:8000/quiz/txt-file-id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -s | jq '.'
```

## Notes

- Replace `YOUR_JWT_TOKEN` with your actual Supabase JWT token
- Replace `YOUR_FILE_ID` with your actual file ID
- The `-v` flag shows verbose output for debugging
- The `-s` flag suppresses progress meter
- Use `jq` for pretty JSON formatting
- Quiz generation may take 10-30 seconds for first generation
- Subsequent calls return cached results immediately
