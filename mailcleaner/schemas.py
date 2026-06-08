from pydantic import BaseModel, Field


class EmailPayload(BaseModel):
    emailId: str = Field(..., min_length=1)
    folderId: str = Field(..., min_length=1)
    base64Content: str = Field(..., min_length=1)


class CleanerJob(BaseModel):
    jobId: str = Field(..., min_length=1)
    resultQueue: str = Field(..., min_length=1)
    payload: EmailPayload


class QueuedJobResponse(BaseModel):
    jobId: str
    status: str
