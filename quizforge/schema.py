from typing import Literal

from pydantic import BaseModel, Field


class Option(BaseModel):
    key: Literal["A", "B", "C", "D"]
    text: str
    correct: bool
    why: str = Field(description="One line: why this option is right or wrong")


class ListQuestion(BaseModel):
    scenario: str = Field(description="A short situation of your own, then one clear question")
    options: list[Option] = Field(description="Four options, A to D, exactly one correct")
    quote: str = Field(description="One sentence copied word for word from the lesson")


class Question(BaseModel):
    scenario: str = Field(description="A short situation of your own, then one clear question")
    a: str
    b: str
    c: str
    d: str
    answer: Literal["A", "B", "C", "D"]
    why: str = Field(description="One line: why the answer is right")
    quote: str = Field(description="One sentence copied word for word from the lesson")


class ListQuestions(BaseModel):
    questions: list[ListQuestion]


class Questions(BaseModel):
    questions: list[Question]
