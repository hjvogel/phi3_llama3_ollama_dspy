from langfuse import Langfuse
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal
import dspy

load_dotenv()


review_text = open("code_review.txt", "r").read()


class ReviewSummary(BaseModel):
    """Summary of code changes"""

    summary: str = Field(..., description="Summary of the changes in the code file.")


class ReviewSeverity(BaseModel):
    """Implied severity of the code changes"""

    severity: Literal["Critical", "Serious", "Minor"]
    explanations: list[str] = Field(
        ..., description="Explanation for severity selection"
    )

class ReviewCategory(BaseModel):
    """Categories of code changes."""

    categories: list[str] = Field(..., description="Categorize the changes of code given. Examples: readability, maintainability, security")
    explanations: str = Field(..., description="Explanation for category selections.")


class Review(BaseModel):
    """Review of New code in relation to Old code."""

    summary: ReviewSummary
    severity: ReviewSeverity
    category: ReviewCategory


class CodeReview(dspy.Signature):
    """Summary of code changes that outputs only valid json and nothing else."""

    code_changes: str = dspy.InputField()
    review: ReviewSummary = dspy.OutputField()


class RawSummary(dspy.Signature):
    """Summary of the code changes"""

    code_changes: str = dspy.InputField()
    review: str = dspy.OutputField()


class RawSeverity(dspy.Signature):
    """Severity of the code changes. Make sure to provide detailed explanation of the severity classification. Possible sevirities: Critical, Serious, Minor"""

    code_changes: str = dspy.InputField()
    severity: str = dspy.OutputField()
    explanation: str = dspy.OutputField()


class RawCategory(dspy.Signature):
    """Categories that changes of could be. Examples: readability, maintainability, security. Give explanations for each category that is chosen."""

    code_changes: str = dspy.InputField()
    categories: str = dspy.OutputField()
    explanations: str = dspy.OutputField()


class ExtractCategoryJson(dspy.Signature):
    """Extract the relevant information from the input into valid JSON. No other chat text allowed outside clean JSON format output, before or after.  Example output: '''{ 'valid_json': "some values"} ''' """

    input_text: str = dspy.InputField()
    valid_json: ReviewCategory = dspy.OutputField()


class ExtractSummaryJson(dspy.Signature):
    """Extract the relevant information from the input into valid JSON. Donot add any additional text before or after."""

    input_text: str = dspy.InputField()
    valid_json: ReviewSummary = dspy.OutputField()


class ExtractSeverityJson(dspy.Signature):
    """Extract the relevant information from the input into valid JSON. Donot add any additional text before or after."""

    input_text: str = dspy.InputField()
    valid_json: ReviewSeverity = dspy.OutputField()


class SummaryModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.raw_summary = dspy.Predict(RawSummary)
        self.structured_summary = dspy.TypedPredictor(ExtractSummaryJson)

    def forward(self, code_changes):
        raw = self.raw_summary(code_changes=code_changes)
        structured = self.structured_summary(input_text=raw.review)

        return structured


class SeverityModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.raw_severity = dspy.Predict(RawSeverity)
        self.structured_severity = dspy.TypedPredictor(ExtractSeverityJson)

    def forward(self, code_changes):
        raw = self.raw_severity(code_changes=code_changes)
        structured = self.structured_severity(
            input_text="\n".join([raw.severity, raw.explanation])
        )
        return structured
    
class CategoryModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.raw_category = dspy.Predict(RawCategory)
        self.structured_category = dspy.TypedPredictor(ExtractCategoryJson)

    def forward(self, code_changes):
        raw = self.raw_category(code_changes=code_changes)
        structured = self.structured_category(
            input_text="\n".join([raw.categories, raw.explanations])
        )
        return structured

#ol_model = "llama3"
#ol_model = "phi3"
ol_model = "phi3:instruct" 
#ol_model = "phi3:3.8b-mini-128k-instruct-q4_K_S" # crashes !!
#ol_model = "phi3:medium" # crashes
#ol_model = "phi3:14b-medium-128k-instruct-q4_0" # crashes !!
#ol_model = "deepseek-coder-v2" #  max 128k! needs timeout_s=300

client = dspy.OllamaLocal(model=ol_model, max_tokens=3000,temperature=0.002, timeout_s=300 )
dspy.configure(lm=client)

print("Model: " + ol_model)
print("SummaryModule - Results")
summary = SummaryModule()
summary_output = summary(code_changes=review_text)
print(summary_output)

print()
print("SeverityModule - Results")
severity = SeverityModule()
severity_output = severity(code_changes=review_text)
print(severity_output)

print()
print("CategoryModule - Results")
category = CategoryModule()
category_output = category(code_changes=review_text)
print(category_output)

client.history[-1]

