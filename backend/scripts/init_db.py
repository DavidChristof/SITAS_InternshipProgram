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
            # ===== 演示企业（5 家）=====
            ent_data = [
                ("示例科技有限公司", "互联网 / 人工智能",
                 "一家专注于 AI 产品的科技公司，面向校园招聘后端开发、算法、产品等岗位。"),
                ("星辰科技有限公司", "互联网 / 电商 SaaS",
                 "面向电商零售行业提供 SaaS 平台与数字营销解决方案，技术栈以微服务为主。"),
                ("云帆数据科技有限公司", "大数据 / 数据服务",
                 "企业级大数据分析与数据中台建设，服务金融、零售行业客户。"),
                ("极光智能科技", "人工智能",
                 "人工智能算法研发与行业解决方案，覆盖视觉、NLP 与多模态，配备大模型算力资源。"),
                ("青藤软件", "软件服务",
                 "企业级软件产品与定制开发，覆盖办公协同、低代码平台，重视代码质量与测试规范。"),
            ]
            ents: list[Enterprise] = []
            for name, industry, desc in ent_data:
                e = Enterprise(name=name, industry=industry, description=desc)
                db.add(e)
                ents.append(e)
            db.flush()

            # ===== 演示岗位（6 个，挂靠各企业）=====
            job_data = [
                (ents[0], "Python 后端开发工程师",
                 "负责公司 AI 产品后端服务的设计与开发，包括 REST API、数据服务和 AI 功能接入。",
                 "熟悉 Python、FastAPI/Django；了解 SQL 与数据库设计；对大模型应用感兴趣；有项目经验者优先。",
                 "Python, FastAPI, SQL, LLM, Redis"),
                (ents[1], "Java 后端开发工程师",
                 "负责核心业务系统的后端服务设计与开发，包括 REST API、数据库建模与微服务拆分。",
                 "熟悉 Java、Spring Boot/Spring Cloud；掌握 MySQL 与索引优化；了解 Redis 缓存与消息队列。",
                 "Java, Spring Boot, MySQL, Redis"),
                (ents[4], "前端开发工程师",
                 "负责 Web 产品的前端开发与组件库建设，基于 Vue/React 实现高质量交互页面。",
                 "熟悉 HTML/CSS/JavaScript，掌握 Vue 或 React；了解工程化与性能优化；有项目经验者优先。",
                 "HTML, CSS, JavaScript, Vue"),
                (ents[4], "测试开发工程师",
                 "负责自动化测试体系建设，包括接口测试、UI 自动化与质量闭环。",
                 "熟悉 Python 或 Java；了解 pytest/TestNG、Selenium 等测试框架；具备接口测试经验。",
                 "Python, 自动化测试, pytest, CI/CD"),
                (ents[2], "数据分析师",
                 "负责业务数据的清洗、分析与可视化，输出经营分析报告与决策建议。",
                 "掌握 SQL 与 Python；熟悉数据分析方法与可视化工具；了解统计基础与 A/B 测试。",
                 "Python, SQL, 数据分析, 可视化"),
                (ents[3], "算法工程师",
                 "负责机器学习/深度学习模型的研发与落地，参与大模型应用与检索增强方向。",
                 "熟悉 Python、PyTorch 或 TensorFlow；掌握机器学习基础；了解 NLP/大模型与 RAG 优先。",
                 "Python, 机器学习, 深度学习, NLP, RAG"),
            ]
            jobs: list[Job] = []
            for ent, title, desc, req, skills in job_data:
                j = Job(enterprise_id=ent.id, title=title, description=desc,
                        requirements=req, skills=skills)
                db.add(j)
                jobs.append(j)
            db.flush()

            # ===== 后台题库（21 道，覆盖各岗位与环节）=====
            q_data = [
                # --- Python 后端 ---
                (jobs[0], "technical", "请简述 FastAPI 与 Flask 的区别。",
                 "异步支持,自动生成 OpenAPI 文档,基于 Pydantic 的类型校验,性能",
                 "FastAPI 基于 ASGI 支持异步、自带 Swagger 文档、用 Pydantic 做请求校验，性能接近 Go；Flask 是同步 WSGI 框架，更轻量但需自行集成文档与校验。", 2),
                (jobs[0], "technical", "如何设计一个高并发的 REST API 查询接口？",
                 "缓存,索引,分页,异步,连接池",
                 "加 Redis 缓存热点数据、数据库加索引并合理分页、用异步处理 IO 密集任务、配置连接池避免连接风暴。", 3),
                (jobs[0], "technical", "请解释 Redis 缓存穿透、击穿、雪崩的区别与应对。",
                 "穿透,击穿,雪崩,布隆过滤器,互斥锁",
                 "穿透指查不存在的数据，用布隆过滤器或空值缓存；击穿指热点 key 过期，用互斥锁或逻辑过期；雪崩指大量 key 同时过期，用随机过期时间 + 熔断降级。", 3),
                (jobs[0], "project", "请讲一次你做过的接口性能优化过程。",
                 "量化指标,定位瓶颈,索引,缓存,效果验证",
                 "用慢查询定位未走索引的 SQL 并建联合索引，热点数据加 Redis 缓存并处理穿透，最终接口耗时从 1 秒降到 500ms。", 3),
                # --- Java 后端 ---
                (jobs[1], "technical", "请解释 Spring Boot 的自动装配原理。",
                 "自动装配,条件注解,starter,依赖注入",
                 "启动时通过 spring.factories 加载自动配置类，配合 @ConditionalOnClass 等条件注解按依赖装配 Bean；依赖注入实现控制反转，降低耦合。", 3),
                (jobs[1], "technical", "JVM 运行时内存区域如何划分？",
                 "堆,栈,方法区,程序计数器,GC",
                 "分为堆（对象实例）、虚拟机栈（方法调用）、方法区（类元信息）、程序计数器；GC 主要作用于堆，分新生代/老年代回收。", 3),
                (jobs[1], "project", "请描述一个你负责过的模块，重点讲数据库设计。",
                 "表设计,索引,范式,冗余取舍",
                 "结合业务设计表结构，高频查询字段加索引，合理取舍冗余字段换取查询性能，并通过慢查询持续优化。", 2),
                # --- 前端 ---
                (jobs[2], "technical", "Vue 与 React 在响应式原理上有什么主要区别？",
                 "响应式,虚拟DOM,数据驱动,组件通信",
                 "Vue 基于依赖收集 + Proxy 做响应式，模板编译优化；React 基于不可变 state + 虚拟 DOM diff。Vue 上手平缓、模板直观，React 生态灵活。", 2),
                (jobs[2], "technical", "请解释 JavaScript 的事件循环机制。",
                 "调用栈,宏任务,微任务,异步执行",
                 "JS 单线程，通过事件循环调度：同步任务进调用栈，异步任务按宏任务/微任务队列执行，微任务优先于宏任务，Promise 属微任务、setTimeout 属宏任务。", 3),
                (jobs[2], "project", "请介绍你做过的一个前端页面，讲性能优化。",
                 "首屏,懒加载,缓存,构建优化",
                 "组件按需加载、路由懒加载、图片懒加载，静态资源加缓存并做构建分包，首屏加载时间显著下降。", 2),
                # --- 测试开发 ---
                (jobs[3], "technical", "自动化测试分层的策略是什么？",
                 "单元测试,接口测试,E2E,金字塔模型",
                 "按测试金字塔：底层单元测试最多、接口测试居中、E2E 最少；核心业务用接口测试覆盖，UI 只做关键链路。", 2),
                (jobs[3], "technical", "如何设计一套接口测试用例？",
                 "正常路径,边界,异常,幂等,鉴权",
                 "覆盖正常流程、边界值、异常入参、鉴权失败、幂等性；用接口文档契约驱动，结合数据准备与断言。", 2),
                (jobs[3], "behavioral", "遇到一个反复复现又难以定位的 Bug，你会怎么排查？",
                 "复现,二分定位,日志,代码评审,工具",
                 "先稳定复现，用二分法缩小范围，加日志打点定位，必要时用调试器单步，最后通过代码评审确认根因并补回归用例。", 3),
                # --- 数据分析 ---
                (jobs[4], "technical", "SQL 中 INNER JOIN 与 LEFT JOIN 的区别？如何优化关联查询？",
                 "JOIN类型,驱动表,索引,执行计划",
                 "INNER 只返回两边匹配的记录，LEFT 保留左表全部记录；优化上用较小表作驱动表、关联字段加索引、看执行计划避免全表扫描。", 2),
                (jobs[4], "technical", "如何设计一个 A/B 测试？",
                 "实验假设,样本量,显著性,实验周期,指标",
                 "明确假设与核心指标，估算样本量与实验周期，随机分流并保证组间无泄漏，用显著性检验判断结果并考虑长期影响。", 3),
                (jobs[4], "project", "请讲一次你通过数据分析帮助决策的经历。",
                 "数据清洗,分析思路,结论,业务价值",
                 "明确问题→取数清洗→探索性分析→输出可视化结论与建议，最终推动了某个运营策略的调整并带来可量化收益。", 2),
                # --- 算法 ---
                (jobs[5], "technical", "什么时候选大模型微调、什么时候选 RAG？",
                 "微调,检索增强,知识更新,成本,幻觉",
                 "知识源频繁变化、需要可溯源和低成本更新时选 RAG；需要把模型能力固化为特定业务风格或私有知识且更新不频繁时才考虑微调。", 3),
                (jobs[5], "technical", "快排、归并、堆排序的时间复杂度和稳定性如何？",
                 "复杂度,稳定性,适用场景",
                 "三者平均/最坏都是 O(n log n)；快排不稳定但常数小、空间 O(log n)；归并稳定需 O(n) 空间；堆排序不稳定、原地。", 2),
                (jobs[5], "project", "请介绍你做过的一个模型或算法项目。",
                 "问题定义,数据处理,模型选择,评估指标,效果",
                 "定义问题→清洗数据→选基线模型→调参与评估→上线监控，用准确率/召回率等指标衡量并持续迭代。", 2),
                # --- 通用（不绑定岗位）---
                (None, "self_intro", "请做一个 1 分钟自我介绍。",
                 "教育背景,项目经历,技能,求职动机",
                 "面试官你好，我是XX大学计算机专业应届生，主攻 Python 后端，做过数据报表和智能客服项目，熟悉 FastAPI 与数据库优化……", 1),
                (None, "behavioral", "请举例说明你在团队项目中遇到分歧时是如何解决的。",
                 "STAR 结构,沟通,换位思考,结果",
                 "（情境）小组开发时对技术选型有分歧；（任务）需要尽快确定方案；（行动）我整理两种方案优劣对比，组织短会讨论并投票，保留可回退方案；（结果）达成一致并按时交付。", 2),
                (None, "reverse", "面试最后，你有什么想问我们的？",
                 "主动提问,关注成长,了解业务",
                 "可以问团队当前的技术栈与迭代节奏、入职后前三个月的工作重点、岗位最重要的能力等，展现主动性。", 1),
            ]
            db.add_all(
                [
                    Question(job_id=q[0].id if q[0] else None, category=q[1], question=q[2],
                             expected_points=q[3], sample_answer=q[4], difficulty=q[5])
                    for q in q_data
                ]
            )

            # ===== 面试官（3 位，供面试官管理与面试归属）=====
            db.add_all(
                [
                    Interviewer(name="张老师", role="teacher", title="实习指导教师"),
                    Interviewer(name="王老师", role="hr", title="招聘 HR"),
                    Interviewer(name="李老师", role="admin", title="教学主任"),
                ]
            )
        db.commit()
        print("[init_db] 建表完成，演示数据已写入 data/sitas.db")
    finally:
        db.close()


if __name__ == "__main__":
    main()
