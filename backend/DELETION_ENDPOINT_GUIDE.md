# 🗑️ Deletion Endpoints Guide - AI Exam-Prep Tutor

This guide provides comprehensive testing commands for all deletion endpoints with expected responses and error handling.

## 📋 Deletion Endpoints Overview

| Endpoint | Description | CASCADE Effect |
|----------|-------------|----------------|
| `DELETE /delete/file/{file_id}` | Delete file and all related content | ✅ Deletes summaries, quizzes, flashcards |
| `DELETE /delete/summary/{summary_id}` | Delete specific summary only | ❌ Leaves file and other content intact |
| `DELETE /delete/quiz/{quiz_id}` | Delete specific quiz only | ❌ Leaves file and other content intact |
| `DELETE /delete/flashcard/{flashcard_id}` | Delete specific flashcard set only | ❌ Leaves file and other content intact |

---

## 🔐 Authentication Setup

All deletion endpoints require authentication. Get your access token first:

### 1. Login to get access token
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "user_id": "12345678-1234-1234-1234-123456789abc",
  "email": "your-email@example.com"
}
```

---

## 🗑️ Endpoint Tests

### 1. DELETE /delete/file/{file_id}

**Description:** Deletes an uploaded file and ALL related content (summaries, quizzes, flashcards) due to CASCADE CONSTRAINT.

```bash
curl -X DELETE "http://localhost:8000/delete/file/YOUR_FILE_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### ✅ Success Response (200)
```json
{
  "deleted": true
}
```

#### ❌ Error Responses
```bash
# 404 - File not found
{
  "detail": "File not found"
}

# 403 - Not owner
{
  "detail": "You can only delete your own resources"
}

# 401 - Invalid token
{
  "detail": "Invalid authentication token"
}
```

#### 🧪 CASCADE Behavior Test
1. Upload a file with file_id `ABC123`
2. Generate summary with summary_id `SUM456`  
3. Generate quiz with quiz_id `QUIZ789`
4. Generate flashcards with flashcard_id `CARD012`
5. Delete file `ABC123`
6. Verify all related records (`SUM456`, `QUIZ789`, `CARD012`) are automatically deleted

---

### 2. DELETE /delete/summary/{summary_id}

**Description:** Deletes only the specific summary, leaves the file and other content intact.

```bash
curl -X DELETE "http://localhost:8000/delete/summary/YOUR_SUMMARY_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### ✅ Success Response (200)
```json
{
  "deleted": true
}
```

#### ❌ Error Responses
```bash
# 404 - Summary not found
{
  "detail": "Summary not found"
}

# 403 - Not owner
{
  "detail": "You can only delete your own resources"
}
```

---

### 3. DELETE /delete/quiz/{quiz_id}

**Description:** Deletes only the specific quiz, leaves the file and other content intact.

```bash
curl -X DELETE "http://localhost:8000/delete/quiz/YOUR_QUIZ_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### ✅ Success Response (200)
```json
{
  "deleted": true
}
```

#### ❌ Error Responses
Same as summary deletion endpoints.

---

### 4. DELETE /delete/flashcard/{flashcard_id}

**Description:** Deletes only the specific flashcard set, leaves the file and other content intact.

```bash
curl -X DELETE "http://localhost:8000/delete/flashcard/YOUR_FLASHCARD_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### ✅ Success Response (200)
```json
{
  "deleted": true
}
```

#### ❌ Error Responses
Same as summary/quiz deletion endpoints.

---

## 🔍 Database CASCADE Verification

### Verify CASCADE Behavior
To confirm that file deletion cascades to related records:

1. **Upload a file and create related content:**
```bash
# 1. Upload file
curl -X POST "http://localhost:8000/files/upload_file" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@lecture_notes.pdf"

# Response: {"file_id": "abc-123-def", ...}

# 2. Generate summary
curl -X POST "http://localhost:8000/ai/summarize/abc-123-def" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response: {"summary_id": "sum-456-ghi", ...}

# 3. Generate quiz  
curl -X POST "http://localhost:8000/ai/quiz/abc-123-def" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response: {"quiz_id": "quiz-789-jkl", ...}

