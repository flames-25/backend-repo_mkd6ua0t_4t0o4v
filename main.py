import os
from datetime import date, datetime
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Tasks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Models -----
Status = Literal["todo", "in_progress", "done"]
Priority = Literal["low", "medium", "high"]

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = ""
    status: Status = "todo"
    priority: Priority = "medium"
    due_date: Optional[date] = None
    tags: List[str] = []

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    due_date: Optional[date] = None
    tags: Optional[List[str]] = None

class Task(TaskBase):
    id: str
    created_at: datetime
    updated_at: datetime

# ----- Mock Store -----
_tasks: List[Task] = []

# Seed mock data
from uuid import uuid4

def seed_mock():
    global _tasks
    if _tasks:
        return
    today = date.today()
    samples = [
        {
            "title": "设计任务卡片样式",
            "description": "确定卡片信息层级与交互状态",
            "status": "todo",
            "priority": "high",
            "due_date": today,
            "tags": ["design", "ui"]
        },
        {
            "title": "实现看板拖拽",
            "description": "列内排序 + 跨列移动",
            "status": "in_progress",
            "priority": "medium",
            "due_date": today.replace(day=min(28, today.day + 2)),
            "tags": ["frontend"]
        },
        {
            "title": "编写单元测试",
            "description": "覆盖任务 CRUD 核心逻辑",
            "status": "todo",
            "priority": "low",
            "due_date": None,
            "tags": ["testing"]
        },
        {
            "title": "部署预览环境",
            "description": "配置 CI 并发布",
            "status": "done",
            "priority": "medium",
            "due_date": today.replace(day=max(1, today.day - 3)),
            "tags": ["devops"]
        },
    ]
    now = datetime.utcnow()
    for s in samples:
        _tasks.append(Task(id=str(uuid4()), created_at=now, updated_at=now, **s))

seed_mock()

# ----- Helpers -----

def find_task(task_id: str) -> int:
    for i, t in enumerate(_tasks):
        if t.id == task_id:
            return i
    return -1

# ----- Routes -----

@app.get("/")
def root():
    return {"message": "Tasks API Running"}

@app.get("/api/tasks", response_model=List[Task])
def list_tasks(
    q: Optional[str] = Query(None, description="Search text in title/description"),
    status: Optional[Status] = Query(None),
    priority: Optional[Priority] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by due date month"),
    year: Optional[int] = Query(None, ge=1970, le=2100, description="Filter by due date year"),
    tag: Optional[str] = Query(None, description="Filter by single tag"),
):
    results = _tasks
    if q:
        ql = q.lower()
        results = [t for t in results if ql in t.title.lower() or (t.description or "").lower().find(ql) != -1]
    if status:
        results = [t for t in results if t.status == status]
    if priority:
        results = [t for t in results if t.priority == priority]
    if tag:
        results = [t for t in results if tag in t.tags]
    if month:
        results = [t for t in results if t.due_date and t.due_date.month == month and (not year or t.due_date.year == year)]
    elif year:
        results = [t for t in results if t.due_date and t.due_date.year == year]
    return results

@app.post("/api/tasks", response_model=Task)
def create_task(payload: TaskCreate):
    now = datetime.utcnow()
    new = Task(id=str(uuid4()), created_at=now, updated_at=now, **payload.dict())
    _tasks.append(new)
    return new

@app.get("/api/tasks/{task_id}", response_model=Task)
def get_task(task_id: str):
    idx = find_task(task_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Task not found")
    return _tasks[idx]

@app.put("/api/tasks/{task_id}", response_model=Task)
@app.patch("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: str, payload: TaskUpdate):
    idx = find_task(task_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Task not found")
    stored = _tasks[idx]
    data = payload.dict(exclude_unset=True)
    updated = stored.copy(update={**data, "updated_at": datetime.utcnow()})
    _tasks[idx] = updated
    return updated

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    idx = find_task(task_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Task not found")
    _tasks.pop(idx)
    return {"ok": True}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Simple health endpoint (DB intentionally unused for mock data)."""
    return {
        "backend": "✅ Running",
        "database": "ℹ️ Skipped (using mock data)",
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
