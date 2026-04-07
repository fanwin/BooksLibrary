"""
填充图书数据脚本
用法：在 backend 目录下运行 python seed_books.py
"""
from app.core.database import SessionLocal
from app.models.models import Book, BookCopy, BookStatus, CopyStatus, Category


def seed_categories(db):
    """创建默认分类（如已存在则跳过）"""
    categories = [
        {"name": "文学", "level": 1, "sort_order": 1},
        {"name": "小说", "level": 2, "parent_id": 1, "sort_order": 1},
        {"name": "诗歌散文", "level": 2, "parent_id": 1, "sort_order": 2},
        {"name": "计算机科学", "level": 1, "sort_order": 2},
        {"name": "编程语言", "level": 2, "parent_id": 3, "sort_order": 1},
        {"name": "人工智能", "level": 2, "parent_id": 3, "sort_order": 2},
        {"name": "历史", "level": 1, "sort_order": 3},
        {"name": "中国历史", "level": 2, "parent_id": 5, "sort_order": 1},
        {"name": "世界历史", "level": 2, "parent_id": 5, "sort_order": 2},
        {"name": "经济管理", "level": 1, "sort_order": 4},
        {"name": "哲学", "level": 1, "sort_order": 5},
        {"name": "自然科学", "level": 1, "sort_order": 6},
        {"name": "数学", "level": 2, "parent_id": 8, "sort_order": 1},
        {"name": "物理学", "level": 2, "parent_id": 8, "sort_order": 2},
        {"name": "教育学", "level": 1, "sort_order": 7},
        {"name": "艺术", "level": 1, "sort_order": 8},
    ]
    for cat in categories:
        existing = db.query(Category).filter(Category.name == cat["name"],
                                              Category.parent_id == (cat.get("parent_id"))).first()
        if not existing:
            db.add(Category(**cat))
    db.commit()
    print("分类数据已就绪")