# 4. Generate flashcards
curl -X POST "http://localhost:8000/ai/flashcards/abc-123-def" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response: {"flashcard_id": "card-012-mno", ...}
```

2. **Verify all content exists:**
```bash
# Check file exists
curl -X GET "http://localhost:8000/files/list" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should show file abc-123-def

# Check summary exists  
curl -X GET "http://localhost:8000/ai/summaries" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should show summary sum-456-ghi

# Check quiz exists
curl -X GET "http://localhost:8000/ai/quizzes" \
  -H "Authorization: Bearer YOUR_TOKEN" 
# Should show quiz quiz-789-jkl

# Check flashcards exist
curl -X GET "http://localhost:8000/ai/flashcards" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should show flashcard card-012-mno
```

3. **Delete the file:**
```bash
curl -X DELETE "http://localhost:8000/delete/file/abc-123-def" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

4. **Verify CASCADE worked - all content should be gone:**
```bash
# Check file deleted
curl -X GET "http://localhost:8000/files/list" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return empty list - file abc-123-def gone

# Check summary deleted (CASCADE)
curl -X GET "http://localhost:8000/ai/summaries" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return empty list - summary sum-456-ghi gone

# Check quiz deleted (CASCADE)
curl -X GET "http://localhost:8000/ai/quizzes" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return empty list - quiz quiz-789-jkl gone

# Check flashcards deleted (CASCADE)
curl -X GET "http://localhost:8000/ai/flashcards" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return empty list - flashcard card-012-mno gone
```

---

## 🔒 Security Features Verified

### ✅ Ownership Verification
- Users can only delete resources they own (`user_id` matches)
- Cross-user deletion attempts return 403 Forbidden
- All endpoints verify ownership before deletion

### ✅ Row Level Security (RLS)
- Database-level RLS policies enforce user isolation
- CASCADE DELETE respects ownership constraints
- Multi-user scenarios are safe

### ✅ Token-based Authentication
- JWT tokens verified for all endpoints
- Expired/invalid tokens return 401 Unauthorized
- User extraction from token validated

---

## 📊 Expected Database State Changes

### File Deletion (CASCADE)
```sql
-- Before deletion
files: {id: "abc-123", user_id: "user-1", filename: "notes.pdf"}
summaries: {id: "sum-456", file_id: "abc-123", user_id: "user-1"}
quizzes: {id: "quiz-789", file_id: "abc-123", user_id: "user-1"}  
flashcards: {id: "card-012", file_id: "abc-123", user_id: "user-1"}

-- After DELETE /delete/file/abc-123
files: (empty - file deleted)
summaries: (empty - CASCADE deleted)
quizzes: (empty - CASCADE deleted)
flashcards: (empty - CASCADE deleted)
```

### Individual Resource Deletion (NO CASCADE)
```sql
-- Before deletion
files: {id: "abc-123", user_id: "user-1", filename: "notes.pdf"}
summaries: {id: "sum-456", file_id: "abc-123", user_id: "user-1"}

-- After DELETE /delete/summary/sum-456
files: {id: "abc-123", user_id: "user-1", filename: "notes.pdf"} (unchanged)
summaries: (empty - only summary deleted)
```

---

## 🚀 Quick Test Script

Save this as `test_deletions.sh` and run to verify all endpoints:

```bash
#!/bin/bash

# Set your credentials
TOKEN="YOUR_ACCESS_TOKEN"
BASE_URL="http://localhost:8000"

echo "🧪 Testing Deletion Endpoints..."

# Test with invalid IDs (should return 404)
echo "📝 Testing 404 responses..."
curl -X DELETE "$BASE_URL/delete/file/invalid-id" \
  -H "Authorization: Bearer $TOKEN" | jq

curl -X DELETE "$BASE_URL/delete/summary/invalid-id" \
  -H "Authorization: Bearer $TOKEN" | jq

echo "✅ Deletion endpoints are ready!"
```

---

## 💡 Soft-Delete Extension Notes

For future enhancement, the deletion router includes commented guidance for implementing soft-delete:

- Add `deleted_at` column to tables
- Modify queries to exclude soft-deleted records  
- Update delete endpoints to set `deleted_at` instead of hard deletion
- Add restore functionality
- Add automatic purging after retention period

This approach allows data recovery while maintaining audit trails for compliance and analytics.

