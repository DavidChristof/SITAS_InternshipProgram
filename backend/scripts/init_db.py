"""初始化数据库：建表 + 写入演示数据。

用法（项目根目录执行）：
    python -m backend.scripts.init_db
"""
import sys
from pathlib import Path

# 保证从项目根目录可导入 backend 包
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app import models  # noqa: F401,E402  注册全部模型
from backend.app.database import Base, SessionLocal, engine
from backend.app.models import Enterprise, Interviewer, Job, Question


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Enterprise).count() == 0:
            ent = Enterprise(
                name="示例科技有限公司",
                industry="互联网 / 人工智能",
                description="一家专注于 AI 产品的科技公司，面向校园招聘后端开发、算法、产品等岗位。",
            )
            db.add(ent)
            db.flush()

            job = Job(
                enterprise_id=ent.id,
                title="Python 后端开发工程师",
                description="负责公司 AI 产品后端服务的设计与开发，包括 REST API、数据服务和 AI 功能接入。",
                requirements="熟悉 Python、FastAPI/Django；了解 SQL 与数据库设计；对大模型应用感兴趣；有项目经验者优先。",
                skills="Python, FastAPI, SQL, LLM, Redis",
            )
            db.add(job)
            db.flush()

            db.add_all(
                [
                    Question(
                        job_id=job.id,
                        category="technical",
                        question="请简述 FastAPI 与 Flask 的区别。",
                        expected_points="异步支持,自动生成 OpenAPI 文档,基于 Pydantic 的类型校验,性能",
                        sample_answer="FastAPI 基于 ASGI 支持异步、自带 Swagger 文档、用 Pydantic 做请求校验，性能接近 Go；Flask 是同步 WSGI 框架，更轻量但需自行集成文档与校验。",
                        difficulty=2,
                    ),
                    Question(
                        job_id=job.id,
                        category="technical",
                        question="如何设计一个高并发的 REST API 查询接口？",
                        expected_points="缓存,索引,分页,异步,连接池",
                        sample_answer="加 Redis 缓存热点数据、数据库加索引并合理分页、用异步处理 IO 密集任务、配置连接池避免连接风暴。",
                        difficulty=3,
                    ),
                    Question(
                        job_id=job.id,
                        category="behavioral",
                        question="请举例说明你在团队项目中遇到分歧时是如何解决的。",
                        expected_points="STAR 结构,沟通,换位思考,结果",
                        sample_answer="（情境）小组开发时对技术选型有分歧；（任务）需要尽快确定方案；（行动）我整理两种方案的优劣对比，组织一次短会讨论并投票，保留可回退方案；（结果）达成一致并按时交付。",
                        difficulty=2,
                    ),
                    Question(
                        job_id=None,
                        category="self_intro",
                        question="请做一个 1 分钟自我介绍。",
                        expected_points="教育背景,项目经历,技能,求职动机",
                        sample_answer="面试官你好，我是XX大学软件工程专业应届生，主攻 Python 后端……",
                        difficulty=1,
                    ),
                ]
            )
            db.add(Interviewer(name="张老师", role="teacher", title="实习指导教师"))
        db.commit()
        print("[init_db] 建表完成，演示数据已写入 data/sitas.db")
    finally:
        db.close()


if __name__ == "__main__":
    main()
