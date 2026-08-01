# AI_NOTES.md

# AI Usage Notes

## AI Tools Used

- Claude Code
- ChatGPT (GPT-5.5)

I used AI as a development assistant throughout this assignment. AI helped generate the initial project structure, implement parts of the FastAPI application, suggest improvements, generate test cases, and review the final code.

All generated code was reviewed, executed, tested, and verified before submission.

---

## What AI Generated

AI assisted with:

- FastAPI project scaffold
- Folder structure
- Pydantic models and schemas
- JSON storage implementation
- Service layer
- API routes
- Error handling
- Unit tests
- README draft
- Initial AI_NOTES draft

---

## What I Reviewed and Modified

I reviewed the generated implementation and made corrections where necessary.

Examples include:

- Updated the project structure to match the assignment requirements (`src/` layout).
- Corrected the expense fields to match the specification (`id`, `title`, `amount`, `category`, `date`).
- Reviewed validation logic and error handling.
- Verified JSON storage behavior.
- Improved API documentation.
- Updated dependency versions after testing in a clean virtual environment.
- Fixed issues identified during testing.

---

## Validation Performed

Before submission I personally:

- Ran the application locally using Uvicorn.
- Tested all API endpoints through Swagger UI and HTTP requests.
- Verified create, list, filter, summary, retrieve, and delete operations.
- Tested validation failures and error responses.
- Executed the complete pytest suite successfully.
- Verified the project in a clean virtual environment using the installation instructions from the README.

---

## AI Suggestions I Rejected

Some AI-generated suggestions were intentionally not used.

Examples include:

- Additional fields that were not part of the assignment.
- A fixed category enumeration, which I replaced with normalized free-form categories.
- Project structures that did not match the required submission format.

These decisions were made to keep the implementation aligned with the assignment requirements.

---

## Final Review

Before submission I reviewed the generated code, verified that it satisfied the assignment requirements, and ensured that all tests passed successfully.