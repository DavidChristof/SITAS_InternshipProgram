# -*- coding: utf-8 -*-
"""一次性扩充 RAG 知识库（答辩演示数据）。运行：python -m backend.scripts.expand_kb

只写新增文件，不覆盖已有文件；输出新增文件清单。
"""
import json
from pathlib import Path

KB = Path(__file__).resolve().parents[2] / "data" / "knowledge"


def write(cat: str, name: str, title: str, content: str, meta: dict) -> Path:
    d = KB / cat
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    if p.exists():
        print(f"  [跳过已存在] {cat}/{name}")
        return p
    p.write_text(
        json.dumps({"title": title, "content": content, "meta": meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  [新增] {cat}/{name}")
    return p


# ==================== 1. 岗位 JD ====================
jobs = {
    "java_backend": {
        "title": "Java 后端开发工程师岗位JD",
        "content": "岗位职责：负责公司核心业务系统的后端服务设计与开发，包括 REST API 开发、数据库建模、微服务拆分、中间件（Redis/MQ）接入与性能优化。任职要求：计算机相关专业本科及以上；熟练掌握 Java，熟悉 Spring Boot/Spring Cloud；掌握 MySQL 与索引优化；了解 Redis 缓存与消息队列；有分布式或高并发经验者优先。加分项：了解微服务治理、Docker/K8s、有实习或项目经验。",
        "meta": {"category": "job", "skills": ["Java", "Spring Boot", "MySQL", "Redis"]},
    },
    "qa_engineer": {
        "title": "测试开发工程师岗位JD",
        "content": "岗位职责：负责产品的自动化测试体系建设，包括接口测试、UI 自动化、性能与稳定性测试，编写测试用例并推动质量闭环。任职要求：计算机相关专业本科及以上；熟悉 Python 或 Java；了解 pytest/TestNG、Selenium 等测试框架；具备接口测试（Postman/requests）经验；了解 CI/CD 流水线优先。加分项：有自动化测试平台建设经验、了解 JIRA/禅道等缺陷管理工具。",
        "meta": {"category": "job", "skills": ["Python", "自动化测试", "pytest", "CI/CD"]},
    },
}

# ==================== 2. 企业资料 ====================
companies = {
    "star_tech": {
        "title": "星辰科技有限公司",
        "content": "公司规模：200-500 人，成立于 2016 年，总部位于深圳。主营方向：面向电商零售行业提供 SaaS 平台与数字营销解决方案。核心技术：微服务架构、大数据分析、智能推荐。公司文化：结果导向、技术驱动，团队年轻活跃；应届生有完整培养体系，技术线晋升透明。",
        "meta": {"category": "company", "industry": "互联网 / 电商 SaaS"},
    },
    "yunfan_data": {
        "title": "云帆数据科技有限公司",
        "content": "公司规模：100-300 人，成立于 2018 年，总部位于杭州。主营方向：企业级大数据分析与数据中台建设，服务金融、零售行业客户。核心技术：数据仓库、实时计算、机器学习建模。公司文化：数据说话、鼓励创新，提供数据科学方向的专业培训与认证支持。",
        "meta": {"category": "company", "industry": "大数据 / 数据服务"},
    },
    "aurora_ai": {
        "title": "极光智能科技",
        "content": "公司规模：150 人左右，成立于 2017 年，总部位于北京。主营方向：人工智能算法研发与行业解决方案，覆盖视觉、NLP 与多模态。核心技术：深度学习、大模型应用、智能体。公司文化：研究氛围浓厚，鼓励发表论文与开源，配有大模型算力资源，应届生可由资深研究员一对一带教。",
        "meta": {"category": "company", "industry": "人工智能"},
    },
    "qingteng_soft": {
        "title": "青藤软件",
        "content": "公司规模：300 人，成立于 2015 年，总部位于上海。主营方向：企业级软件产品与定制开发，覆盖办公协同、低代码平台。核心技术：前后端分离架构、低代码引擎、质量保障体系。公司文化：工程师文化、重视代码质量与测试规范，有完善的质量与测试团队。",
        "meta": {"category": "company", "industry": "软件服务"},
    },
}

# ==================== 3. 面试题库 ====================
# category: self_intro / project / technical / behavioral / reverse
questions = {
    # --- 反问环节（reverse）---
    "reverse_team_stack": {
        "title": "反问：团队技术栈与迭代节奏",
        "content": "如果入职，团队目前主要的技术栈和迭代节奏是怎样的？日常开发用什么协作流程？",
        "meta": {"category": "reverse", "expected_points": "主动了解技术栈,了解协作流程,结合自身技术背景,表达热情", "difficulty": 1},
    },
    "reverse_growth": {
        "title": "反问：成长路径与晋升",
        "content": "对于新入职的同学，公司/团队通常有哪些成长路径和晋升机会？",
        "meta": {"category": "reverse", "expected_points": "关注长期发展,主动规划职业路径,表达上进心", "difficulty": 1},
    },
    "reverse_mentor": {
        "title": "反问：导师制与新员工培养",
        "content": "新员工入职后会有导师制或系统性的培养计划吗？",
        "meta": {"category": "reverse", "expected_points": "了解培养机制,体现学习意愿,关注落地细节", "difficulty": 1},
    },
    "reverse_product": {
        "title": "反问：产品方向与业务",
        "content": "咱们当前主要的产品方向和业务目标是什么？未来半年有什么规划？",
        "meta": {"category": "reverse", "expected_points": "关注业务价值,主动了解产品,体现全局观", "difficulty": 1},
    },
    "reverse_expectation": {
        "title": "反问：岗位最重要的能力",
        "content": "您认为这个岗位最重要的三项能力是什么？入职后最希望我在哪方面快速上手？",
        "meta": {"category": "reverse", "expected_points": "明确岗位要求,聚焦能力提升,体现进取心", "difficulty": 1},
    },
    # --- 项目经历（project）---
    "pj_debug": {
        "title": "项目：最难排查的 Bug",
        "content": "请讲一个你遇到过的最难排查的 Bug 或线上故障，你是如何定位和解决的？",
        "meta": {"category": "project", "expected_points": "问题描述清晰,定位过程有方法,解决方案完整,有量化影响", "difficulty": 3},
    },
    "pj_perf": {
        "title": "项目：性能优化过程",
        "content": "请详细讲一次你做过的性能优化：从发现问题到定位瓶颈再到最终效果。",
        "meta": {"category": "project", "expected_points": "有量化指标,定位方法科学,优化手段合理,效果可验证", "difficulty": 3},
    },
    "pj_design": {
        "title": "项目：架构设计取舍",
        "content": "在项目设计时，你做过哪些技术选型或架构上的取舍？为什么这样选？",
        "meta": {"category": "project", "expected_points": "选型有依据,对比多个方案,考虑成本与演进,反思取舍", "difficulty": 3},
    },
    "pj_failure": {
        "title": "项目：失败与返工经历",
        "content": "讲一次项目中失败或返工的经历，你从中学到了什么？",
        "meta": {"category": "project", "expected_points": "敢于承认失败,分析原因,有改进措施,体现成长", "difficulty": 2},
    },
    # --- 行为面试（behavioral）---
    "beh_pressure": {
        "title": "行为：高压下的工作",
        "content": "请讲一次在高压或赶工期的情况下，你是如何安排优先级并完成任务的？",
        "meta": {"category": "behavioral", "expected_points": "情境清晰,分清主次,行动具体,结果与反思", "difficulty": 2},
    },
    "beh_mistake": {
        "title": "行为：承认错误的经历",
        "content": "请讲一次你犯过的错误，你是如何发现、承认并补救的？",
        "meta": {"category": "behavioral", "expected_points": "敢于承认,补救措施,承担责任,反思总结", "difficulty": 2},
    },
    "beh_team": {
        "title": "行为：团队分歧的处理",
        "content": "当与同事或团队在产品方案、技术上出现分歧时，你会怎么处理？",
        "meta": {"category": "behavioral", "expected_points": "理性沟通,以数据说话,尊重他人,达成共识", "difficulty": 2},
    },
    "beh_learning": {
        "title": "行为：快速学习新技能",
        "content": "请讲一次你为了完成任务而快速学习一门新技术的经历，你是如何学会的？",
        "meta": {"category": "behavioral", "expected_points": "学习目标明确,方法有效,学以致用,结果体现", "difficulty": 2},
    },
    # --- 自我介绍（self_intro）---
    "si_short": {
        "title": "自我介绍：一分钟精简版",
        "content": "请用一分钟做一个精简的自我介绍，突出你与这个岗位最匹配的 2-3 个亮点。",
        "meta": {"category": "self_intro", "expected_points": "结构清晰,亮点突出,匹配岗位,时间控制", "difficulty": 1},
    },
    "si_swot": {
        "title": "自我认知：优点与待改进",
        "content": "说说你的三个优点和一项最需要改进的不足？",
        "meta": {"category": "self_intro", "expected_points": "优点有实例支撑,不足坦诚,有改进计划", "difficulty": 2},
    },
    # --- 专业技能（technical）---
    "py_coroutine": {
        "title": "专业：Python 协程与 async/await",
        "content": "请解释 Python 的协程与 async/await 机制，以及它和线程相比的优缺点。",
        "meta": {"category": "technical", "expected_points": "协程原理,事件循环,与线程对比,适用场景", "difficulty": 3},
    },
    "py_orm": {
        "title": "专业：ORM 与原生 SQL",
        "content": "用 ORM（如 SQLAlchemy）和原生 SQL 各有什么优缺点？你会在什么场景下选择哪一种？",
        "meta": {"category": "technical", "expected_points": "ORM优点,原生SQL优点,性能对比,场景取舍", "difficulty": 2},
    },
    "redis_use": {
        "title": "专业：Redis 缓存穿透/击穿/雪崩",
        "content": "请解释缓存穿透、缓存击穿和缓存雪崩分别是什么？如何解决？",
        "meta": {"category": "technical", "expected_points": "三个概念区分,各自成因,解决方案,实战经验", "difficulty": 3},
    },
    "db_index": {
        "title": "专业：数据库索引原理",
        "content": "数据库索引为什么能加速查询？B+ 树索引的底层原理是什么？哪些情况下索引会失效？",
        "meta": {"category": "technical", "expected_points": "索引原理,B+树结构,失效场景,覆盖索引", "difficulty": 3},
    },
    "api_design": {
        "title": "专业：RESTful 接口设计",
        "content": "设计一套 RESTful API 时，你会遵循哪些原则？如何设计资源、版本和错误码？",
        "meta": {"category": "technical", "expected_points": "资源命名,HTTP方法语义,版本管理,错误处理,幂等", "difficulty": 2},
    },
    "auth_jwt": {
        "title": "专业：接口鉴权方案",
        "content": "JWT 和 Session 两种登录鉴权方案的区别是什么？各自适用什么场景？",
        "meta": {"category": "technical", "expected_points": "JWT结构,无状态,Session服务端存储,安全性与场景", "difficulty": 2},
    },
    "docker_deploy": {
        "title": "专业：Docker 部署",
        "content": "Docker 部署应用相比传统部署有什么优势？你如何编写 Dockerfile 或做容器化？",
        "meta": {"category": "technical", "expected_points": "镜像分层,环境一致,隔离性,构建优化", "difficulty": 2},
    },
    "concurrency": {
        "title": "专业：高并发限流与熔断",
        "content": "在接口层如何做限流、熔断和降级？常见的算法有哪些？",
        "meta": {"category": "technical", "expected_points": "令牌桶,漏桶,计数器,熔断概念,降级策略", "difficulty": 3},
    },
    "java_spring": {
        "title": "专业：Spring Boot 自动装配",
        "content": "请解释 Spring Boot 的自动装配（Auto Configuration）原理，以及依赖注入的优势。",
        "meta": {"category": "technical", "expected_points": "自动装配原理,条件注解,依赖注入,控制反转", "difficulty": 3},
    },
    "java_jvm": {
        "title": "专业：JVM 内存模型与 GC",
        "content": "JVM 运行时内存区域如何划分？常见的垃圾回收算法有哪些？",
        "meta": {"category": "technical", "expected_points": "堆栈方法区,GC算法,新生代老年代,调优思路", "difficulty": 3},
    },
    "fe_js_async": {
        "title": "专业：JS 事件循环",
        "content": "请解释 JavaScript 的事件循环（Event Loop）机制，以及宏任务与微任务的区别。",
        "meta": {"category": "technical", "expected_points": "调用栈,事件循环,宏任务微任务,异步执行顺序", "difficulty": 3},
    },
    "fe_vue_react": {
        "title": "专业：Vue 与 React 对比",
        "content": "Vue 与 React 在响应式原理和渲染机制上有什么主要区别？",
        "meta": {"category": "technical", "expected_points": "响应式原理,虚拟DOM,组件通信,各自适用场景", "difficulty": 2},
    },
    "algo_sort": {
        "title": "专业：常见排序算法",
        "content": "快排、归并、堆排序的时间复杂度和稳定性如何？什么场景下你会优先选哪种？",
        "meta": {"category": "technical", "expected_points": "复杂度分析,稳定性,适用场景,手写能力", "difficulty": 2},
    },
    "algo_dp": {
        "title": "专业：动态规划思想",
        "content": "请用动态规划解决一个你熟悉的题目（如背包、爬楼梯、最长公共子序列），并说明思路。",
        "meta": {"category": "technical", "expected_points": "状态定义,转移方程,边界条件,复杂度优化", "difficulty": 3},
    },
    "data_sql_join": {
        "title": "专业：SQL 多表查询与 JOIN",
        "content": "SQL 中 INNER JOIN、LEFT JOIN 的区别是什么？如何优化多表关联查询？",
        "meta": {"category": "technical", "expected_points": "JOIN类型区别,驱动表,索引优化,执行计划", "difficulty": 2},
    },
    "data_abtest": {
        "title": "专业：A/B 测试与指标体系",
        "content": "如何设计一个 A/B 测试？核心指标与样本量、显著性怎么考虑？",
        "meta": {"category": "technical", "expected_points": "实验设计,核心指标,样本量,显著性,实验周期", "difficulty": 3},
    },
    "llm_finetune": {
        "title": "专业：微调 vs RAG",
        "content": "在接入大模型的场景里，什么时候选择微调（Fine-tuning），什么时候选择 RAG？",
        "meta": {"category": "technical", "expected_points": "两者原理,知识更新,成本对比,适用场景,幻觉控制", "difficulty": 3},
    },
}

# ==================== 4. 优秀回答样例 ====================
samples = {
    "good_answer_self_intro": {
        "title": "优秀回答样例：一分钟自我介绍",
        "content": "优秀回答示范：'面试官您好，我叫张三，本科毕业于北京大学计算机专业。毕业后有 3 年后端开发经验，上一份工作在互联网公司做后端开发。技术栈以 Python 为主，熟悉 FastAPI、MySQL、Redis，也接触过 RAG 大模型应用。做过两个项目：数据报表系统支撑日均 5 万请求、通过索引和缓存优化把接口耗时降了 50%；智能客服机器人基于 RAG 把问答准确率从 62% 提到 85%。我学习能力强、乐于挑战，希望能加入贵团队。' 评分要点：基本信息完整（20%）、亮点有量化数据（40%）、与岗位匹配（30%）、表达流畅自信（10%）。",
        "meta": {"category": "sample", "for_category": "self_intro"},
    },
    "good_answer_project": {
        "title": "优秀回答样例：项目深挖（性能优化）",
        "content": "优秀回答示范：'我重点讲数据报表系统的性能优化。背景是接口在高峰期响应超过 1 秒，影响体验。我的角色是后端开发，负责定位和优化。我先用慢查询分析定位到几条没走索引的 SQL，给高频查询字段加了联合索引；接着对热点数据引入 Redis 缓存，并处理了缓存穿透。最终接口平均耗时从 1 秒降到 500ms，降幅 50%。我的体会是：优化要先量化瓶颈、再针对性动手，而不是盲目加缓存。' 评分要点：问题量化清晰（20%）、定位方法科学（30%）、方案合理可复用（30%）、有总结反思（20%）。",
        "meta": {"category": "sample", "for_category": "project"},
    },
    "good_answer_behavioral": {
        "title": "优秀回答样例：行为面试（STAR）",
        "content": "优秀回答示范：'我讲一次赶工期的经历。当时报表系统要在两周内上线，但临时加了权限模块（情境）。我的任务是保证核心接口按时交付（任务）。我做了三件事：和产品沟通把非核心功能砍到二期；按优先级排接口顺序保证主流程；加班攻坚索引优化并用缓存顶住高峰（行动）。最后项目按时上线，接口耗时还降了 50%（结果）。这件事让我明白，紧急情况下分清主次、主动沟通比埋头苦干更重要。' 评分要点：STAR 四要素完整（50%）、行动有具体措施（30%）、有反思结论（20%）。",
        "meta": {"category": "sample", "for_category": "behavioral"},
    },
    "good_answer_reverse": {
        "title": "优秀回答样例：反问环节",
        "content": "优秀回答示范：'我想了解几个问题：一是如果入职，团队当前的技术栈和迭代节奏是怎样的？二是我前三个月的重点工作会是什么？三是您认为这个岗位最重要的能力有哪些？' 评分要点：问题围绕工作内容与发展（50%）、展现主动思考与诚意（30%）、不问薪资福利（20%）。",
        "meta": {"category": "sample", "for_category": "reverse"},
    },
    "good_answer_async": {
        "title": "优秀回答样例：Python 协程",
        "content": "优秀回答示范：'Python 的协程基于 async/await，底层是一个事件循环（如 asyncio），在单线程内通过状态机的挂起和恢复实现并发，适合 I/O 密集型场景。和线程相比：协程创建开销小、没有线程切换的上下文成本、不存在数据竞争；但协程是单线程的，CPU 密集型任务无法利用多核，需要配合多进程。所以我会用协程处理大量网络请求，用多进程处理 CPU 密集计算。' 评分要点：协程原理正确（30%）、与线程对比全面（30%）、能区分 I/O 与 CPU 密集（30%）、有实际场景（10%）。",
        "meta": {"category": "sample", "for_category": "technical"},
    },
    "good_answer_database": {
        "title": "优秀回答样例：数据库索引优化",
        "content": "优秀回答示范：'索引能加速查询，本质是 B+ 树把数据组织成有序结构，让全表扫描变成 O(log n) 的查找。但索引不是越多越好：会占用存储、拖慢写入。我优化时会先看执行计划（EXPLAIN），找没走索引的慢 SQL，再给高频查询字段建联合索引；同时避免索引失效的场景，比如对索引列做函数运算、隐式类型转换等。我的原则是：以慢查询为依据，精准建索引。' 评分要点：B+ 树原理正确（30%）、能讲索引代价（20%）、优化方法可落地（30%）、结合实战（20%）。",
        "meta": {"category": "sample", "for_category": "technical"},
    },
    "good_answer_rag": {
        "title": "优秀回答样例：RAG 原理",
        "content": "优秀回答示范：'RAG 是检索增强生成。流程是先把知识文档切块、建立索引（可用 BM25 或向量检索），查询时检索最相关的片段作为上下文，连同问题一起交给大模型生成回答。它的价值在于：知识可以独立更新、回答有据可查、能显著降低大模型的幻觉。我在客服机器人项目里就是这么做的，把问答准确率从 62% 提到 85%。我理解的取舍是：知识源经常变、需要可溯源，就优先 RAG；需要把模型能力固化到业务，才考虑微调。' 评分要点：流程描述清晰（30%）、讲清价值（20%）、有项目量化（30%）、能讲 RAG 与微调取舍（20%）。",
        "meta": {"category": "sample", "for_category": "technical"},
    },
    "good_answer_java": {
        "title": "优秀回答样例：Spring Boot 自动装配",
        "content": "优秀回答示范：'Spring Boot 的自动装配基于 @EnableAutoConfiguration，启动时通过 spring.factories 里的自动配置类，配合 @ConditionalOnClass 等条件注解，按依赖情况自动装配 Bean，所以只需要引入 starter 就能开箱即用。依赖注入（DI）实现控制反转，让对象由容器管理，降低耦合、便于测试。我的理解是：自动装配省掉了大量 XML 配置，让团队聚焦业务；但出现问题时也要会看自动配置的源码定位。' 评分要点：自动装配原理正确（40%）、能讲条件注解（20%）、DI/IoC 概念清楚（30%）、有工程体会（10%）。",
        "meta": {"category": "sample", "for_category": "technical"},
    },
}

for cat, items in [("jobs", jobs), ("companies", companies), ("questions", questions), ("samples", samples)]:
    print(f"--- {cat} ---")
    for name, data in items.items():
        write(cat, name, data["title"], data["content"], data["meta"])

print("\n完成。")
