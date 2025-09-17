Extract structured follow-ups from the discharge text as JSON that conforms to:

{
  "followUps": [
    { "category": "lab|med|visit|other",
      "title": "string",
      "dueDate": "YYYY-MM-DD|null",
      "priority": "low|normal|high" }
  ]
}
Return *only* the JSON object.
