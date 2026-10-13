In Azure DevOps, **Test Cases** are treated as a specialized type of Work Item (`Test Case`). Therefore, you create them using the standard **Work Items - Create REST API** by targeting `$Test%20Case` in the endpoint URL.

Test steps are embedded into a specific internal field called `Microsoft.VSTS.TCM.Steps` using an XML format.

---

### 1. API Endpoint Specification

* **HTTP Method:** `POST`
* **URL Format:**
```http
https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/$Test%20Case?api-version=7.1

```


* **For your project:**
```http
https://dev.azure.com/govidev/Frameworks/_apis/wit/workitems/$Test%20Case?api-version=7.1

```



---

### 2. Request Headers

* **Authorization:** `Basic <Base64-Encoded-Empty-Username-and-PAT>`
* **Content-Type:** `application/json-patch+json`

---

### 3. Request Body (JSON Patch with Test Steps)

To add test steps, you provide an XML structure inside the `/fields/Microsoft.VSTS.TCM.Steps` path.

```json
[
  {
    "op": "add",
    "path": "/fields/System.Title",
    "value": "Verify user login with valid credentials"
  },
  {
    "op": "add",
    "path": "/fields/Microsoft.VSTS.Common.Priority",
    "value": 1
  },
  {
    "op": "add",
    "path": "/fields/Microsoft.VSTS.TCM.Steps",
    "value": "<steps id=\"0\" last=\"2\"><step id=\"2\" type=\"ActionStep\"><parameterizedString isformatted=\"true\">Open the application login page</parameterizedString><description/></step><step id=\"3\" type=\"ValidateStep\"><parameterizedString isformatted=\"true\">Enter valid username and password and click login</parameterizedString><parameterizedString isformatted=\"true\">User should be redirected to the dashboard successfully</parameterizedString></step></steps>"
  }
]

```

---

### 4. Complete cURL Example

You can execute this command directly in your terminal to create a Test Case with explicit steps:

```bash
curl --location --request POST 'https://dev.azure.com/govidev/Frameworks/_apis/wit/workitems/$Test%20Case?api-version=7.1' \
--header 'Content-Type: application/json-patch+json' \
--header 'Authorization: Basic <YOUR_BASE64_ENCODED_PAT>' \
--data-raw '[
  {
    "op": "add",
    "path": "/fields/System.Title",
    "value": "Verify user login with valid credentials"
  },
  {
    "op": "add",
    "path": "/fields/Microsoft.VSTS.TCM.Steps",
    "value": "<steps id=\"0\" last=\"2\"><step id=\"2\" type=\"ActionStep\"><parameterizedString isformatted=\"true\">Open the login portal</parameterizedString><description/></step><step id=\"3\" type=\"ValidateStep\"><parameterizedString isformatted=\"true\">Provide valid credentials and submit</parameterizedString><parameterizedString isformatted=\"true\">Dashboard page loads properly</parameterizedString></step></steps>"
  }
]'

```