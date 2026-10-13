To create User Stories in Azure DevOps programmatically, you use the **Work Items - Create REST API**. Azure DevOps requires requests to use the **JSON Patch** format (`application/json-patch+json`).

---

### 1. API Endpoint Specification

* **HTTP Method:** `POST`
* **URL Format:**
```http
https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/$User%20Story?api-version=7.1
```

*(Note: If your process template uses "Product Backlog Item" or "User Story" depending on Agile/Scrum templates, change `$User%20Story` accordingly, e.g., `$Product%20Backlog%20Item`).*

---

### 2. Authentication Header

Azure DevOps REST APIs accept HTTP Basic Authentication using a **Personal Access Token (PAT)**.

* The username can be left blank (or set to any string), and the password is your PAT.
* Encode `":your_pat_here"` in Base64 to construct the header value:
```http
Authorization: Basic <Base64-Encoded-Empty-Username-and-PAT>
Content-Type: application/json-patch+json
```

---

### 3. Request Body (JSON Patch Format)

To specify fields like Title and Description, pass an array of JSON patch operations (`add`):

```json
[
  {
    "op": "add",
    "path": "/fields/System.Title",
    "value": "Your User Story Title Here"
  },
  {
    "op": "add",
    "path": "/fields/System.Description",
    "value": "Detailed description or acceptance criteria parsed from your spec."
  }
]
```

---

### 4. Complete cURL Example

You can test or trigger this directly from your terminal using `curl`:

```bash
curl --location --request POST 'https://dev.azure.com/govidev/Frameworks/_apis/wit/workitems/$User%20Story?api-version=7.1' \
--header 'Content-Type: application/json-patch+json' \
--header 'Authorization: Basic <YOUR_BASE64_ENCODED_PAT>' \
--data-raw '[
  {
    "op": "add",
    "path": "/fields/System.Title",
    "value": "Implement Authentication Module"
  },
  {
    "op": "add",
    "path": "/fields/System.Description",
    "value": "As a user, I want to log into the system securely."
  }
]'
```