def seed_books(db):
    """插入一批图书数据（如已存在相同ISBN则跳过）"""
    books = [
        # ---- 文学 / 小说 ----
        {"isbn": "9787020002207", "title": "红楼梦", "author": "曹雪芹", "publisher": "人民文学出版社",
         "publish_year": 1996, "category_id": 2, "location": "A区1楼", "total_copies": 5,
         "price": 59.70, "call_number": "I242.4/1",
         "description": "中国古典四大名著之首，以贾宝玉、林黛玉的爱情悲剧为主线，描写了贾、王、史、薛四大家族的兴衰。"},

        {"isbn": "9787020008735", "title": "三国演义", "author": "罗贯中", "publisher": "人民文学出版社",
         "publish_year": 1998, "category_id": 2, "location": "A区1楼", "total_copies": 4,
         "price": 39.50, "call_number": "I242.4/2",
         "description": "中国古典四大名著之一，讲述了东汉末年到西晋初年之间的历史风云。"},

        {"isbn": "9787020008728", "title": "水浒传", "author": "施耐庵", "publisher": "人民文学出版社",
         "publish_year": 1997, "category_id": 2, "location": "A区1楼", "total_copies": 4,
         "price": 43.00, "call_number": "I242.4/3",
         "description": "中国古典四大名著之一，描写了北宋末年以宋江为首的一百零八位好汉的传奇故事。"},

        {"isbn": "9787020008735", "title": "西游记", "author": "吴承恩", "publisher": "人民文学出版社",
         "publish_year": 2004, "category_id": 2, "location": "A区1楼", "total_copies": 3,
         "price": 47.20, "call_number": "I242.4/4",
         "description": "中国古典四大名著之一，讲述了唐僧师徒四人西天取经的冒险历程。"},

        {"isbn": "9787532725694", "title": "活着", "author": "余华", "publisher": "上海译文出版社",
         "publish_year": 2012, "category_id": 2, "location": "A区2楼", "total_copies": 6,
         "price": 29.00, "call_number": "I247.5/1",
         "description": "余华代表作，讲述了农村人福贵悲惨的一生，在历史的洪流中承受着生活的苦难。"},

        {"isbn": "9787544253994", "title": "围城", "author": "钱锺书", "publisher": "人民文学出版社",
         "publish_year": 1991, "category_id": 2, "location": "A区2楼", "total_copies": 3,
         "price": 23.00, "call_number": "I247.5/2",
         "description": "钱锺书唯一的长篇小说，以诙谐幽默的笔触描写了抗战时期知识分子的生活百态。"},

        {"isbn": "9787020024759", "title": "平凡的世界", "author": "路遥", "publisher": "人民文学出版社",
         "publish_year": 2004, "category_id": 2, "location": "A区2楼", "total_copies": 5,
         "price": 64.00, "call_number": "I247.5/3",
         "description": "路遥代表作，以全景式的方式展现了当代中国城乡社会生活，曾获茅盾文学奖。"},

        {"isbn": "9787544249685", "title": "白鹿原", "author": "陈忠实", "publisher": "南海出版公司",
         "publish_year": 2012, "category_id": 2, "location": "A区2楼", "total_copies": 3,
         "price": 39.50, "call_number": "I247.5/4",
         "description": "陈忠实代表作，讲述了白姓和鹿姓两大家族在白鹿原上半个多世纪的恩怨纷争。"},

        {"isbn": "9787020042494", "title": "百年孤独", "author": "加西亚·马尔克斯", "publisher": "南海出版公司",
         "publish_year": 2011, "category_id": 2, "location": "A区3楼", "total_copies": 4,
         "price": 39.50, "call_number": "I775.45/1",
         "description": "魔幻现实主义文学的代表作，描述了布恩迪亚家族七代人的传奇故事和马孔多小镇的兴衰。"},

        {"isbn": "9787544270878", "title": "挪威的森林", "author": "村上春树", "publisher": "南海出版公司",
         "publish_year": 2018, "category_id": 2, "location": "A区3楼", "total_copies": 4,
         "price": 36.00, "call_number": "I313.45/1",
         "description": "村上春树最畅销的作品，以纪实手法和诗意语言描写了主人公渡边彻的青春往事。"},

        {"isbn": "9787020009340", "title": "呐喊", "author": "鲁迅", "publisher": "人民文学出版社",
         "publish_year": 1973, "category_id": 2, "location": "A区2楼", "total_copies": 3,
         "price": 15.00, "call_number": "I210.6/1",
         "description": "鲁迅短篇小说集，收录了《狂人日记》《孔乙己》《药》《阿Q正传》等经典名篇。"},

        # ---- 文学 / 诗歌散文 ----
        {"isbn": "9787020086687", "title": "我与地坛", "author": "史铁生", "publisher": "人民文学出版社",
         "publish_year": 2011, "category_id": 3, "location": "A区2楼", "total_copies": 3,
         "price": 22.00, "call_number": "I267/1",
         "description": "史铁生最具代表性的散文作品，记录了作者与地坛的不解之缘以及对生命的深刻感悟。"},

        {"isbn": "9787544267281", "title": "目送", "author": "龙应台", "publisher": "广西师范大学出版社",
         "publish_year": 2014, "category_id": 3, "location": "A区2楼", "total_copies": 3,
         "price": 43.00, "call_number": "I267/2",
         "description": "龙应台散文集，以温柔笔触书写了关于亲情、关于人生渐行渐远的感悟。"},

        # ---- 计算机科学 / 编程语言 ----
        {"isbn": "9787115546081", "title": "深入理解计算机系统", "author": "Randal E. Bryant", "publisher": "机械工业出版社",
         "publish_year": 2020, "category_id": 4, "location": "B区1楼", "total_copies": 5,
         "price": 139.00, "call_number": "TP3/1",
         "description": "从程序员的角度详细阐述计算机系统的本质概念，涵盖处理器、存储器、链接、异常控制流等核心内容。"},

        {"isbn": "9787115529350", "title": "JavaScript高级程序设计", "author": "Matt Frisbie", "publisher": "人民邮电出版社",
         "publish_year": 2020, "category_id": 5, "location": "B区1楼", "total_copies": 4,
         "price": 129.00, "call_number": "TP312JA/1",
         "description": "JavaScript经典权威指南，全面深入地介绍了JavaScript语言的核心概念和高级特性。"},

        {"isbn": "9787111641247", "title": "Python编程：从入门到实践", "author": "Eric Matthes", "publisher": "机械工业出版社",
         "publish_year": 2020, "category_id": 5, "location": "B区1楼", "total_copies": 6,
         "price": 89.00, "call_number": "TP312PY/1",
         "description": "Python入门经典教材，分上下两篇：入门篇讲解基础知识，项目篇通过三个实战项目巩固技能。"},

        {"isbn": "9787115585739", "title": "C程序设计语言", "author": "Brian W. Kernighan", "publisher": "机械工业出版社",
         "publish_year": 2023, "category_id": 5, "location": "B区1楼", "total_copies": 3,
         "price": 55.00, "call_number": "TP312C/1",
         "description": "C语言经典著作，由C语言的设计者之一编写，被誉为程序员的必备参考书。"},

        {"isbn": "9787111558422", "title": "算法导论", "author": "Thomas H. Cormen", "publisher": "机械工业出版社",
         "publish_year": 2012, "category_id": 4, "location": "B区2楼", "total_copies": 4,
         "price": 128.00, "call_number": "TP301.6/1",
         "description": "算法领域权威教材，全面涵盖各类算法的设计与分析方法，兼顾严谨性与实用性。"},

        {"isbn": "9787115583759", "title": "数据结构与算法分析", "author": "Mark Allen Weiss", "publisher": "电子工业出版社",
         "publish_year": 2022, "category_id": 4, "location": "B区2楼", "total_copies": 3,
         "price": 69.00, "call_number": "TP311.12/1",
         "description": "经典数据结构教材，用C语言描述，讲解各种数据结构的实现和算法分析。"},

        {"isbn": "9787115614003", "title": "Vue.js设计与实现", "author": "霍春阳", "publisher": "人民邮电出版社",
         "publish_year": 2022, "category_id": 5, "location": "B区1楼", "total_copies": 4,
         "price": 89.80, "call_number": "TP312/2",
         "description": "深入剖析Vue.js 3.0的设计思路与实现原理，帮助开发者从源码层面理解框架机制。"},

        # ---- 计算机科学 / 人工智能 ----
        {"isbn": "9787115614751", "title": "动手学深度学习", "author": "阿斯顿·张", "publisher": "人民邮电出版社",
         "publish_year": 2023, "category_id": 6, "location": "B区2楼", "total_copies": 4,
         "price": 119.00, "call_number": "TP181/1",
         "description": "面向中文读者的深度学习实战教程，包含大量可运行的代码示例和习题。"},

        {"isbn": "9787521747457", "title": "深度学习", "author": "Ian Goodfellow", "publisher": "中信出版集团",
         "publish_year": 2023, "category_id": 6, "location": "B区2楼", "total_copies": 3,
         "price": 168.00, "call_number": "TP181/2",
         "description": "深度学习领域的权威教材（花书），系统介绍了深度学习的理论基础和实践方法。"},

        {"isbn": "9787115645731", "title": "机器学习实战", "author": "Peter Harrington", "publisher": "人民邮电出版社",
         "publish_year": 2023, "category_id": 6, "location": "B区2楼", "total_copies": 3,
         "price": 89.00, "call_number": "TP181/3",
         "description": "通过精心编排的实例切入机器学习的核心概念，兼顾理论与实践。"},

        # ---- 历史 / 中国历史 ----
        {"isbn": "9787108009821", "title": "万历十五年", "author": "黄仁宇", "publisher": "生活·读书·新知三联书店",
         "publish_year": 2006, "category_id": 7, "location": "C区1楼", "total_copies": 4,
         "price": 20.00, "call_number": "K248.3/1",
         "description": "以1587年为切入点，从大历史观的角度分析明代社会之症结，被视为中国历史研究的经典之作。"},

        {"isbn": "9787020002073", "title": "史记", "author": "司马迁", "publisher": "人民文学出版社",
         "publish_year": 1982, "category_id": 7, "location": "C区1楼", "total_copies": 3,
         "price": 78.00, "call_number": "K204.2/1",
         "description": "中国第一部纪传体通史，被鲁迅誉为'史家之绝唱，无韵之离骚'。"},

        {"isbn": "9787108042256", "title": "中国历代政治得失", "author": "钱穆", "publisher": "生活·读书·新知三联书店",
         "publish_year": 2001, "category_id": 7, "location": "C区1楼", "total_copies": 3,
         "price": 14.00, "call_number": "D691/1",
         "description": "钱穆先生的专题演讲合集，分别论述汉唐宋明清五代的政府组织、考试、经济、兵役等制度。"},

        # ---- 历史 / 世界历史 ----
        {"isbn": "9787540444785", "title": "人类简史", "author": "尤瓦尔·赫拉利", "publisher": "中信出版社",
         "publish_year": 2017, "category_id": 8, "location": "C区2楼", "total_copies": 5,
         "price": 68.00, "call_number": "K02/1",
         "description": "从十万年前有生命迹象开始到21世纪资本、科技交织的人类发展史。"},

        {"isbn": "9787508653377", "title": "全球通史", "author": "斯塔夫里阿诺斯", "publisher": "中信出版社",
         "publish_year": 2015, "category_id": 8, "location": "C区2楼", "total_copies": 3,
         "price": 88.00, "call_number": "K10/1",
         "description": "以全球视野审视世界各地区文明的产生和发展，被誉为当代世界历史编纂学的奠基之作。"},

        {"isbn": "9787508660757", "title": "枪炮、病菌与钢铁", "author": "贾雷德·戴蒙德", "publisher": "中信出版社",
         "publish_year": 2016, "category_id": 8, "location": "C区2楼", "total_copies": 3,
         "price": 58.00, "call_number": "K02/2",
         "description": "探讨了人类社会发展差异的根源，从地理环境角度解释为何欧亚文明最终领先其他地区。"},

        # ---- 经济管理 ----
        {"isbn": "9787508663314", "title": "经济学原理：微观经济学", "author": "N. 格里高利·曼昆", "publisher": "中信出版社",
         "publish_year": 2020, "category_id": 9, "location": "D区1楼", "total_copies": 5,
         "price": 78.00, "call_number": "F016/1",
         "description": "经济学入门经典教材，以通俗易懂的方式讲解微观经济学的基本原理。"},

        {"isbn": "9787508653912", "title": "国富论", "author": "亚当·斯密", "publisher": "中信出版社",
         "publish_year": 2014, "category_id": 9, "location": "D区1楼", "total_copies": 3,
         "price": 58.00, "call_number": "F091.33/1",
         "description": "现代经济学开山之作，系统阐述了自由市场经济的基本原理和政策主张。"},

        {"isbn": "9787508680766", "title": "从优秀到卓越", "author": "吉姆·柯林斯", "publisher": "中信出版社",
         "publish_year": 2019, "category_id": 9, "location": "D区1楼", "total_copies": 3,
         "price": 56.00, "call_number": "F272/1",
         "description": "通过对数千家企业的系统研究，揭示了优秀企业实现跨越式发展的关键因素。"},

        # ---- 哲学 ----
        {"isbn": "9787108009814", "title": "中国哲学简史", "author": "冯友兰", "publisher": "生活·读书·新知三联书店",
         "publish_year": 2013, "category_id": 10, "location": "E区1楼", "total_copies": 4,
         "price": 25.00, "call_number": "B2/1",
         "description": "冯友兰先生的哲学入门经典，以简洁明晰的语言概述了中国哲学的主要流派与思想发展。"},

        {"isbn": "9787108010321", "title": "西方哲学史", "author": "罗素", "publisher": "生活·读书·新知三联书店",
         "publish_year": 2003, "category_id": 10, "location": "E区1楼", "total_copies": 3,
         "price": 48.00, "call_number": "B5/1",
         "description": "罗素最重要的学术著作之一，全面梳理了自古希腊至20世纪的西方哲学发展脉络。"},

        # ---- 自然科学 / 数学 ----
        {"isbn": "9787111544937", "title": "什么是数学", "author": "R·柯朗", "publisher": "机械工业出版社",
         "publish_year": 2016, "category_id": 11, "location": "F区1楼", "total_copies": 3,
         "price": 59.00, "call_number": "O1/1",
         "description": "面向普通读者的数学经典读物，以浅显的方式展示数学的本质和精神。"},

        # ---- 自然科学 / 物理学 ----
        {"isbn": "9787542856204", "title": "时间简史", "author": "史蒂芬·霍金", "publisher": "上海译文出版社",
         "publish_year": 2010, "category_id": 12, "location": "F区1楼", "total_copies": 4,
         "price": 38.00, "call_number": "P159/1",
         "description": "霍金科普代表作，探讨了宇宙的起源、黑洞、时间旅行等深奥话题，通俗易懂。"},

        {"isbn": "9787535732306", "title": "费曼物理学讲义", "author": "理查德·费曼", "publisher": "上海科技出版社",
         "publish_year": 2013, "category_id": 12, "location": "F区2楼", "total_copies": 3,
         "price": 168.00, "call_number": "O4/1",
         "description": "费曼在加州理工学院的物理学讲义，被誉为物理学教育史上最经典的教材之一。"},

        # ---- 教育学 ----
        {"isbn": "9787544456474", "title": "教育的目的", "author": "怀特海", "publisher": "广西师范大学出版社",
         "publish_year": 2015, "category_id": 13, "location": "G区1楼", "total_copies": 3,
         "price": 32.00, "call_number": "G40/1",
         "description": "怀特海的教育哲学经典著作，提出了'教育即引导'和'浪漫-精确-综合'三阶段理论。"},

        {"isbn": "9787108010322", "title": "爱弥儿", "author": "卢梭", "publisher": "商务印书馆",
         "publish_year": 2016, "category_id": 13, "location": "G区1楼", "total_copies": 2,
         "price": 45.00, "call_number": "G40/2",
         "description": "卢梭的教育哲学名著，通过虚构人物爱弥儿的成长过程阐述自然教育的理念。"},

        # ---- 艺术 ----
        {"isbn": "9787549610286", "title": "艺术的故事", "author": "贡布里希", "publisher": "广西美术出版社",
         "publish_year": 2015, "category_id": 14, "location": "H区1楼", "total_copies": 3,
         "price": 188.00, "call_number": "J05/1",
         "description": "最著名的艺术入门书，以叙事性的笔法讲述了从最早的洞窟绘画到当代实验艺术的发展历程。"},
    ]

    inserted = 0
    skipped = 0
    for data in books:
        existing = db.query(Book).filter(Book.isbn == data["isbn"]).first()
        if existing:
            skipped += 1
            continue
        book = Book(
            isbn=data["isbn"],
            title=data["title"],
            author=data["author"],
            publisher=data["publisher"],
            publish_year=data["publish_year"],
            category_id=data["category_id"],
            location=data["location"],
            status=BookStatus.AVAILABLE,
            total_copies=data["total_copies"],
            available_copies=data["total_copies"],
            price=data["price"],
            call_number=data["call_number"],
            description=data["description"],
        )
        db.add(book)
        db.flush()  # 获取 book_id

        # 为每本书创建副本记录
        for i in range(data["total_copies"]):
            barcode = f"{data['isbn']}-{book.book_id}-{i+1:03d}"
            copy = BookCopy(
                book_id=book.book_id,
                barcode=barcode,
                status=CopyStatus.AVAILABLE,
                location_detail=data["location"],
            )
            db.add(copy)

        inserted += 1

    db.commit()
    print(f"图书数据填充完成：新增 {inserted} 本，跳过 {skipped} 本（已存在）")


def main():
    db = SessionLocal()
    try:
        seed_categories(db)
        seed_books(db)
    except Exception as e:
        db.rollback()
        print(f"填充失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
