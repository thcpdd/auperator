"""记忆相关的数据模型"""

from pydantic import BaseModel, Field


class SaveMemoryRequest(BaseModel):
    """保存记忆请求"""

    problem: str = Field(..., description="问题描述")
    root_cause: str = Field(..., description="根本原因")
    solution: str = Field(..., description="解决方案")
    metadata: dict | None = Field(default=None, description="元数据")


class SaveMemoryResponse(BaseModel):
    """保存记忆响应"""

    memory_id: str = Field(..., description="记忆ID")
    message: str = Field(default="记忆已保存", description="响应消息")


class RetrieveMemoryRequest(BaseModel):
    """检索记忆请求"""

    problem_query: str = Field(..., description="问题描述查询")
    root_cause_query: str = Field(..., description="根本原因查询")
    solution_query: str = Field(..., description="解决方案查询")
    top_k: int = Field(default=3, ge=1, le=10, description="返回数量")
    weights: dict[str, float] | None = Field(
        default=None, description="section权重，格式: {problem: 1.2, root_cause: 1.8, solution: 2.0}"
    )


class MemorySection(BaseModel):
    """记忆section"""

    problem: str
    root_cause: str
    solution: str


class MemoryResponse(BaseModel):
    """记忆响应"""

    memory_id: str
    sections: MemorySection
    metadata: dict
    created_at: str
    score: float


class RetrieveMemoryResponse(BaseModel):
    """检索记忆响应"""

    memories: list[MemoryResponse]
    count: int
